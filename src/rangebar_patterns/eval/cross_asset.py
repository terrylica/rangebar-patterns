"""Cross-asset robustness metrics from Gen500 sweep data.

Loads per-asset JSONL from logs/gen500/ and computes per-config aggregate
metrics: n_positive_assets, avg_kelly_cross_asset, total_signals.

These metrics feed into ranking.py as additional MetricSpecs for the
Optuna Pareto optimizer.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/17
"""

from __future__ import annotations

import json
import math
from pathlib import Path


def _repo_root() -> Path:
    """Walk up from this file to find pyproject.toml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    msg = "Cannot find repo root (no pyproject.toml found)"
    raise RuntimeError(msg)


def load_gen500_data(
    gen500_dir: Path | None = None,
) -> dict[str, dict[str, dict]]:
    """Load all Gen500 per-asset JSONL files.

    Returns {asset_key: {config_id: record}}.
    asset_key is the filename stem, e.g. "ADAUSDT_500".
    """
    if gen500_dir is None:
        gen500_dir = _repo_root() / "logs" / "gen500"

    if not gen500_dir.exists():
        return {}

    asset_data: dict[str, dict[str, dict]] = {}
    for f in sorted(gen500_dir.glob("*.jsonl")):
        asset_key = f.stem
        records: dict[str, dict] = {}
        with open(f) as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid = d.get("config_id")
                if cid is None:
                    continue
                if d.get("error") or d.get("skipped"):
                    continue
                records[cid] = d
        asset_data[asset_key] = records

    return asset_data


def compute_cross_asset_metrics(
    asset_data: dict[str, dict[str, dict]],
) -> dict[str, dict[str, float | None]]:
    """Compute per-config cross-asset aggregate metrics.

    Returns dict with keys:
        "xa_n_positive": {config_id: count of assets with profit_factor > 1.0}
        "xa_avg_pf": {config_id: mean profit_factor across all tested assets}
        "xa_total_signals": {config_id: sum of signals across all tested assets}
        "xa_consistency": {config_id: fraction of tested assets with PF > 1.0}

    Uses profit_factor (≈ Omega at L=0) instead of Kelly per Issue #17 decision.
    Configs not present in any asset file get None.
    """
    if not asset_data:
        return {
            "xa_n_positive": {},
            "xa_avg_pf": {},
            "xa_total_signals": {},
            "xa_consistency": {},
        }

    # Collect all config_ids across all assets
    all_configs: set[str] = set()
    for records in asset_data.values():
        all_configs.update(records.keys())

    n_assets = len(asset_data)
    xa_n_positive: dict[str, float | None] = {}
    xa_avg_pf: dict[str, float | None] = {}
    xa_total_signals: dict[str, float | None] = {}
    xa_consistency: dict[str, float | None] = {}

    for cid in all_configs:
        pfs: list[float] = []
        total_sigs = 0
        n_pos = 0
        n_tested = 0

        for records in asset_data.values():
            rec = records.get(cid)
            if rec is None:
                continue
            results = rec.get("results", rec)
            pf = results.get("profit_factor")
            signals = results.get("filtered_signals", 0)

            if pf is not None and math.isfinite(pf):
                pfs.append(pf)
                n_tested += 1
                if pf > 1.0:
                    n_pos += 1
            total_sigs += signals or 0

        if n_tested == 0:
            xa_n_positive[cid] = None
            xa_avg_pf[cid] = None
            xa_total_signals[cid] = None
            xa_consistency[cid] = None
        else:
            xa_n_positive[cid] = float(n_pos)
            xa_avg_pf[cid] = sum(pfs) / len(pfs)
            xa_total_signals[cid] = float(total_sigs)
            xa_consistency[cid] = n_pos / n_assets  # fraction of ALL assets

    return {
        "xa_n_positive": xa_n_positive,
        "xa_avg_pf": xa_avg_pf,
        "xa_total_signals": xa_total_signals,
        "xa_consistency": xa_consistency,
    }


def write_cross_asset_rankings(
    metrics: dict[str, dict[str, float | None]],
    output_path: Path | None = None,
) -> Path:
    """Write cross-asset metrics to JSONL for ranking.py consumption.

    Writes results/eval/cross_asset_rankings.jsonl.
    """
    if output_path is None:
        output_path = _repo_root() / "results" / "eval" / "cross_asset_rankings.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge all metrics by config_id
    all_cids = set()
    for values in metrics.values():
        all_cids.update(values.keys())

    with open(output_path, "w") as f:
        for cid in sorted(all_cids):
            record = {"config_id": cid}
            for metric_name, values in metrics.items():
                record[metric_name] = values.get(cid)
            f.write(json.dumps(record) + "\n")

    return output_path


def main():
    """Compute and write cross-asset rankings from Gen500 data."""
    print("=== Cross-Asset Metrics (Gen500) ===\n")

    asset_data = load_gen500_data()
    if not asset_data:
        print("ERROR: No Gen500 data found in logs/gen500/")
        return 1

    print(f"Loaded {len(asset_data)} assets:")
    for key, records in sorted(asset_data.items()):
        print(f"  {key}: {len(records)} configs")

    metrics = compute_cross_asset_metrics(asset_data)

    # Summary statistics
    n_pos = metrics["xa_n_positive"]
    valid = {k: v for k, v in n_pos.items() if v is not None}
    n_total = len(valid)
    n_all_positive = sum(1 for v in valid.values() if v == len(asset_data))
    n_majority = sum(1 for v in valid.values() if v > len(asset_data) / 2)
    n_any = sum(1 for v in valid.values() if v > 0)

    print(f"\n{n_total} configs tested across {len(asset_data)} assets:")
    print(f"  All {len(asset_data)} positive: {n_all_positive}")
    print(f"  Majority (>{len(asset_data) // 2}) positive: {n_majority}")
    print(f"  Any positive: {n_any}")

    # Top 10 by consistency
    consistency = metrics["xa_consistency"]
    avg_pf = metrics["xa_avg_pf"]
    total_sigs = metrics["xa_total_signals"]
    top10 = sorted(
        ((cid, consistency.get(cid, 0), avg_pf.get(cid, 0), total_sigs.get(cid, 0))
         for cid in valid),
        key=lambda x: (-x[1], -x[2]),
    )[:10]

    print("\nTop 10 by cross-asset consistency:")
    print(f"{'Config':<55} {'Consist':>7} {'AvgPF':>8} {'TotSigs':>8}")
    for cid, cons, apf, tot_s in top10:
        print(f"{cid:<55} {cons:>7.2%} {apf:>8.4f} {tot_s:>8.0f}")

    path = write_cross_asset_rankings(metrics)
    print(f"\nOutput: {path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
