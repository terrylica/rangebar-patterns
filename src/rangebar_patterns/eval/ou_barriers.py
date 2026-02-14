"""Ornstein-Uhlenbeck barrier calibration.

Fits OU model to range bar close prices via OLS: dX = a + b*X + eps.
Extracts mean-reversion speed (mu), volatility (sigma), half-life, and
optimal take-profit barrier. The OU barrier ratio = min(1, TP_emp / TP_OU)
penalizes noise-harvesting strategies that use barriers tighter than optimal.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json
import os

import numpy as np

from rangebar_patterns.config import SYMBOL, THRESHOLD_DBPS, TP_EMP
from rangebar_patterns.eval._io import results_dir


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


def _get_ch_client():
    """Create ClickHouse client using env config."""
    import clickhouse_connect

    host = os.environ.get("RANGEBAR_CH_HOST", "localhost")
    database = os.environ.get("RANGEBAR_CH_DATABASE", "rangebar_cache")
    return clickhouse_connect.get_client(host=host, database=database)


def main():
    rd = results_dir()
    output_file = rd / "ou_calibration.jsonl"

    symbol = SYMBOL
    threshold = THRESHOLD_DBPS
    tp_emp = TP_EMP

    print(f"Calibrating OU model for {symbol}@{threshold}")

    client = _get_ch_client()
    result = client.query_arrow(
        f"SELECT close FROM rangebar_cache.range_bars "
        f"WHERE symbol = '{symbol}' AND threshold_decimal_bps = {threshold} "
        f"ORDER BY timestamp_ms"
    )
    prices = result.column("close").to_numpy()
    print(f"Loaded {len(prices)} close prices")

    cal = calibrate_ou(prices)
    if cal is None:
        print("ERROR: OU calibration failed (not mean-reverting or insufficient data)")
        record = {
            "symbol": symbol,
            "threshold_dbps": threshold,
            "mean_reverting": False,
            "n_prices": len(prices),
        }
    else:
        ratio = min(1.0, tp_emp / cal["optimal_tp_frac"]) if cal["optimal_tp_frac"] > 0 else None
        record = {
            "symbol": symbol,
            "threshold_dbps": threshold,
            "mean_reverting": True,
            "n_prices": len(prices),
            "mu_dt": round(cal["mu_dt"], 8),
            "sigma_dt": round(cal["sigma_dt"], 8),
            "half_life": round(cal["half_life"], 2),
            "optimal_tp_abs": round(cal["optimal_tp_abs"], 8),
            "optimal_tp_frac": round(cal["optimal_tp_frac"], 8),
            "empirical_tp_frac": tp_emp,
            "ou_barrier_ratio": round(ratio, 6) if ratio is not None else None,
        }
        print(f"  mu_dt: {cal['mu_dt']:.8f}")
        print(f"  sigma_dt: {cal['sigma_dt']:.8f}")
        print(f"  half_life: {cal['half_life']:.2f} bars")
        print(f"  optimal_tp_frac: {cal['optimal_tp_frac']:.8f}")
        print(f"  empirical_tp_frac: {tp_emp}")
        print(f"  ou_barrier_ratio: {ratio:.6f}" if ratio else "  ou_barrier_ratio: None")

    with open(output_file, "w") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
