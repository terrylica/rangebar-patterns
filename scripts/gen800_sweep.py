"""Gen800: Brute-force regime-conditioned signal sweep.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

Python-only sweep (no SQL) because ATR-Adaptive Laguerre RSI is Python-computed.
Sweeps 288 Laguerre configs × 300 inner combos = 86,400 total configs on SOLUSDT @750.

Ranking target: shortest maximum stagnation (max_underwater_bars ascending).
Thesis: regime-aware signals avoid unfavorable periods → compressed drawdown durations.

Usage:
    uv run -p 3.13 python scripts/gen800_sweep.py
    uv run -p 3.13 python scripts/gen800_sweep.py --dry-run     # First 10 Laguerre configs
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import polars as pl

# ---- Grid Definition ----

LAGUERRE_GRID = {
    "atr_period": [14, 32, 64, 100],
    "level_up": [0.60, 0.65, 0.70, 0.75, 0.80, 0.85],
    "level_down": [0.10, 0.15, 0.25, 0.40],
    "adaptive_offset": [0.50, 0.75, 1.00],
}

PATTERNS = ["2down", "udd", "dud", "3down", "wl1d"]

REGIME_GATES = {
    "bullish_only": lambda regimes: regimes == 2,
    "not_bearish": lambda regimes: regimes >= 1,
    "any_regime": lambda regimes: np.ones(len(regimes), dtype=bool),
}

SYMBOL = "SOLUSDT"
THRESHOLD = 750
BAR_RANGE = THRESHOLD / 100_000.0  # 0.0075

RESULTS_DIR = Path("results/eval/gen800")
RESULTS_FILE = RESULTS_DIR / "gen800_sweep.jsonl"


def _build_laguerre_configs() -> list[dict]:
    """Generate all Laguerre parameter combinations."""
    keys = list(LAGUERRE_GRID.keys())
    values = [LAGUERRE_GRID[k] for k in keys]
    configs = []
    for combo in itertools.product(*values):
        configs.append(dict(zip(keys, combo)))
    return configs


def _load_data():
    """Load SOLUSDT @750 range bar data from ClickHouse."""
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    bt_path = str(Path(__file__).resolve().parent.parent / "backtest" / "backtesting_py")
    if bt_path not in sys.path:
        sys.path.insert(0, bt_path)
    from data_loader import load_range_bars

    print(f"Loading {SYMBOL} @{THRESHOLD}dbps...")
    df = load_range_bars(symbol=SYMBOL, threshold=THRESHOLD)
    print(f"  Loaded {len(df)} bars")
    return df


def _detect_patterns(direction, opens, highs, lows, closes):
    """Pre-compute all pattern masks.

    Imports pattern detectors from gen600_strategy.py.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest" / "backtesting_py"))
    from gen600_strategy import PATTERN_DETECTORS, _compute_opposite_wick_pct, _detect_wl1d

    masks = {}
    for name, detector in PATTERN_DETECTORS.items():
        masks[name] = detector(direction)

    # Wickless patterns need wick_pct
    wick_pct = _compute_opposite_wick_pct(opens, highs, lows, closes)
    masks["wl1d"] = _detect_wl1d(direction, wick_pct)

    return masks


def _process_laguerre_config(
    laguerre_params: dict,
    ohlcv: dict,
    pattern_masks: dict[str, np.ndarray],
    barrier_configs_raw: list[dict],
    n_bars: int,
) -> list[dict]:
    """Process one Laguerre config: compute regimes, then sweep inner grid.

    Returns list of NDJSON-ready result dicts.
    """
    import pandas as pd

    from rangebar_patterns.barrier_sim import BarrierConfig, simulate_barriers
    from rangebar_patterns.eval.omega import compute_omega
    from rangebar_patterns.laguerre import LaguerreRegimeConfig, compute_laguerre_regimes

    # Build pandas DataFrame for Laguerre (needs Title-case OHLCV + DatetimeIndex)
    df = pd.DataFrame({
        "Open": ohlcv["opens"],
        "High": ohlcv["highs"],
        "Low": ohlcv["lows"],
        "Close": ohlcv["closes"],
        "Volume": ohlcv["volumes"],
    })
    df.index = pd.to_datetime(ohlcv["timestamps_ms"], unit="ms")

    config = LaguerreRegimeConfig(
        atr_period=laguerre_params["atr_period"],
        smoothing_period=5,
        level_up=laguerre_params["level_up"],
        level_down=laguerre_params["level_down"],
        adaptive_offset=laguerre_params["adaptive_offset"],
    )

    try:
        _rsi_values, regime_labels = compute_laguerre_regimes(df, config)
    except (ValueError, TypeError, RuntimeError) as e:
        # Laguerre can fail on: insufficient data (ValueError),
        # column mismatch (TypeError), or numerical issues (RuntimeError)
        return [{
            "status": "error",
            "laguerre_config": laguerre_params,
            "error": str(e),
        }]

    # Warmup: exclude signals within warmup window
    warmup = max(config.atr_period, 20) + 10

    # Build BarrierConfig objects
    barrier_cfgs = [BarrierConfig(**bc) for bc in barrier_configs_raw]

    results = []
    laguerre_id = (
        f"atr{config.atr_period}_up{int(config.level_up*100)}"
        f"_dn{int(config.level_down*100)}_ao{int(config.adaptive_offset*100)}"
    )

    for pattern_name in PATTERNS:
        pattern_mask = pattern_masks[pattern_name]

        for gate_name, gate_fn in REGIME_GATES.items():
            regime_mask = gate_fn(regime_labels)

            # Combine: pattern + regime + warmup
            combined = pattern_mask & regime_mask
            combined[:warmup] = False

            signal_indices = np.where(combined)[0]
            n_signals = len(signal_indices)

            if n_signals == 0:
                results.append({
                    "status": "skipped",
                    "laguerre_id": laguerre_id,
                    "laguerre_config": laguerre_params,
                    "pattern": pattern_name,
                    "regime_gate": gate_name,
                    "n_signals": 0,
                })
                continue

            # Simulate barriers for all signals × all barrier configs
            trades_df = simulate_barriers(
                ohlcv["opens"], ohlcv["highs"], ohlcv["lows"], ohlcv["closes"],
                signal_indices, barrier_cfgs,
            )

            if trades_df.is_empty():
                results.append({
                    "status": "skipped",
                    "laguerre_id": laguerre_id,
                    "laguerre_config": laguerre_params,
                    "pattern": pattern_name,
                    "regime_gate": gate_name,
                    "n_signals": n_signals,
                    "reason": "no_complete_trades",
                })
                continue

            # Evaluate per barrier config
            for bid in trades_df["barrier_id"].unique().sort().to_list():
                barrier_trades = trades_df.filter(pl.col("barrier_id") == bid)
                returns = barrier_trades["return_pct"].to_numpy()
                n_trades = len(returns)

                if n_trades < 5:
                    continue

                arr = returns.astype(float)
                wins = float(np.sum(arr > 0))
                gross_profit = float(np.sum(arr[arr > 0]))
                gross_loss = float(np.abs(np.sum(arr[arr < 0])))

                # Profit factor
                if gross_loss > 1e-12:
                    pf = min(gross_profit / gross_loss, 10.0)
                elif gross_profit > 1e-12:
                    pf = 10.0
                else:
                    pf = float("nan")

                # Omega
                omega = compute_omega(arr.tolist())

                # Bar-level equity curve stagnation (vectorized)
                # Place each trade's return at its absolute exit bar to build
                # a per-bar equity array (n_bars elements, mostly zeros).
                # This measures actual time underwater, not just trade count.
                sig_idx_arr = barrier_trades["signal_idx"].to_numpy()
                exit_bar_fwd = barrier_trades["exit_bar"].to_numpy()
                ret_arr = barrier_trades["return_pct"].to_numpy()
                exit_bar_abs = signal_indices[sig_idx_arr] + 1 + exit_bar_fwd
                valid = exit_bar_abs < n_bars
                bar_returns = np.zeros(n_bars, dtype=float)
                np.add.at(bar_returns, exit_bar_abs[valid], ret_arr[valid])

                cum = np.cumsum(bar_returns)
                running_max = np.maximum.accumulate(cum)
                drawdowns = running_max - cum
                mdd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

                underwater = drawdowns > 1e-12
                underwater_ratio = float(np.mean(underwater))

                if np.any(underwater):
                    changes = np.diff(underwater.astype(int), prepend=0, append=0)
                    starts = np.where(changes == 1)[0]
                    ends = np.where(changes == -1)[0]
                    durations = ends - starts
                    max_underwater_bars = int(np.max(durations))
                    avg_recovery_bars = float(np.mean(durations))
                else:
                    max_underwater_bars = 0
                    avg_recovery_bars = 0.0

                # Exit type distribution
                exit_counts = barrier_trades["exit_type"].value_counts()
                exit_dist = {
                    row["exit_type"]: row["count"]
                    for row in exit_counts.to_dicts()
                }

                config_id = f"{laguerre_id}__{pattern_name}__{gate_name}__{bid}"

                results.append({
                    "status": "ok",
                    "config_id": config_id,
                    "laguerre_id": laguerre_id,
                    "laguerre_config": laguerre_params,
                    "pattern": pattern_name,
                    "regime_gate": gate_name,
                    "barrier_id": bid,
                    "n_signals": n_signals,
                    "n_trades": n_trades,
                    "win_rate": round(wins / n_trades, 4),
                    "profit_factor": round(pf, 4) if not np.isnan(pf) else None,
                    "omega": round(omega, 4) if omega is not None else None,
                    "total_return": round(float(arr.sum()), 6),
                    "avg_return": round(float(arr.mean()), 6),
                    "max_drawdown": round(mdd, 6),
                    "underwater_ratio": round(underwater_ratio, 4),
                    "max_underwater_bars": max_underwater_bars,
                    "avg_recovery_bars": round(avg_recovery_bars, 2),
                    "exit_dist": exit_dist,
                    "symbol": SYMBOL,
                    "threshold": THRESHOLD,
                })

    return results


def main():
    parser = argparse.ArgumentParser(description="Gen800 regime-conditioned sweep")
    parser.add_argument("--dry-run", action="store_true", help="Process first 10 Laguerre configs only")
    parser.add_argument("--workers", type=int, default=12, help="Number of parallel workers")
    args = parser.parse_args()

    # 1. Load data ONCE
    df = _load_data()

    opens = np.array(df["Open"], dtype=float)
    highs = np.array(df["High"], dtype=float)
    lows = np.array(df["Low"], dtype=float)
    closes = np.array(df["Close"], dtype=float)
    volumes = np.array(df["Volume"], dtype=float)
    timestamps_ms = np.array(df["timestamp_ms"], dtype=np.int64)
    n_bars = len(opens)

    # Direction for pattern detection
    direction = (closes > opens).astype(int)

    # 2. Pre-compute pattern masks
    print("Computing pattern masks...")
    pattern_masks = _detect_patterns(direction, opens, highs, lows, closes)
    for name, mask in pattern_masks.items():
        print(f"  {name}: {mask.sum()} raw signals")

    # 3. Load barrier configs
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen800.barriers import load_barrier_configs

    barrier_configs_raw = load_barrier_configs(bar_range=BAR_RANGE)
    print(f"Barrier configs: {len(barrier_configs_raw)}")

    # 4. Build Laguerre grid
    laguerre_configs = _build_laguerre_configs()
    if args.dry_run:
        laguerre_configs = laguerre_configs[:10]
    print(f"Laguerre configs: {len(laguerre_configs)}")

    total_combos = len(laguerre_configs) * len(PATTERNS) * len(REGIME_GATES) * len(barrier_configs_raw)
    print(f"Total sweep: {total_combos:,} configs")

    # Package OHLCV as dict for pickling to workers
    ohlcv = {
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": volumes,
        "timestamps_ms": timestamps_ms,
    }

    # 5. Sweep
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    n_ok = 0
    n_skipped = 0
    n_error = 0
    n_laguerre_done = 0

    with open(RESULTS_FILE, "w") as f:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {}
            for lc in laguerre_configs:
                future = executor.submit(
                    _process_laguerre_config,
                    lc, ohlcv, pattern_masks, barrier_configs_raw, n_bars,
                )
                futures[future] = lc

            for future in as_completed(futures):
                lc = futures[future]
                n_laguerre_done += 1
                try:
                    results = future.result()
                    for row in results:
                        f.write(json.dumps(row, default=str) + "\n")
                        if row.get("status") == "ok":
                            n_ok += 1
                        elif row.get("status") == "skipped":
                            n_skipped += 1
                        elif row.get("status") == "error":
                            n_error += 1
                    f.flush()
                except (ValueError, TypeError, RuntimeError, OSError) as e:
                    n_error += 1
                    f.write(json.dumps({
                        "status": "error",
                        "laguerre_config": lc,
                        "error": str(e),
                    }) + "\n")
                    f.flush()

                elapsed = time.time() - t0
                rate = n_laguerre_done / elapsed if elapsed > 0 else 0
                eta = (len(laguerre_configs) - n_laguerre_done) / rate if rate > 0 else 0
                print(
                    f"  [{n_laguerre_done}/{len(laguerre_configs)}] "
                    f"ok={n_ok} skip={n_skipped} err={n_error} "
                    f"rate={rate:.1f} lag/s ETA={eta:.0f}s",
                    flush=True,
                )

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Results: {n_ok} ok, {n_skipped} skipped, {n_error} errors")
    print(f"  Output: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
