"""Signal temporal regularity via KDE peak-finding.

Evaluates whether trade signals are temporally regular (evenly distributed)
or clustered in bursts. Uses Gaussian KDE with Scott's rule bandwidth to
smooth timestamps into a density curve, finds peaks (cluster centers), and
computes the CV (coefficient of variation) of inter-peak distances.

Low kde_peak_cv = regular signal spacing (good).
High kde_peak_cv = irregular bursts (crash-only, pump-only patterns).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from __future__ import annotations

import json

import numpy as np
from scipy.signal import find_peaks
from scipy.stats import gaussian_kde

from rangebar_patterns.config import MIN_TRADES_REGULARITY
from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_signal_regularity(
    timestamps_ms: list[int],
    min_trades: int = MIN_TRADES_REGULARITY,
) -> dict | None:
    """Compute signal temporal regularity metrics.

    Args:
        timestamps_ms: Trade entry timestamps in milliseconds.
        min_trades: Minimum trades for meaningful KDE.

    Returns:
        Dict with kde_peak_cv, n_peaks, raw_iat_cv, temporal_coverage.
        None if insufficient data.
    """
    if len(timestamps_ms) < min_trades:
        return None

    ts = np.array(sorted(timestamps_ms), dtype=np.float64)
    ts_range = ts[-1] - ts[0]
    if ts_range <= 0:
        return None

    # Normalize to [0, 1] for numerical stability
    ts_norm = (ts - ts[0]) / ts_range

    # Raw inter-arrival time CV (naive baseline)
    iats = np.diff(ts)
    raw_iat_cv = float(np.std(iats) / np.mean(iats)) if np.mean(iats) > 0 else None

    # KDE with Scott/4 bandwidth — Scott's rule over-smooths to 1-2 peaks;
    # dividing by 4 resolves 3-8 temporal clusters across multi-year data
    try:
        kde_scott = gaussian_kde(ts_norm, bw_method="scott")
        bw = kde_scott.factor * 0.25
        kde = gaussian_kde(ts_norm, bw_method=bw)
    except np.linalg.LinAlgError:
        return None

    # Evaluate KDE on a grid
    n_grid = min(1000, max(200, len(ts) * 2))
    grid = np.linspace(0, 1, n_grid)
    density = kde(grid)

    # Find peaks in density curve
    # Prominence threshold: 10% of max density to avoid noise peaks
    prominence = 0.10 * density.max()
    peak_indices, _ = find_peaks(density, prominence=prominence)

    n_peaks = len(peak_indices)

    if n_peaks < 2:
        # Single peak or no peaks — can't compute inter-peak CV
        kde_peak_cv = None
    else:
        peak_positions = grid[peak_indices]
        inter_peak_distances = np.diff(peak_positions)
        mean_ipd = np.mean(inter_peak_distances)
        kde_peak_cv = (
            float(np.std(inter_peak_distances) / mean_ipd)
            if mean_ipd > 0 else None
        )

    # Temporal coverage: fraction of time range with signal activity
    # Divide timeline into 20 equal bins, count non-empty bins
    n_bins = 20
    bin_edges = np.linspace(ts[0], ts[-1], n_bins + 1)
    bin_counts = np.histogram(ts, bins=bin_edges)[0]
    temporal_coverage = float(np.sum(bin_counts > 0) / n_bins)

    return {
        "kde_peak_cv": round(kde_peak_cv, 6) if kde_peak_cv is not None else None,
        "n_peaks": n_peaks,
        "raw_iat_cv": round(raw_iat_cv, 6) if raw_iat_cv is not None else None,
        "temporal_coverage": round(temporal_coverage, 4),
        "kde_bandwidth": round(float(kde.factor), 6),
    }


def main():
    rd = results_dir()
    input_file = rd / "trade_returns.jsonl"
    output_file = rd / "signal_regularity_rankings.jsonl"

    trade_data = load_jsonl(input_file)
    print(f"Loaded {len(trade_data)} configs from {input_file}")

    results = []
    n_valid = 0
    for data in trade_data:
        config_id = data["config_id"]
        n_trades = data.get("n_trades", 0)
        timestamps = data.get("timestamps_ms", [])

        null_result = {
            "config_id": config_id, "n_trades": n_trades,
            "kde_peak_cv": None, "n_peaks": None,
            "raw_iat_cv": None, "temporal_coverage": None,
        }

        if data.get("error") or n_trades < MIN_TRADES_REGULARITY:
            results.append(null_result)
            continue

        reg = compute_signal_regularity(timestamps)
        if reg is None:
            results.append(null_result)
            continue

        n_valid += 1
        results.append({"config_id": config_id, "n_trades": n_trades, **reg})

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Distribution summary
    valid_cv = [r["kde_peak_cv"] for r in results
                if r.get("kde_peak_cv") is not None]
    valid_cov = [r["temporal_coverage"] for r in results
                 if r.get("temporal_coverage") is not None]

    print(f"\nResults: {len(results)} configs, {n_valid} valid")
    if valid_cv:
        arr_cv = np.array(valid_cv)
        print(f"  KDE peak CV: min={arr_cv.min():.4f}, "
              f"p50={np.median(arr_cv):.4f}, max={arr_cv.max():.4f}")
    if valid_cov:
        arr_cov = np.array(valid_cov)
        print(f"  Temporal coverage: min={arr_cov.min():.4f}, "
              f"p50={np.median(arr_cov):.4f}, max={arr_cov.max():.4f}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
