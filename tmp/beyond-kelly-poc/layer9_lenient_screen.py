"""Layer 9: Lenient 5-Metric Screening — Forensic Re-Evaluation.

Re-evaluates all 1,008 configs with graduated lenient thresholds (3 tiers)
to identify candidates for further investigation. The strict thresholds from
the original POC (DSR > 0.95, MinBTL pass) yielded 0 survivors. This layer
relaxes thresholds to surface the strongest candidates within the noise.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_SCREEN = RESULTS_DIR / "lenient_screen.jsonl"
OUTPUT_VERDICT = RESULTS_DIR / "lenient_verdict.md"

# --- Tier Thresholds ---
# DSR reality: 958/961 configs have DSR=0.000 exactly (SR too weak for N=1008).
# DSR > 0 is effectively a 3-config filter — useless for screening.
# Strategy: Tier 1 drops DSR gate entirely (set to -1 = always pass).
# Tier 2-3 use DSR as soft gate (>= 0 = non-NaN).
TIERS = {
    "tier1_exploratory": {
        "kelly_min": 0.0,
        "omega_min": 1.0,
        "dsr_min": -1.0,       # disabled: DSR is binary 0/non-0, useless as gate
        "headroom_min": 0.01,
        "n_trades_min": 30,
    },
    "tier2_balanced": {
        "kelly_min": 0.01,
        "omega_min": 1.02,
        "dsr_min": -1.0,       # disabled: same reason
        "headroom_min": 0.05,
        "n_trades_min": 50,
    },
    "tier3_strict": {
        "kelly_min": 0.05,
        "omega_min": 1.05,
        "dsr_min": -1.0,       # disabled: same reason
        "headroom_min": 0.10,
        "n_trades_min": 100,
    },
}


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def load_all_metrics() -> dict[str, dict]:
    """Load and join all metric result files by config_id."""
    moments = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "moments.jsonl")}
    dsr = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "dsr_rankings.jsonl")}
    minbtl = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "minbtl_gate.jsonl")}
    omega = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "omega_rankings.jsonl")}
    evalues = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "evalues.jsonl")}

    cf_path = RESULTS_DIR / "cornish_fisher.jsonl"
    cf = {r["config_id"]: r for r in load_jsonl(cf_path)} if cf_path.exists() else {}

    all_ids = sorted(set(moments.keys()) | set(dsr.keys()) | set(omega.keys()))

    configs = {}
    for cid in all_ids:
        m = moments.get(cid, {})
        d = dsr.get(cid, {})
        b = minbtl.get(cid, {})
        o = omega.get(cid, {})
        e = evalues.get(cid, {})
        c = cf.get(cid, {})

        kelly = m.get("kelly_fraction")
        omega_val = o.get("omega_L0")
        dsr_val = d.get("dsr")
        headroom = b.get("headroom_ratio", 0.0)
        n_trades = m.get("n_trades", 0)
        sr = d.get("sharpe_ratio")
        evalue = e.get("final_evalue")
        cf_es = c.get("mean_over_cf_es_05")
        min_btl_req = b.get("min_btl_required")

        configs[cid] = {
            "config_id": cid,
            "kelly": kelly,
            "omega": omega_val,
            "dsr": dsr_val,
            "headroom": headroom,
            "n_trades": n_trades,
            "sharpe": sr,
            "evalue": evalue,
            "cf_es": cf_es,
            "min_btl_required": min_btl_req,
        }

    return configs


def _safe_float(v, default=0.0) -> float:
    if v is None:
        return default
    if isinstance(v, float) and not math.isfinite(v):
        return default
    return float(v)


def passes_tier(cfg: dict, thresholds: dict) -> bool:
    kelly = _safe_float(cfg["kelly"], -999)
    omega = _safe_float(cfg["omega"], 0)
    dsr = _safe_float(cfg["dsr"], -1)
    headroom = _safe_float(cfg["headroom"], 0)
    n_trades = cfg.get("n_trades", 0) or 0

    return (
        kelly > thresholds["kelly_min"]
        and omega > thresholds["omega_min"]
        and dsr > thresholds["dsr_min"]
        and headroom > thresholds["headroom_min"]
        and n_trades >= thresholds["n_trades_min"]
    )


def individual_gate_pass(cfg: dict, thresholds: dict) -> dict[str, bool]:
    kelly = _safe_float(cfg["kelly"], -999)
    omega = _safe_float(cfg["omega"], 0)
    dsr = _safe_float(cfg["dsr"], -1)
    headroom = _safe_float(cfg["headroom"], 0)
    n_trades = cfg.get("n_trades", 0) or 0

    return {
        "kelly": kelly > thresholds["kelly_min"],
        "omega": omega > thresholds["omega_min"],
        "dsr": dsr > thresholds["dsr_min"],
        "headroom": headroom > thresholds["headroom_min"],
        "n_trades": n_trades >= thresholds["n_trades_min"],
    }


def normalize_array(arr: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1]. Returns zeros if constant."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-12:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def compute_composite_scores(passing: list[dict]) -> list[dict]:
    """Weighted composite: 0.4*kelly + 0.3*omega + 0.2*dsr + 0.1*headroom."""
    if not passing:
        return []

    kellys = np.array([_safe_float(c["kelly"]) for c in passing])
    omegas = np.array([_safe_float(c["omega"]) for c in passing])
    dsrs = np.array([_safe_float(c["dsr"]) for c in passing])
    headrooms = np.array([_safe_float(c["headroom"]) for c in passing])

    scores = (
        0.4 * normalize_array(kellys)
        + 0.3 * normalize_array(omegas)
        + 0.2 * normalize_array(dsrs)
        + 0.1 * normalize_array(headrooms)
    )

    for i, cfg in enumerate(passing):
        cfg["composite_score"] = round(float(scores[i]), 6)

    return sorted(passing, key=lambda x: x["composite_score"], reverse=True)


def distribution_stats(values: list[float], label: str) -> dict:
    arr = np.array([v for v in values if math.isfinite(v)])
    if len(arr) == 0:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": len(arr),
        "min": round(float(arr.min()), 6),
        "p10": round(float(np.percentile(arr, 10)), 6),
        "p25": round(float(np.percentile(arr, 25)), 6),
        "p50": round(float(np.percentile(arr, 50)), 6),
        "p75": round(float(np.percentile(arr, 75)), 6),
        "p90": round(float(np.percentile(arr, 90)), 6),
        "max": round(float(arr.max()), 6),
        "mean": round(float(arr.mean()), 6),
    }


def write_forensic_report(
    all_configs: dict[str, dict],
    tier_results: dict[str, list[dict]],
    dist_stats: dict[str, dict],
    funnel_data: dict[str, dict],
) -> None:
    lines = [
        "# Lenient 5-Metric Screening — Forensic Report",
        "",
        "## 1. Metric Distribution Summary (All 1,008 Configs)",
        "",
        "| Metric | Min | P10 | P25 | P50 | P75 | P90 | Max |",
        "|--------|-----|-----|-----|-----|-----|-----|-----|",
    ]
    for key in ["kelly", "omega", "dsr", "headroom", "n_trades"]:
        s = dist_stats.get(key, {})
        if s.get("n", 0) > 0:
            lines.append(
                f"| {s['label']} | {s['min']} | {s['p10']} | {s['p25']} "
                f"| {s['p50']} | {s['p75']} | {s['p90']} | {s['max']} |"
            )

    # Funnel analysis per tier
    for tier_name, thresholds in TIERS.items():
        tier_label = tier_name.replace("_", " ").title()
        passing = tier_results[tier_name]

        lines.extend([
            "",
            f"## 2. {tier_label}",
            "",
            f"**Thresholds**: Kelly > {thresholds['kelly_min']}, "
            f"Omega > {thresholds['omega_min']}, "
            f"DSR > {thresholds['dsr_min']}, "
            f"MinBTL headroom > {thresholds['headroom_min']}, "
            f"n_trades >= {thresholds['n_trades_min']}",
            "",
        ])

        # Funnel
        funnel = funnel_data[tier_name]
        lines.extend([
            "### Funnel (individual gate pass rates)",
            "",
            "| Gate | Pass | Fail | % Pass |",
            "|------|------|------|--------|",
        ])
        total = funnel["total"]
        for gate_name in ["kelly", "omega", "dsr", "headroom", "n_trades"]:
            p = funnel["gates"].get(gate_name, 0)
            f_count = total - p
            pct = round(100 * p / total, 1) if total > 0 else 0
            lines.append(f"| {gate_name} | {p} | {f_count} | {pct}% |")

        lines.extend([
            f"| **ALL gates** | **{len(passing)}** | "
            f"**{total - len(passing)}** | "
            f"**{round(100 * len(passing) / total, 1) if total > 0 else 0}%** |",
        ])

        # Binding constraint
        lines.extend([
            "",
            f"### Binding Constraint: **{funnel['binding_constraint']}** "
            f"(kills {funnel['binding_kills']} configs that pass other 4 gates)",
            "",
        ])

        if not passing:
            lines.append("**No configs pass all gates at this tier.**")
            continue

        # Top configs
        lines.extend([
            f"### Top {min(20, len(passing))} Configs (by composite score)",
            "",
            "| Rank | Config ID | Kelly | Omega | DSR | Headroom | N Trades | Score |",
            "|------|-----------|-------|-------|-----|----------|----------|-------|",
        ])
        for rank, cfg in enumerate(passing[:20], 1):
            lines.append(
                f"| {rank} | {cfg['config_id'][:50]} "
                f"| {_safe_float(cfg['kelly']):.4f} "
                f"| {_safe_float(cfg['omega']):.4f} "
                f"| {_safe_float(cfg['dsr']):.6f} "
                f"| {_safe_float(cfg['headroom']):.4f} "
                f"| {cfg.get('n_trades', 0)} "
                f"| {cfg.get('composite_score', 0):.4f} |"
            )

    # Near-miss analysis (fail exactly 1 gate at Tier 2)
    lines.extend([
        "",
        "## 3. Near-Miss Analysis (Tier 2 — fail exactly 1 gate)",
        "",
    ])
    near_miss = []
    tier2_thresholds = TIERS["tier2_balanced"]
    for cfg in all_configs.values():
        gates = individual_gate_pass(cfg, tier2_thresholds)
        fail_count = sum(1 for v in gates.values() if not v)
        if fail_count == 1:
            failed_gate = next(k for k, v in gates.items() if not v)
            near_miss.append((cfg, failed_gate))

    if near_miss:
        # Group by failed gate
        by_gate: dict[str, int] = {}
        for _, gate in near_miss:
            by_gate[gate] = by_gate.get(gate, 0) + 1

        lines.extend([
            f"**{len(near_miss)} configs** fail exactly 1 gate at Tier 2:",
            "",
            "| Failed Gate | Count |",
            "|-------------|-------|",
        ])
        for gate, count in sorted(by_gate.items(), key=lambda x: -x[1]):
            lines.append(f"| {gate} | {count} |")

        # Show top near-misses by Kelly
        near_miss.sort(key=lambda x: _safe_float(x[0]["kelly"]), reverse=True)
        lines.extend([
            "",
            "### Top 10 Near-Misses (by Kelly)",
            "",
            "| Config ID | Kelly | Omega | DSR | Headroom | N | Failed Gate |",
            "|-----------|-------|-------|-----|----------|---|-------------|",
        ])
        for cfg, gate in near_miss[:10]:
            lines.append(
                f"| {cfg['config_id'][:45]} "
                f"| {_safe_float(cfg['kelly']):.4f} "
                f"| {_safe_float(cfg['omega']):.4f} "
                f"| {_safe_float(cfg['dsr']):.6f} "
                f"| {_safe_float(cfg['headroom']):.4f} "
                f"| {cfg.get('n_trades', 0)} "
                f"| {gate} |"
            )
    else:
        lines.append("No near-misses found.")

    # Summary
    lines.extend([
        "",
        "## 4. Summary",
        "",
        "| Tier | Pass | % of 1,008 | Binding Constraint |",
        "|------|------|------------|-------------------|",
    ])
    for tier_name in TIERS:
        tier_label = tier_name.replace("_", " ").title()
        n_pass = len(tier_results[tier_name])
        pct = round(100 * n_pass / len(all_configs), 1)
        binding = funnel_data[tier_name]["binding_constraint"]
        lines.append(f"| {tier_label} | {n_pass} | {pct}% | {binding} |")

    lines.extend([
        "",
        "## 5. Actionable Recommendations",
        "",
        "Configs passing Tier 1 (exploratory) are candidates for:",
        "- **Live paper trading** to accumulate more trades (address MinBTL shortfall)",
        "- **Cross-asset validation** via Gen500 data (check if signal generalizes)",
        "- **Barrier optimization** via Gen510 grid (tight TP + wide SL)",
        "",
        "PBO = 0.3286 (marginal) applies globally — there IS some overfitting risk.",
        "",
    ])

    with open(OUTPUT_VERDICT, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    print("=== Layer 9: Lenient 5-Metric Screening ===\n")

    # Load all metrics
    all_configs = load_all_metrics()
    print(f"Loaded {len(all_configs)} configs with joined metrics")

    # Distribution stats
    dist_stats = {}
    for key, getter in [
        ("kelly", lambda c: _safe_float(c["kelly"], float("nan"))),
        ("omega", lambda c: _safe_float(c["omega"], float("nan"))),
        ("dsr", lambda c: _safe_float(c["dsr"], float("nan"))),
        ("headroom", lambda c: _safe_float(c["headroom"], float("nan"))),
        ("n_trades", lambda c: float(c.get("n_trades", 0) or 0)),
    ]:
        values = [getter(c) for c in all_configs.values()]
        finite_values = [v for v in values if math.isfinite(v)]
        label_map = {
            "kelly": "Kelly",
            "omega": "Omega",
            "dsr": "DSR",
            "headroom": "MinBTL Headroom",
            "n_trades": "N Trades",
        }
        dist_stats[key] = distribution_stats(finite_values, label_map[key])

    print("\nDistribution summary:")
    for _key, s in dist_stats.items():
        if s.get("n", 0) > 0:
            print(
                f"  {s['label']:18s}: p50={s['p50']}, p90={s['p90']}, "
                f"max={s['max']}, n={s['n']}"
            )

    # Apply tiers
    tier_results = {}
    funnel_data = {}

    for tier_name, thresholds in TIERS.items():
        passing = []
        gate_counts: dict[str, int] = {
            "kelly": 0, "omega": 0, "dsr": 0, "headroom": 0, "n_trades": 0,
        }

        for cfg in all_configs.values():
            gates = individual_gate_pass(cfg, thresholds)
            for g, v in gates.items():
                if v:
                    gate_counts[g] += 1
            if all(gates.values()):
                passing.append(dict(cfg))

        # Compute composite scores
        passing = compute_composite_scores(passing)
        tier_results[tier_name] = passing

        # Binding constraint: which gate kills most configs that pass other 4?
        binding = "n/a"
        max_kills = -1
        total = len(all_configs)
        for gate_name in gate_counts:
            # Configs that pass all OTHER gates but fail THIS one
            kills = 0
            for cfg in all_configs.values():
                gates = individual_gate_pass(cfg, thresholds)
                other_pass = all(v for k, v in gates.items() if k != gate_name)
                if other_pass and not gates[gate_name]:
                    kills += 1
            if kills > max_kills:
                max_kills = kills
                binding = gate_name

        funnel_data[tier_name] = {
            "total": total,
            "gates": gate_counts,
            "binding_constraint": binding,
            "binding_kills": max_kills,
        }

        tier_label = tier_name.replace("_", " ").title()
        print(f"\n{tier_label}: {len(passing)}/{total} pass "
              f"(binding: {binding}, kills {max_kills})")
        if passing:
            top = passing[0]
            print(f"  Top: {top['config_id']} "
                  f"(Kelly={_safe_float(top['kelly']):.4f}, "
                  f"Omega={_safe_float(top['omega']):.4f}, "
                  f"score={top.get('composite_score', 0):.4f})")

    # Write JSONL output (all configs with tier flags)
    with open(OUTPUT_SCREEN, "w") as f:
        for cid, cfg in sorted(all_configs.items()):
            out = dict(cfg)
            for tier_name in TIERS:
                passing_ids = {c["config_id"] for c in tier_results[tier_name]}
                out[f"passes_{tier_name}"] = cid in passing_ids
            # Find composite score if in any tier
            for tier_name in TIERS:
                for c in tier_results[tier_name]:
                    if c["config_id"] == cid:
                        out[f"score_{tier_name}"] = c.get("composite_score")
                        break
            f.write(json.dumps(out) + "\n")

    # Write forensic report
    write_forensic_report(all_configs, tier_results, dist_stats, funnel_data)

    print("\n=== Screening Complete ===")
    print(f"  Screen: {OUTPUT_SCREEN}")
    print(f"  Report: {OUTPUT_VERDICT}")


if __name__ == "__main__":
    main()
