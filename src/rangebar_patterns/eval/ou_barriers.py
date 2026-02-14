"""Ornstein-Uhlenbeck barrier calibration with rolling 1000-bar lookback.

Fits OU model to range bar close prices via OLS: dX = a + b*X + eps.
Extracts mean-reversion speed (mu), volatility (sigma), half-life, and
optimal take-profit barrier. The OU barrier ratio = min(1, TP_emp / TP_OU)
penalizes noise-harvesting strategies that use barriers tighter than optimal.

Rolling window approach (per Gemini 3 Pro prescription): for each trade entry,
calibrate OU on the preceding 1000 bars, producing a per-trade ou_barrier_ratio.
Per-config ratio is the median across all trades in that config.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json
import os

import numpy as np

from rangebar_patterns.config import SYMBOL, THRESHOLD_DBPS, TP_EMP
from rangebar_patterns.eval._io import load_jsonl, results_dir

OU_LOOKBACK = 1000


def calibrate_ou(prices: np.ndarray, min_prices: int = 100) -> dict | None:
    """OLS: dX = a + b*X + eps. mu=-b, sigma=std(eps), half_life=ln(2)/mu.

    min_prices=100 is a structural OLS guard, not a tunable research parameter.
    Returns None if not enough data or if the process is not mean-reverting.
    """
    import statsmodels.api as sm

    if len(prices) < min_prices:
        return None
    y = np.diff(prices)
    x = sm.add_constant(prices[:-1])
    model = sm.OLS(y, x).fit()
    mu_dt = -model.params[1]
    if mu_dt <= 0:
        return None  # Not mean-reverting
    sigma_dt = float(np.std(model.resid))
    half_life = float(np.log(2) / mu_dt)
    optimal_tp_abs = sigma_dt * np.sqrt(half_life)
    mean_price = float(np.mean(prices))
    optimal_tp_frac = optimal_tp_abs / mean_price if mean_price > 0 else 0.0
    return {
        "mu_dt": float(mu_dt),
        "sigma_dt": sigma_dt,
        "half_life": half_life,
        "optimal_tp_abs": float(optimal_tp_abs),
        "optimal_tp_frac": optimal_tp_frac,
    }


def ou_barrier_ratio(prices: np.ndarray, empirical_tp_frac: float = TP_EMP) -> float | None:
    """Compute min(1, TP_emp / TP_OU). None if OU calibration fails."""
    cal = calibrate_ou(prices)
    if cal is None or cal["optimal_tp_frac"] <= 0:
        return None
    return float(min(1.0, empirical_tp_frac / cal["optimal_tp_frac"]))


def rolling_ou_ratios(
    bar_timestamps: np.ndarray,
    bar_closes: np.ndarray,
    trade_timestamps: list[int],
    empirical_tp_frac: float = TP_EMP,
    lookback: int = OU_LOOKBACK,
) -> list[float | None]:
    """Compute per-trade OU barrier ratios using rolling lookback windows.

    For each trade entry timestamp, finds the bar index via binary search,
    extracts the preceding `lookback` bars, and runs calibrate_ou().

    Args:
        bar_timestamps: Sorted array of bar timestamps (ms).
        bar_closes: Array of close prices aligned with bar_timestamps.
        trade_timestamps: List of trade entry timestamps (ms).
        empirical_tp_frac: Empirical TP fraction (from config).
        lookback: Number of preceding bars to use for OU calibration.

    Returns:
        List of ou_barrier_ratio per trade (None if calibration fails).
    """
    ratios = []
    for ts in trade_timestamps:
        idx = int(np.searchsorted(bar_timestamps, ts, side="right")) - 1
        if idx < lookback:
            ratios.append(None)
            continue
        window = bar_closes[idx - lookback : idx]
        ratios.append(ou_barrier_ratio(window, empirical_tp_frac))
    return ratios


def _get_ch_client():
    """Create ClickHouse client using env config."""
    import clickhouse_connect

    host = os.environ.get("RANGEBAR_CH_HOST", "localhost")
    database = os.environ.get("RANGEBAR_CH_DATABASE", "rangebar_cache")
    return clickhouse_connect.get_client(host=host, database=database)


def _load_bar_series(symbol: str, threshold: int) -> tuple[np.ndarray, np.ndarray]:
    """Load bar series from TSV cache or ClickHouse.

    Checks /tmp/{symbol}_{threshold}_ts_close.tsv first (avoids SSH issues).
    Falls back to ClickHouse query_arrow if file not found.

    Returns (timestamps_ms, closes) as numpy arrays sorted by time.
    """
    cache_path = f"/tmp/{symbol.lower()}_{threshold}_ts_close.tsv"
    if os.path.exists(cache_path):
        print(f"Loading bar series from cache: {cache_path}")
        data = np.loadtxt(cache_path, dtype=np.float64)
        return data[:, 0].astype(np.int64), data[:, 1]

    print("Cache not found, querying ClickHouse...")
    client = _get_ch_client()
    result = client.query_arrow(
        f"SELECT timestamp_ms, close FROM rangebar_cache.range_bars "
        f"WHERE symbol = '{symbol}' AND threshold_decimal_bps = {threshold} "
        f"ORDER BY timestamp_ms"
    )
    timestamps = result.column("timestamp_ms").to_numpy()
    closes = result.column("close").to_numpy()
    return timestamps, closes


def main():
    rd = results_dir()
    output_file = rd / "ou_calibration.jsonl"
    trade_returns_file = rd / "trade_returns.jsonl"

    symbol = SYMBOL
    threshold = THRESHOLD_DBPS
    tp_emp = TP_EMP

    print(f"Rolling OU calibration for {symbol}@{threshold} (lookback={OU_LOOKBACK})")

    bar_ts, bar_closes = _load_bar_series(symbol, threshold)
    print(f"Loaded {len(bar_ts)} bars")

    # Full-history calibration for reference (kept in output for diagnostics)
    full_cal = calibrate_ou(bar_closes)
    if full_cal:
        full_ratio = (
            min(1.0, tp_emp / full_cal["optimal_tp_frac"])
            if full_cal["optimal_tp_frac"] > 0 else None
        )
        if full_ratio:
            print(f"Full-history OU: half_life={full_cal['half_life']:.0f}, "
                  f"ratio={full_ratio:.6f}")
        else:
            print("Full-history OU: not mean-reverting")

    # Per-config rolling OU
    trade_data = load_jsonl(trade_returns_file)
    print(f"Computing rolling OU for {len(trade_data)} configs...")

    per_config_results = []
    n_valid = 0
    n_mr_trades = 0
    n_total_trades = 0

    for i, cfg in enumerate(trade_data):
        config_id = cfg["config_id"]
        timestamps = cfg.get("timestamps_ms", [])
        n_trades = len(timestamps)
        n_total_trades += n_trades

        if not timestamps:
            per_config_results.append({
                "config_id": config_id,
                "n_trades": 0,
                "ou_barrier_ratio": None,
                "n_mr_trades": 0,
                "median_half_life": None,
            })
            continue

        ratios = rolling_ou_ratios(bar_ts, bar_closes, timestamps, tp_emp)
        valid_ratios = [r for r in ratios if r is not None]
        n_mr_trades += len(valid_ratios)

        if valid_ratios:
            median_ratio = float(np.median(valid_ratios))
            n_valid += 1
        else:
            median_ratio = None

        per_config_results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "ou_barrier_ratio": round(median_ratio, 6) if median_ratio is not None else None,
            "n_mr_trades": len(valid_ratios),
        })

        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(trade_data)} configs processed")

    # Summary record (first line, preserves backward compat for global queries)
    summary = {
        "symbol": symbol,
        "threshold_dbps": threshold,
        "method": "rolling",
        "lookback": OU_LOOKBACK,
        "n_bars": len(bar_ts),
        "n_configs": len(trade_data),
        "n_configs_valid": n_valid,
        "n_total_trades": n_total_trades,
        "n_mr_trades": n_mr_trades,
        "mr_trade_pct": round(n_mr_trades / n_total_trades * 100, 1) if n_total_trades > 0 else 0,
        "empirical_tp_frac": tp_emp,
    }

    # Add full-history reference
    if full_cal:
        summary["full_history_half_life"] = round(full_cal["half_life"], 2)
        summary["full_history_ratio"] = round(full_ratio, 6) if full_ratio else None

    # Add distribution stats for rolling ratios
    all_ratios = [r["ou_barrier_ratio"] for r in per_config_results if r["ou_barrier_ratio"] is not None]
    if all_ratios:
        summary["rolling_ratio_min"] = round(min(all_ratios), 6)
        summary["rolling_ratio_p50"] = round(float(np.median(all_ratios)), 6)
        summary["rolling_ratio_max"] = round(max(all_ratios), 6)
        summary["rolling_ratio_mean"] = round(float(np.mean(all_ratios)), 6)

    with open(output_file, "w") as f:
        f.write(json.dumps(summary) + "\n")
        for r in per_config_results:
            f.write(json.dumps(r) + "\n")

    print(f"\nResults: {n_valid}/{len(trade_data)} configs with valid rolling OU")
    print(f"Mean-reverting trades: {n_mr_trades}/{n_total_trades} ({summary['mr_trade_pct']}%)")
    if all_ratios:
        print(f"Rolling OU ratio: min={min(all_ratios):.6f}, "
              f"p50={np.median(all_ratios):.6f}, max={max(all_ratios):.6f}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
