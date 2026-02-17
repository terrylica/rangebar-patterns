# FILE-SIZE-OK: 4-stage WFO pipeline is a single cohesive module (~700 lines)
"""Walk-forward barrier optimization engine.

4-stage pipeline for out-of-sample validation of time-decay barrier configs:
  Stage 1: WFO Screening (sequential walk-forward, all 434 barriers)
  Stage 2: CPCV Validation (combinatorial purged CV, top-K barriers)
  Stage 3: Bootstrap Stability (BCa confidence intervals)
  Stage 4: Stability Synthesis (Vorob'ev + regime + GT-composite + knee)

ALL sizes are in bar counts (integers). NO timestamps, NO timedeltas.
Range bars form on fixed price movement, not fixed time — bar-index space
is the only valid coordinate system for CV, bootstrap, and regime detection.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import polars as pl

from rangebar_patterns import config
from rangebar_patterns.eval.cdar import compute_cdar
from rangebar_patterns.eval.omega import compute_omega
from rangebar_patterns.eval.rachev import compute_rachev

# ---- Data Structures ----


@dataclass(frozen=True)
class BarrierParams:
    """Parsed barrier configuration from barrier_id string."""

    phase1_bars: int
    sl_tight_mult: float
    max_bars: int


# ---- Stage 1: WFO Screening ----


def build_wfo_folds(
    n_signals: int,
    *,
    min_train_splits: int = config.WF_MIN_TRAIN_SPLITS,
    max_train_splits: int = config.WF_MAX_TRAIN_SPLITS,
    purge_bars: int = 100,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Build sequential walk-forward folds using skfolio.WalkForward.

    All sizes are in observation counts (= bar counts for range bars).
    Uses freq=None to operate in bar-index space — no timestamps.

    Parameters
    ----------
    n_signals : int
        Total number of signals (observations).
    min_train_splits : int
        Minimum training folds before first test.
    max_train_splits : int
        Rolling window size in folds (prevents expanding-train bias).
    purge_bars : int
        Gap between train end and test start (prevents lookahead from
        trades whose outcomes extend into the test period).

    Returns
    -------
    list of (train_indices, test_indices) pairs.
    """
    from skfolio.model_selection import WalkForward

    # Data-driven fold sizing: ~200 signals per test fold
    n_splits = max(5, n_signals // 200)
    test_size = max(1, n_signals // n_splits)

    # Gate: need at least train + purge + test to fit one fold.
    # Without this, WalkForward raises ValueError when n_signals is too small.
    min_required = purge_bars + test_size * 2  # at least 1x test for train + 1x for test
    if n_signals < min_required:
        return []

    # Ensure train + purge + test fits within data
    max_train = n_signals - purge_bars - test_size
    train_size = min(test_size * max_train_splits, max(test_size, max_train))

    wf = WalkForward(
        test_size=test_size,
        train_size=train_size,
        purged_size=purge_bars,
        freq=None,
    )

    X = np.arange(n_signals).reshape(-1, 1)
    folds = []
    for train_idx, test_idx in wf.split(X):
        if len(train_idx) >= test_size * min_train_splits:
            folds.append((train_idx, test_idx))

    return folds


def evaluate_barriers_in_fold(
    signal_data: pl.DataFrame,
    test_idx: np.ndarray,
    barrier_ids: list[str] | None = None,
) -> pl.DataFrame:
    """Evaluate barrier configs on test-set signals for one WFO fold.

    Parameters
    ----------
    signal_data : pl.DataFrame
        Full signal data with columns: barrier_id, signal_idx (0-based position),
        return_pct, exit_type.
    test_idx : np.ndarray
        Integer indices of test-set signals.
    barrier_ids : list[str] or None
        If provided, evaluate only these barriers. Otherwise evaluate all.

    Returns
    -------
    pl.DataFrame with one row per barrier: barrier_id, n_trades, win_rate,
    profit_factor, omega, rachev, cdar, total_return, avg_return, max_drawdown.
    """
    test_arr = np.asarray(test_idx)
    test_set = set(test_arr.tolist())
    test_df = signal_data.filter(pl.col("signal_idx").is_in(test_set))

    if barrier_ids is not None:
        test_df = test_df.filter(pl.col("barrier_id").is_in(barrier_ids))

    rows = []
    for bid in test_df["barrier_id"].unique().sort().to_list():
        barrier_df = test_df.filter(pl.col("barrier_id") == bid)
        returns = barrier_df["return_pct"].to_list()
        n = len(returns)

        if n == 0:
            rows.append(_empty_barrier_row(bid))
            continue

        arr = np.array(returns, dtype=float)
        wins = float(np.sum(arr > 0))
        gross_profit = float(np.sum(arr[arr > 0]))
        gross_loss = float(np.abs(np.sum(arr[arr < 0])))

        # Cumulative equity for drawdown
        cum = np.cumsum(arr)
        running_max = np.maximum.accumulate(cum)
        drawdowns = running_max - cum
        mdd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # PF division cases:
        #   gross_loss > 0: normal PF = profit/loss, capped at PF_CAP
        #   gross_loss ≈ 0, gross_profit > 0: 100% WR → capped at PF_CAP
        #     (inf poisons aggregation; cap=10 matches institutional practice)
        #   gross_loss ≈ 0, gross_profit ≈ 0: all zero returns → NaN
        #     (0/0 is undefined, not infinity — see test_evaluate_barriers_zero_return_pf_nan)
        PF_CAP = 10.0  # Anything above 10 in a single fold is a small-sample artifact
        if gross_loss > 1e-12:
            pf = min(gross_profit / gross_loss, PF_CAP)
        elif gross_profit > 1e-12:
            pf = PF_CAP
        else:
            pf = float("nan")

        rows.append({
            "barrier_id": bid,
            "n_trades": n,
            "win_rate": wins / n,
            "profit_factor": pf,
            "omega": compute_omega(returns),
            "rachev": compute_rachev(returns) or 0.0,
            "cdar": compute_cdar(returns) or 0.0,
            "total_return": float(arr.sum()),
            "avg_return": float(arr.mean()),
            "max_drawdown": mdd,
        })

    return pl.DataFrame(rows)


def _empty_barrier_row(barrier_id: str) -> dict:
    """Return a zero-filled row for a barrier with no trades."""
    return {
        "barrier_id": barrier_id,
        "n_trades": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "omega": 0.0,
        "rachev": 0.0,
        "cdar": 0.0,
        "total_return": 0.0,
        "avg_return": 0.0,
        "max_drawdown": 0.0,
    }


def screen_top_k_barriers(
    fold_results: pl.DataFrame,
    k: int = config.WF_SCREEN_TOP_K,
) -> list[str]:
    """Select top K barriers by median OOS Omega across folds.

    Parameters
    ----------
    fold_results : pl.DataFrame
        Concatenated results from all folds. Must have columns:
        barrier_id, omega, fold_id.
    k : int
        Number of barriers to keep.

    Returns
    -------
    list of barrier_id strings, ordered by median Omega descending.
    Ties broken by lower omega_cv (stability), then higher median rachev.
    """
    agg = fold_results.group_by("barrier_id").agg([
        pl.col("omega").median().alias("median_omega"),
        (pl.col("omega").std() / pl.col("omega").mean()).alias("omega_cv"),
        pl.col("rachev").median().alias("median_rachev"),
    ])

    # Replace any null/NaN omega_cv with inf (worst stability)
    agg = agg.with_columns(
        pl.col("omega_cv").fill_null(float("inf")).fill_nan(float("inf")),
    )

    ranked = agg.sort(
        by=["median_omega", "omega_cv", "median_rachev"],
        descending=[True, False, True],
    )

    return ranked.head(k)["barrier_id"].to_list()


def build_fold_metadata(
    folds: list[tuple[np.ndarray, np.ndarray]],
    signal_df: pl.DataFrame,
    purge_bars: int = 100,
    embargo_bars: int = 0,
) -> list[dict]:
    """Extract metadata for each WFO fold.

    Parameters
    ----------
    folds : list of (train_idx, test_idx) pairs.
    signal_df : pl.DataFrame
        Must have columns: signal_idx, timestamp_ms (for diagnostic timestamps).
    purge_bars : int
        Purge gap used when building folds.
    embargo_bars : int
        Embargo used (Stage 2 only).

    Returns
    -------
    list of dicts with fold boundaries (bar indices primary, timestamps diagnostic).
    """
    metadata = []
    for fold_id, (train_idx, test_idx) in enumerate(folds):
        # Bar index boundaries (primary)
        train_start = int(train_idx.min())
        train_end = int(train_idx.max())
        test_start = int(test_idx.min())
        test_end = int(test_idx.max())

        # Calendar timestamps (diagnostic only — NOT used in CV)
        ts_col = "timestamp_ms"
        if ts_col in signal_df.columns:
            train_signals = signal_df.filter(pl.col("signal_idx").is_in(train_idx.tolist()))
            test_signals = signal_df.filter(pl.col("signal_idx").is_in(test_idx.tolist()))
            train_start_ms = int(train_signals[ts_col].min()) if len(train_signals) > 0 else 0
            train_end_ms = int(train_signals[ts_col].max()) if len(train_signals) > 0 else 0
            test_start_ms = int(test_signals[ts_col].min()) if len(test_signals) > 0 else 0
            test_end_ms = int(test_signals[ts_col].max()) if len(test_signals) > 0 else 0
        else:
            train_start_ms = train_end_ms = test_start_ms = test_end_ms = 0

        n_train_raw = len(train_idx)
        n_purged = 0  # skfolio handles purging internally
        n_train_purged = n_train_raw - n_purged

        metadata.append({
            "fold_id": fold_id,
            "train_start_bar": train_start,
            "train_end_bar": train_end,
            "test_start_bar": test_start,
            "test_end_bar": test_end,
            "train_start_ms": train_start_ms,
            "train_end_ms": train_end_ms,
            "test_start_ms": test_start_ms,
            "test_end_ms": test_end_ms,
            "purge_gap_bars": purge_bars,
            "embargo_bars": embargo_bars,
            "n_train_raw": n_train_raw,
            "n_train_purged": n_train_purged,
            "n_purged": n_purged,
            "n_test": len(test_idx),
        })

    return metadata


# ---- Stage 2: CPCV Validation ----


def build_cpcv_folds(
    n_signals: int,
    *,
    n_folds: int = 10,
    n_test_folds: int = config.WF_CPCV_N_TEST_FOLDS,
    purge_bars: int = 100,
    embargo_bars: int = config.WF_CPCV_EMBARGO_BARS,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Build combinatorial purged CV folds using skfolio.CombinatorialPurgedCV.

    All sizes are integer bar counts. NO timestamps, NO timedeltas.

    Parameters
    ----------
    n_signals : int
        Total number of signals.
    n_folds : int
        Number of groups to partition signals into. C(n_folds, n_test_folds)
        combinatorial splits will be generated.
    n_test_folds : int
        Number of test groups per split.
    purge_bars : int
        Gap between train and test (prevents lookahead).
    embargo_bars : int
        Gap after each test fold to prevent serial correlation leakage.

    Returns
    -------
    list of (train_indices, test_indices) pairs.
    """
    from skfolio.model_selection import CombinatorialPurgedCV

    cpcv = CombinatorialPurgedCV(
        n_folds=n_folds,
        n_test_folds=n_test_folds,
        purged_size=purge_bars,
        embargo_size=embargo_bars,
    )

    X = np.arange(n_signals).reshape(-1, 1)
    folds = []
    for train_idx, test_parts in cpcv.split(X):
        # CombinatorialPurgedCV returns test as list of arrays (one per test fold).
        # Flatten into a single array for consistent API.
        if isinstance(test_parts, list):
            test_idx = np.concatenate(test_parts)
        else:
            test_idx = test_parts
        folds.append((train_idx, test_idx))
    return folds


def run_nested_cpcv(
    signal_data: pl.DataFrame,
    cpcv_folds: list[tuple[np.ndarray, np.ndarray]],
    top_k_barriers: list[str],
    inner_k: int = config.WF_INNER_K,
) -> pl.DataFrame:
    """Nested CPCV: inner loop selects barriers, outer loop evaluates.

    For each outer fold:
    1. Inner: evaluate top_k_barriers on train subset via 3-fold inner WFO
    2. Select top inner_k by inner OOS Omega
    3. Outer: evaluate ONLY those inner_k barriers on outer test fold

    This prevents barrier snooping — outer test set never influences selection.

    Parameters
    ----------
    signal_data : pl.DataFrame
        Full signal data with columns: barrier_id, signal_idx, return_pct.
    cpcv_folds : list of (train_idx, test_idx) pairs.
    top_k_barriers : list[str]
        Barrier IDs surviving Stage 1 screening.
    inner_k : int
        Number of barriers to select in inner loop.

    Returns
    -------
    pl.DataFrame with columns: barrier_id, fold_id, n_trades, win_rate,
    profit_factor, omega, rachev, is_inner_selected.
    """
    all_rows = []

    for fold_id, (train_idx, test_idx) in enumerate(cpcv_folds):
        # Inner loop: 3-fold WFO on train subset to rank barriers
        inner_folds = build_wfo_folds(
            len(train_idx),
            min_train_splits=2,
            max_train_splits=3,
            purge_bars=min(50, len(train_idx) // 10),
        )

        # Map inner fold indices back to global signal indices
        inner_results = []
        for inner_train, inner_test in inner_folds:
            global_test = train_idx[inner_test]
            fold_df = evaluate_barriers_in_fold(
                signal_data, global_test, barrier_ids=top_k_barriers,
            )
            inner_results.append(fold_df)

        if inner_results:
            inner_concat = pl.concat(inner_results)
            # Select top inner_k by median Omega across inner folds
            inner_selected = screen_top_k_barriers(
                inner_concat.with_columns(pl.lit(0).alias("fold_id")),
                k=inner_k,
            )
        else:
            inner_selected = top_k_barriers[:inner_k]

        # Outer evaluation: ONLY inner-selected barriers on test fold
        outer_df = evaluate_barriers_in_fold(
            signal_data, test_idx, barrier_ids=inner_selected,
        )

        for row in outer_df.to_dicts():
            row["fold_id"] = fold_id
            row["is_inner_selected"] = True
            all_rows.append(row)

    return pl.DataFrame(all_rows) if all_rows else pl.DataFrame()


def compute_pbo_from_cpcv(
    cpcv_results: pl.DataFrame,
) -> dict[str, float]:
    """Estimate PBO per barrier from CPCV fold performance.

    PBO = fraction of folds where OOS rank is worse than IS rank.
    A barrier with PBO > 0.50 is likely overfit.

    Parameters
    ----------
    cpcv_results : pl.DataFrame
        Must have columns: barrier_id, fold_id, omega.

    Returns
    -------
    dict mapping barrier_id to PBO score (0.0 = robust, 1.0 = overfit).
    """
    if cpcv_results.is_empty():
        return {}

    barriers = cpcv_results["barrier_id"].unique().sort().to_list()
    fold_ids = cpcv_results["fold_id"].unique().sort().to_list()

    if len(fold_ids) < 2:
        return {b: 0.5 for b in barriers}

    pbo_scores = {}
    for bid in barriers:
        bid_df = cpcv_results.filter(pl.col("barrier_id") == bid)
        omegas = bid_df.sort("fold_id")["omega"].to_list()

        if len(omegas) < 2:
            pbo_scores[bid] = 0.5
            continue

        # Compare each fold's Omega to median of all other folds
        arr = np.array(omegas)
        n_worse = 0
        for i in range(len(arr)):
            others = np.delete(arr, i)
            if arr[i] < np.median(others):
                n_worse += 1

        pbo_scores[bid] = n_worse / len(arr)

    return pbo_scores


# ---- Stage 3: Bootstrap Stability ----


def compute_bootstrap_ci(
    oos_returns: list[float],
    metric_fn: callable,
    *,
    n_resamples: int = config.WF_BOOTSTRAP_RESAMPLES,
    alpha: float = 0.05,
    block_size: int = config.WF_BOOTSTRAP_BLOCK_SIZE,
) -> dict:
    """Compute BCa bootstrap confidence interval for a single metric.

    Uses Moving Block Bootstrap (MBB) to preserve serial correlation
    in trade returns. Falls back to IID bootstrap if block_size is too
    large relative to sample size.

    CRITICAL: Only use for DISTRIBUTIONAL metrics (Omega, Rachev, PF,
    total_return). NEVER use for SEQUENTIAL metrics (CDaR, max_drawdown)
    — IID/MBB resampling destroys the cumulative-sum structure.

    Parameters
    ----------
    oos_returns : list[float]
        Pooled OOS trade returns (from CPCV folds).
    metric_fn : callable
        Function taking np.ndarray of returns → scalar. Must accept a
        single keyword argument ``x``.
    n_resamples : int
        Number of bootstrap replicates.
    alpha : float
        Significance level (0.05 = 95% CI).
    block_size : int
        Block size for MBB (regime persistence).

    Returns
    -------
    dict with keys: point_estimate, ci_lower, ci_upper, se, n_trades, method.
    """
    from arch.bootstrap import IIDBootstrap, MovingBlockBootstrap

    arr = np.array(oos_returns, dtype=float)
    n = len(arr)

    if n < 10:
        pe = float(metric_fn(x=arr))
        return {
            "point_estimate": pe,
            "ci_lower": pe,
            "ci_upper": pe,
            "se": 0.0,
            "n_trades": n,
            "method": "degenerate",
        }

    # Fall back to IID if block_size too large relative to sample
    if block_size > n // 3:
        bs = IIDBootstrap(x=arr, seed=42)
        method = "iid"
    else:
        bs = MovingBlockBootstrap(block_size, x=arr, seed=42)
        method = "mbb"

    # BCa can fail when jackknife produces inf/NaN (e.g., all-positive returns
    # give inf Omega). Fall back to percentile method.
    try:
        ci = bs.conf_int(
            func=metric_fn,
            reps=n_resamples,
            method="bca",
            size=1.0 - alpha,
        )
    except (ValueError, FloatingPointError, RuntimeError):
        ci = bs.conf_int(
            func=metric_fn,
            reps=n_resamples,
            method="percentile",
            size=1.0 - alpha,
        )
        method = f"{method}_percentile"

    pe = float(metric_fn(x=arr))

    # Estimate SE from CI width: SE ≈ (upper - lower) / (2 * z_alpha)
    ci_lower = float(ci[0, 0])
    ci_upper = float(ci[1, 0])
    z = 1.96  # z_{0.025} for 95% CI
    se = (ci_upper - ci_lower) / (2 * z) if ci_upper > ci_lower else 0.0

    return {
        "point_estimate": pe,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "se": se,
        "n_trades": n,
        "method": method,
    }


def _omega_metric(x: np.ndarray) -> float:
    """Omega ratio for bootstrap — accepts keyword arg ``x``."""
    gains = float(np.sum(np.maximum(x, 0)))
    losses = float(np.sum(np.maximum(-x, 0)))
    # Cap at 1e6 to avoid inf which poisons BCa jackknife
    return min(gains / losses, 1e6) if losses > 1e-12 else 1e6


def _rachev_metric(x: np.ndarray) -> float:
    """Rachev ratio for bootstrap — accepts keyword arg ``x``."""
    result = compute_rachev(x.tolist())
    return result if result is not None else 0.0


def _pf_metric(x: np.ndarray) -> float:
    """Profit factor for bootstrap — accepts keyword arg ``x``."""
    gross_profit = float(np.sum(x[x > 0]))
    gross_loss = float(np.abs(np.sum(x[x < 0])))
    return min(gross_profit / gross_loss, 1e6) if gross_loss > 1e-12 else 1e6


def _total_return_metric(x: np.ndarray) -> float:
    """Total return for bootstrap — accepts keyword arg ``x``."""
    return float(np.sum(x))


def run_bootstrap_validation(
    signal_data: pl.DataFrame,
    cpcv_folds: list[tuple[np.ndarray, np.ndarray]],
    surviving_barriers: list[str],
    *,
    alpha: float = 0.05,
    min_trades: int = 100,
) -> pl.DataFrame:
    """Run bootstrap CIs on pooled OOS returns for surviving barriers.

    For each barrier that survived Stage 2 (PBO < 0.50):
    - Pool ALL OOS trades across CPCV folds
    - Compute BCa CIs for: Omega, Rachev, PF, total_return (DISTRIBUTIONAL only)
    - Reject if: Omega CI lower < 1.0 OR Rachev CI lower < 0.30

    Parameters
    ----------
    signal_data : pl.DataFrame
        Full signal data with columns: barrier_id, signal_idx, return_pct.
    cpcv_folds : list of (train_idx, test_idx) pairs.
    surviving_barriers : list[str]
        Barrier IDs with PBO < 0.50 from Stage 2.
    alpha : float
        Significance level for CIs.
    min_trades : int
        Minimum pooled OOS trades for stable CIs. Barriers with fewer
        are flagged ``low_power=True``.

    Returns
    -------
    pl.DataFrame with CI columns per barrier per metric.
    """
    # Pool all OOS test indices
    oos_indices = set()
    for _train_idx, test_idx in cpcv_folds:
        oos_indices.update(test_idx.tolist())

    oos_df = signal_data.filter(
        pl.col("signal_idx").is_in(oos_indices)
        & pl.col("barrier_id").is_in(surviving_barriers)
    )

    metrics = {
        "omega": _omega_metric,
        "rachev": _rachev_metric,
        "pf": _pf_metric,
        "total_return": _total_return_metric,
    }

    rows = []
    for bid in surviving_barriers:
        barrier_df = oos_df.filter(pl.col("barrier_id") == bid)
        returns = barrier_df["return_pct"].to_list()
        n = len(returns)
        low_power = n < min_trades

        row: dict = {
            "barrier_id": bid,
            "n_oos_trades": n,
            "low_power": low_power,
        }

        for metric_name, metric_fn in metrics.items():
            ci_result = compute_bootstrap_ci(
                returns, metric_fn, alpha=alpha,
            )
            row[f"{metric_name}_point"] = ci_result["point_estimate"]
            row[f"{metric_name}_ci_lower"] = ci_result["ci_lower"]
            row[f"{metric_name}_ci_upper"] = ci_result["ci_upper"]
            row[f"{metric_name}_se"] = ci_result["se"]
            row[f"{metric_name}_method"] = ci_result["method"]

        # Rejection gates
        row["omega_rejects"] = row["omega_ci_lower"] < 1.0
        row["rachev_rejects"] = row["rachev_ci_lower"] < 0.30
        row["rejected"] = row["omega_rejects"] or row["rachev_rejects"]

        rows.append(row)

    return pl.DataFrame(rows) if rows else pl.DataFrame()


# ---- Stage 4: Stability Synthesis ----


def build_stability_matrix(
    fold_df: pl.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Reshape fold results into moocore-compatible format.

    Uses ONLY distributional metrics (order-independent): omega, rachev,
    total_return. Sequential metrics (CDaR, max_drawdown) are excluded
    because their values depend on trade order, making cross-fold
    Vorob'ev comparison unreliable. Profit_factor excluded because
    moocore EAF/Vorob'ev supports at most 3D, and PF correlates
    highly with Omega.

    Parameters
    ----------
    fold_df : pl.DataFrame
        Concatenated results from all WFO folds. Must have columns:
        barrier_id, fold_id, omega, rachev, total_return.

    Returns
    -------
    (matrix, sets, barrier_ids) where:
    - matrix: (N, 3) array [omega, rachev, total_return]
    - sets: (N,) array of fold_id per row
    - barrier_ids: list of unique barrier IDs (row ordering)
    """
    required = {"barrier_id", "fold_id", "omega", "rachev", "total_return"}
    missing = required - set(fold_df.columns)
    if missing:
        msg = f"Missing columns for stability matrix: {missing}"
        raise ValueError(msg)

    sorted_df = fold_df.sort(["barrier_id", "fold_id"])

    matrix = sorted_df.select(
        ["omega", "rachev", "total_return"],
    ).to_numpy().astype(float)

    sets = sorted_df["fold_id"].to_numpy().astype(int)
    barrier_ids = sorted_df["barrier_id"].to_list()

    return matrix, sets, barrier_ids


def _vorob_worker(neg_matrix, sets, ref, result_dict):
    """Worker function for Vorob'ev computation (runs in subprocess).

    Writes results to a shared dict (multiprocessing.Manager) since
    multiprocessing.Process does not return values.
    """
    import moocore

    vt = moocore.vorob_t(neg_matrix, sets, ref=ref)
    vd = moocore.vorob_dev(neg_matrix, sets, ref=ref)
    hv_per_fold = moocore.apply_within_sets(
        neg_matrix, sets, moocore.hypervolume, ref=ref,
    )
    result_dict["vt"] = dict(vt)  # Convert moocore result to plain dict
    result_dict["vd"] = float(vd)
    result_dict["hv_list"] = hv_per_fold.tolist()


def compute_vorob_stability(
    matrix: np.ndarray,
    sets: np.ndarray,
    ref: np.ndarray | None = None,
    timeout: int = 60,
) -> dict:
    """Compute Vorob'ev stability metrics across WFO folds.

    CRITICAL: moocore assumes minimization. All 3 columns (omega, rachev,
    total_return) are benefit metrics → must negate before calling moocore.
    moocore EAF/Vorob'ev supports at most 3D datasets.

    The moocore EAF computation (eaf3d → find_all_promoters) can degenerate
    on certain input configurations, hanging indefinitely. A timeout guard
    runs the computation in a subprocess that can be killed (SIGTERM) if it
    exceeds the time limit. multiprocessing.Process is used instead of
    ProcessPoolExecutor because executor.shutdown(wait=True) blocks on stuck
    C-level code — Process.terminate() sends SIGTERM immediately.

    INTERPRETING VOROB'EV DEVIATION (VD)
    ------------------------------------
    VD measures the expected hypervolume of the symmetric difference between
    the Vorob'ev expectation and each fold's attained set (Binois et al. 2015,
    "Quantifying uncertainty on Pareto fronts with Gaussian process conditional
    simulations"). It is reported in *raw objective-space units* — so its
    absolute scale depends on the magnitude of the objective columns.

    Extreme VD values (>100 or >1000) arise from:
    1. **Non-overlapping fold fronts**: Folds with disjoint Pareto regions
       produce large symmetric-difference hypervolume. Common with small
       n_trades per fold or highly regime-dependent barrier performance.
    2. **Objective magnitude**: If omega ranges [0.5, 5.0] and total_return
       ranges [−0.01, 0.01], the raw VD reflects the unbounded omega axis.
    3. **Sparse fold coverage**: Few barriers surviving per fold means few
       front points, producing noisy hypervolume estimates.

    NORMALIZATION (FUTURE IMPROVEMENT): Normalize objectives to [0, 1]
    before computing VD to make deviations comparable across combos and
    directions. Use ``_flip_to_minimize()`` + per-column min/max scaling.
    Currently tracked as a known improvement — the raw VD still correctly
    rank-orders combos within the same analysis run because all combos
    share the same objective scales.

    For combo-level diagnostics, VD > 10.0 is flagged as ``vorob_unstable``
    in Tier 2 JSONL summaries. This does not disqualify a combo but signals
    that its fold-to-fold Pareto stability is poor.

    Parameters
    ----------
    matrix : np.ndarray
        (N, 3) array of [omega, rachev, total_return].
    sets : np.ndarray
        (N,) fold ID per row.
    ref : np.ndarray or None
        Reference point for hypervolume. If None, uses zeros (which after
        negation = worst possible performance).
    timeout : int
        Maximum seconds for moocore computation. Default 60.

    Returns
    -------
    dict with: vorob_threshold, vorob_deviation, hv_per_fold, hv_cv, avg_hyp.

    Raises
    ------
    TimeoutError
        If moocore computation exceeds timeout.
    """
    import multiprocessing

    from rangebar_patterns.eval.ranking import _flip_to_minimize

    # All 4 metrics are benefits (higher = better) → type=1
    types = np.ones(matrix.shape[1], dtype=int)
    neg_matrix = _flip_to_minimize(matrix, types)

    if ref is None:
        ref = np.zeros(matrix.shape[1])

    # Run moocore in a subprocess with timeout — the C code in
    # find_all_promoters can hang indefinitely on degenerate inputs
    # and cannot be interrupted by Python signal handlers.
    # multiprocessing.Process + terminate() guarantees cleanup.
    mgr = multiprocessing.Manager()
    result_dict = mgr.dict()
    proc = multiprocessing.Process(
        target=_vorob_worker,
        args=(neg_matrix, sets, ref, result_dict),
    )
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=5)
        mgr.shutdown()
        raise TimeoutError(
            f"moocore Vorob'ev computation timed out after {timeout}s "
            f"(matrix shape={matrix.shape}, n_sets={len(np.unique(sets))})"
        )

    # Read results from Manager proxy BEFORE shutdown — accessing proxy
    # objects after mgr.shutdown() raises FileNotFoundError because the
    # Manager's Unix socket is already removed.
    has_result = "vt" in result_dict
    if has_result:
        vt = dict(result_dict["vt"])  # Copy from proxy to plain dict
        vd = float(result_dict["vd"])
        hv_per_fold = np.array(list(result_dict["hv_list"]))

    mgr.shutdown()

    if not has_result:
        raise RuntimeError("Vorob'ev worker failed without producing results")

    hv_mean = float(np.mean(hv_per_fold))
    hv_std = float(np.std(hv_per_fold))
    hv_cv = hv_std / hv_mean if hv_mean > 1e-12 else float("inf")

    return {
        "vorob_threshold": float(vt["threshold"]),
        "vorob_deviation": float(vd),
        "avg_hyp": float(vt["avg_hyp"]),
        "hv_per_fold": hv_per_fold.tolist(),
        "hv_cv": hv_cv,
    }


def detect_regimes(
    signal_df: pl.DataFrame,
    n_regimes: int = config.WF_N_REGIMES,
) -> np.ndarray:
    """Detect market regimes using HMM on lookback features.

    Uses lookback_hurst as primary feature (discriminates mean-reverting
    H<0.5, random-walk H~0.5, trending H>0.5). Falls back to
    lookback_garman_klass_vol if hurst unavailable.

    NOT used for barrier selection — only diagnostic reporting.

    Parameters
    ----------
    signal_df : pl.DataFrame
        Must have signal-level features (lookback_hurst or
        lookback_garman_klass_vol).
    n_regimes : int
        Number of HMM states.

    Returns
    -------
    np.ndarray of regime labels (0, 1, ..., n_regimes-1) per signal.
    """
    from hmmlearn.hmm import GaussianHMM

    # Select feature
    if "lookback_hurst" in signal_df.columns:
        feature = signal_df["lookback_hurst"].to_numpy().astype(float)
    elif "lookback_garman_klass_vol" in signal_df.columns:
        feature = signal_df["lookback_garman_klass_vol"].to_numpy().astype(float)
    else:
        # No suitable feature — assign all to regime 0
        return np.zeros(len(signal_df), dtype=int)

    # Handle NaN: fill with median
    valid = ~np.isnan(feature)
    if valid.sum() < n_regimes * 10:
        return np.zeros(len(signal_df), dtype=int)

    median_val = float(np.median(feature[valid]))
    feature = np.where(valid, feature, median_val)

    X = feature.reshape(-1, 1)

    hmm = GaussianHMM(
        n_components=n_regimes,
        covariance_type="diag",
        n_iter=100,
        random_state=42,
    )
    hmm.fit(X)
    labels = hmm.predict(X)

    return labels


def compute_gt_composite(
    omega: float,
    dsr: float,
    pbo: float,
    max_drawdown: float,
    capital_threshold: float = 0.15,
) -> float:
    """GT-composite score embedding anti-overfitting into ranking.

    GT = Omega × min(1, |DSR|) × (1 - PBO) × max(0, 1 - MaxDD/capital)

    Components:
    - Omega: distribution shape (from OOS evaluation)
    - DSR: Deflated Sharpe Ratio. n_trials = number of Stage 4 survivors
      (NOT 434 barrier grid — CPCV already filtered to survivors).
    - PBO: Probability of Backtest Overfitting (from Stage 2 CPCV)
    - MaxDD: SEQUENTIAL metric — empirical per-fold, NOT bootstrapped

    Higher = better + more robust.
    """
    dsr_term = min(1.0, abs(dsr))
    pbo_term = max(0.0, 1.0 - pbo)
    dd_term = max(0.0, 1.0 - max_drawdown / capital_threshold)

    return omega * dsr_term * pbo_term * dd_term


# ---- Utility ----


def parse_barrier_id(barrier_id: str) -> BarrierParams:
    """Parse barrier_id string into structured parameters.

    Format: p{phase1}_slt{sl_tight*100:03d}_mb{max_bars}
    Examples: p5_slt010_mb50, p0_slt050_mb100, p3_slt000_mb20
    """
    m = re.match(r"^p(\d+)_slt(\d{3})_mb(\d+)$", barrier_id)
    if not m:
        msg = f"Invalid barrier_id format: {barrier_id!r}"
        raise ValueError(msg)
    return BarrierParams(
        phase1_bars=int(m.group(1)),
        sl_tight_mult=int(m.group(2)) / 100.0,
        max_bars=int(m.group(3)),
    )
