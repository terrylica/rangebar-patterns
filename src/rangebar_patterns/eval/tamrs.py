"""TAMRS (Tail-Adjusted Mean Reversion Score) composite metric.

TAMRS = Rachev(alpha) * min(1, |SL_emp| / CDaR(alpha)) * min(1, TP_emp / TP_OU)

Joins Rachev rankings, CDaR rankings, and OU calibration into a single
composite score per config. Replaces Kelly Criterion as the primary ranker
because Kelly selects penny-picker configs (high WR, asymmetric tails).

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/16
"""

from __future__ import annotations

import json

from rangebar_patterns.eval._io import load_jsonl, results_dir


def compute_tamrs(
    rachev: float | None,
    sl_cdar_ratio: float | None,
    ou_barrier_ratio: float | None,
) -> float | None:
    """TAMRS = rachev * sl_cdar_ratio * ou_barrier_ratio. None if any input is None."""
    if any(v is None for v in (rachev, sl_cdar_ratio, ou_barrier_ratio)):
        return None
    return rachev * sl_cdar_ratio * ou_barrier_ratio


def main():
    rd = results_dir()
    rachev_file = rd / "rachev_rankings.jsonl"
    cdar_file = rd / "cdar_rankings.jsonl"
    ou_file = rd / "ou_calibration.jsonl"
    moments_file = rd / "moments.jsonl"
    output_file = rd / "tamrs_rankings.jsonl"

    rachev_data = {r["config_id"]: r for r in load_jsonl(rachev_file)}
    cdar_data = {r["config_id"]: r for r in load_jsonl(cdar_file)}
    ou_records = load_jsonl(ou_file)
    kelly_map = {r["config_id"]: r.get("kelly_fraction") for r in load_jsonl(moments_file)}

    if not ou_records or not ou_records[0].get("mean_reverting"):
        ou_ratio = None
        print("WARNING: OU calibration failed, ou_barrier_ratio will be None for all configs")
    else:
        ou_ratio = ou_records[0].get("ou_barrier_ratio")

    config_ids = list(rachev_data.keys())
    print(f"Joining {len(config_ids)} configs: rachev + cdar + ou")

    results = []
    n_valid = 0
    for config_id in config_ids:
        rr = rachev_data.get(config_id, {}).get("rachev_ratio")
        sl_cdar = cdar_data.get(config_id, {}).get("sl_cdar_ratio")
        n_trades = rachev_data.get(config_id, {}).get("n_trades", 0)

        tamrs = compute_tamrs(rr, sl_cdar, ou_ratio)
        if tamrs is not None:
            n_valid += 1

        results.append({
            "config_id": config_id,
            "n_trades": n_trades,
            "tamrs": round(tamrs, 6) if tamrs is not None else None,
            "rachev_ratio": rr,
            "sl_cdar_ratio": sl_cdar,
            "ou_barrier_ratio": ou_ratio,
            "kelly_fraction": kelly_map.get(config_id),
        })

    with open(output_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    valid_tamrs = [r["tamrs"] for r in results if r["tamrs"] is not None]
    print(f"\nResults: {len(results)} configs, {n_valid} valid TAMRS")
    if valid_tamrs:
        print(f"  TAMRS range: [{min(valid_tamrs):.6f}, {max(valid_tamrs):.6f}]")
        import numpy as np

        print(f"  TAMRS median: {np.median(valid_tamrs):.6f}")
        print(f"  TAMRS std: {np.std(valid_tamrs):.6f}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
