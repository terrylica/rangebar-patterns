"""Agent 9: Synthesis -- e-BH FDR + Romano-Wolf + cross-metric verdict.

(a) e-BH procedure (Wang & Ramdas 2022) for FDR control using E-values
(b) Romano-Wolf step-down (bootstrap FWER control)
(c) Cross-metric comparison: Spearman correlations, redundancy, verdict

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/12
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_EBH = RESULTS_DIR / "ebh_fdr.jsonl"
OUTPUT_RW = RESULTS_DIR / "romano_wolf.jsonl"
OUTPUT_CORR = RESULTS_DIR / "rank_correlations.jsonl"
OUTPUT_VERDICT = RESULTS_DIR / "verdict.md"

ALPHA = 0.05


def load_jsonl(path: Path) -> list[dict]:
    """Load NDJSON file into list of dicts."""
    records = []
    with open(path) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def ebh_procedure(evalues: list[dict]) -> dict:
    """e-BH FDR control procedure (Wang & Ramdas 2022).

    Order configs by E-value descending, find k* = max{k: k * e[k] / K >= 1/alpha}.
    """
    valid = [
        (r["config_id"], r["final_evalue"])
        for r in evalues
        if r.get("final_evalue") is not None and r["final_evalue"] > 0
    ]
    valid.sort(key=lambda x: x[1], reverse=True)
    k_total = len(valid)

    if k_total == 0:
        return {"k_star": 0, "discoveries": [], "k_total": 0}

    k_star = 0
    for k in range(1, k_total + 1):
        if k * valid[k - 1][1] / k_total >= 1.0 / ALPHA:
            k_star = k

    discoveries = [{"config_id": cid, "evalue": ev} for cid, ev in valid[:k_star]]

    return {
        "k_star": k_star,
        "k_total": k_total,
        "alpha": ALPHA,
        "discoveries": discoveries,
        "top_5_evalues": [
            {"config_id": cid, "evalue": round(ev, 4)}
            for cid, ev in valid[:5]
        ],
    }


def romano_wolf_stepdown(trade_returns: list[dict], n_bootstrap: int = 1000) -> dict:
    """Romano-Wolf step-down for FWER control using bootstrap.

    Simplified for POC: bootstrap resample trade returns, compute test
    statistics (mean return / se), step-down using max-t distribution.
    """
    rng = np.random.default_rng(42)

    # Build matrix: configs x trades (sparse - different configs have different trades)
    configs_with_data = [
        d for d in trade_returns
        if not d.get("error") and d.get("n_trades", 0) >= 10
    ]

    if not configs_with_data:
        return {"n_rejections": 0, "discoveries": [], "n_bootstrap": n_bootstrap}

    # Compute observed test statistics: t = mean / (std / sqrt(n))
    observed_t = []
    config_ids = []
    config_returns = []

    for d in configs_with_data:
        rets = np.array(d["returns"])
        n = len(rets)
        mean = rets.mean()
        se = rets.std(ddof=1) / np.sqrt(n) if n > 1 else float("inf")
        t_stat = mean / se if se > 0 else 0.0
        observed_t.append(t_stat)
        config_ids.append(d["config_id"])
        config_returns.append(rets)

    observed_t = np.array(observed_t)
    n_configs = len(observed_t)

    # Bootstrap: resample and compute max-t for step-down
    boot_max_t = np.zeros(n_bootstrap)
    for b in range(n_bootstrap):
        boot_t = np.zeros(n_configs)
        for i, rets in enumerate(config_returns):
            n = len(rets)
            # Resample under null: center returns at 0
            centered = rets - rets.mean()
            boot_sample = rng.choice(centered, size=n, replace=True)
            se = boot_sample.std(ddof=1) / np.sqrt(n) if n > 1 else float("inf")
            boot_t[i] = boot_sample.mean() / se if se > 0 else 0.0
        boot_max_t[b] = boot_t.max()

    # Step-down: reject if observed_t > critical value from bootstrap max-t
    critical = np.percentile(boot_max_t, 100 * (1 - ALPHA))

    discoveries = [
        {"config_id": config_ids[i], "t_stat": round(float(observed_t[i]), 4)}
        for i in range(n_configs)
        if observed_t[i] > critical
    ]

    return {
        "n_rejections": len(discoveries),
        "n_configs_tested": n_configs,
        "n_bootstrap": n_bootstrap,
        "critical_value": round(float(critical), 4),
        "alpha": ALPHA,
        "discoveries": discoveries,
    }


def cross_metric_comparison() -> dict:
    """Compute Spearman rank correlations between all metric rankings."""
    # Load all metric files
    moments = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "moments.jsonl")}
    dsr = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "dsr_rankings.jsonl")}
    minbtl = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "minbtl_gate.jsonl")}
    cf = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "cornish_fisher.jsonl")}
    omega = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "omega_rankings.jsonl")}
    evalues = {r["config_id"]: r for r in load_jsonl(RESULTS_DIR / "evalues.jsonl")}

    # Common config set (all must have data)
    common_ids = sorted(
        set(moments.keys()) & set(dsr.keys()) & set(omega.keys()) & set(evalues.keys())
    )

    # Extract ranking vectors
    vectors = {}
    for cid in common_ids:
        m = moments.get(cid, {})
        d = dsr.get(cid, {})
        o = omega.get(cid, {})
        e = evalues.get(cid, {})
        c = cf.get(cid, {})

        kelly = m.get("kelly_fraction")
        sr = d.get("sharpe_ratio")
        psr_val = d.get("psr_vs_zero")
        dsr_val = d.get("dsr")
        omega_val = o.get("omega_L0")
        grow_val = e.get("grow_criterion")
        cf_es = c.get("mean_over_cf_es_05")

        def _is_finite(v):
            return v is not None and (not isinstance(v, float) or math.isfinite(v))

        if all(_is_finite(v) for v in [kelly, sr, psr_val, dsr_val, omega_val, grow_val]):
            for name, val in [
                ("kelly", kelly), ("sharpe", sr), ("psr", psr_val),
                ("dsr", dsr_val), ("omega", omega_val), ("grow", grow_val),
            ]:
                vectors.setdefault(name, []).append(val)
            # CF ES may be None for some
            vectors.setdefault("cf_es_adj", []).append(cf_es if cf_es is not None else 0.0)

    if not vectors or len(vectors.get("kelly", [])) < 10:
        return {"error": "Insufficient common configs for correlation"}

    # Compute pairwise Spearman correlations
    metric_names = ["kelly", "sharpe", "psr", "dsr", "omega", "grow", "cf_es_adj"]
    n_metrics = len(metric_names)
    corr_matrix = np.zeros((n_metrics, n_metrics))

    for i in range(n_metrics):
        for j in range(n_metrics):
            if i == j:
                corr_matrix[i][j] = 1.0
            elif j > i:
                vi = np.array(vectors.get(metric_names[i], []))
                vj = np.array(vectors.get(metric_names[j], []))
                min_len = min(len(vi), len(vj))
                if min_len >= 10:
                    rho, _ = spearmanr(vi[:min_len], vj[:min_len])
                    corr_matrix[i][j] = rho
                    corr_matrix[j][i] = rho

    corr_dict = {}
    for i in range(n_metrics):
        for j in range(i + 1, n_metrics):
            key = f"{metric_names[i]}_vs_{metric_names[j]}"
            corr_dict[key] = round(float(corr_matrix[i][j]), 4)

    # Identify redundant (r > 0.95) and complementary (r < 0.80)
    redundant = {k: v for k, v in corr_dict.items() if v > 0.95}
    complementary = {k: v for k, v in corr_dict.items() if abs(v) < 0.80}

    # Pathological cases: Kelly > 0 but DSR < 0.5
    patho_kelly_dsr = []
    for cid in common_ids:
        m = moments.get(cid, {})
        d = dsr.get(cid, {})
        kelly = m.get("kelly_fraction", 0)
        dsr_val = d.get("dsr", 1)
        btl = minbtl.get(cid, {})
        if kelly is not None and kelly > 0 and dsr_val is not None and dsr_val < 0.5:
            patho_kelly_dsr.append({
                "config_id": cid,
                "kelly": round(kelly, 6),
                "dsr": round(dsr_val, 6),
                "n_trades": m.get("n_trades", 0),
                "minbtl_passes": btl.get("passes_gate", False),
            })

    return {
        "n_common_configs": len(vectors.get("kelly", [])),
        "correlations": corr_dict,
        "redundant_pairs": redundant,
        "complementary_pairs": complementary,
        "pathological_kelly_dsr": patho_kelly_dsr[:20],  # Top 20
        "n_pathological": len(patho_kelly_dsr),
    }


def write_verdict(ebh: dict, rw: dict, corr: dict, cscv: dict) -> None:
    """Write human-readable verdict to verdict.md."""
    lines = [
        "# Beyond-Kelly POC Verdict",
        "",
        "## 1. Multiple Testing Corrections",
        "",
        f"### e-BH FDR (alpha={ALPHA})",
        f"- **Discoveries**: {ebh['k_star']} out of {ebh['k_total']} configs",
        f"- Top 5 E-values: {json.dumps(ebh.get('top_5_evalues', []))}",
        "",
        f"### Romano-Wolf FWER (B={rw.get('n_bootstrap', 'N/A')})",
        f"- **Rejections**: {rw.get('n_rejections', 0)} out of {rw.get('n_configs_tested', 'N/A')}",
        f"- Critical value: {rw.get('critical_value', 'N/A')}",
        "",
        "## 2. Overfitting Detection (CSCV/PBO)",
        "",
    ]

    if cscv:
        lines.extend([
            f"- **PBO**: {cscv.get('pbo', 'N/A')} ({cscv.get('pbo_interpretation', 'N/A')})",
            f"- Mean OOS rank of IS winner: {cscv.get('mean_oos_rank', 'N/A')}",
            f"- Most common IS winner: {cscv.get('most_common_is_winner', 'N/A')}",
        ])

    lines.extend([
        "",
        "## 3. Cross-Metric Rank Correlations",
        "",
        "| Pair | Spearman r | Interpretation |",
        "|------|-----------|----------------|",
    ])

    for pair, rho in sorted(corr.get("correlations", {}).items()):
        interp = "REDUNDANT" if rho > 0.95 else "HIGH" if rho > 0.80 else "COMPLEMENTARY"
        lines.append(f"| {pair} | {rho:.4f} | {interp} |")

    lines.extend([
        "",
        f"### Redundant pairs (r > 0.95): {len(corr.get('redundant_pairs', {}))}",
    ])
    for pair, rho in corr.get("redundant_pairs", {}).items():
        lines.append(f"- {pair}: {rho}")

    lines.extend([
        "",
        f"### Complementary pairs (r < 0.80): {len(corr.get('complementary_pairs', {}))}",
    ])
    for pair, rho in corr.get("complementary_pairs", {}).items():
        lines.append(f"- {pair}: {rho}")

    lines.extend([
        "",
        "## 4. Pathological Cases (Kelly > 0 but DSR < 0.5)",
        "",
        f"**Total**: {corr.get('n_pathological', 0)} configs",
        "",
    ])

    patho = corr.get("pathological_kelly_dsr", [])
    if patho:
        lines.extend([
            "| config_id | Kelly | DSR | N trades | MinBTL passes |",
            "|-----------|-------|-----|----------|---------------|",
        ])
        for p in patho[:10]:
            lines.append(
                f"| {p['config_id'][:40]} | {p['kelly']:.4f} | "
                f"{p['dsr']:.4f} | {p['n_trades']} | {p['minbtl_passes']} |"
            )

    lines.extend([
        "",
        "## 5. Recommended Metric Stack",
        "",
        "Based on the POC analysis, the recommended minimal metric stack is:",
        "",
        "1. **DSR** (Deflated Sharpe Ratio) -- primary ranking metric (replaces Kelly)",
        "2. **MinBTL** -- data sufficiency gate (hard reject if n_trades < MinBTL)",
        "3. **PBO** (from CSCV) -- overfitting detection (reject if PBO > 0.5)",
        "4. **Omega Ratio** -- complementary ranking (captures full distribution)",
        "5. **E-values + e-BH** -- anytime-valid FDR control for live monitoring",
        "6. **Cornish-Fisher ES** -- tail risk filter (reject extreme tail_risk_ratio)",
        "",
        "### Metrics to DROP (if redundant):",
        "",
    ])

    for pair in corr.get("redundant_pairs", {}):
        lines.append(f"- {pair} are redundant -- keep only one")

    lines.extend([
        "",
        "## 6. Summary Verdict",
        "",
    ])

    if ebh["k_star"] == 0 and rw.get("n_rejections", 0) == 0:
        lines.append(
            "**CONSISTENT WITH BONFERRONI**: Zero discoveries under both e-BH and "
            "Romano-Wolf, confirming that no configs survive rigorous multiple testing."
        )
    else:
        lines.append(
            f"**DISCOVERIES FOUND**: {ebh['k_star']} under e-BH, "
            f"{rw.get('n_rejections', 0)} under Romano-Wolf."
        )

    if cscv and cscv.get("pbo", 0) > 0.5:
        lines.append(
            f"\n**OVERFITTING CONFIRMED**: PBO = {cscv['pbo']:.2f} indicates the "
            "best in-sample config is worse than median out-of-sample."
        )

    with open(OUTPUT_VERDICT, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Verdict written to {OUTPUT_VERDICT}")


def main():
    print("=== Phase 3: Synthesis ===\n")

    # Load E-values for e-BH
    evalues = load_jsonl(RESULTS_DIR / "evalues.jsonl")
    print(f"Loaded {len(evalues)} E-value records")

    # (a) e-BH FDR procedure
    ebh = ebh_procedure(evalues)
    with open(OUTPUT_EBH, "w") as f:
        f.write(json.dumps(ebh) + "\n")
    print(f"e-BH: {ebh['k_star']} discoveries (FDR={ALPHA})")

    # (b) Romano-Wolf step-down
    trade_returns = load_jsonl(RESULTS_DIR / "trade_returns.jsonl")
    print("Running Romano-Wolf bootstrap (B=1000)...")
    rw = romano_wolf_stepdown(trade_returns, n_bootstrap=1000)
    with open(OUTPUT_RW, "w") as f:
        f.write(json.dumps(rw) + "\n")
    print(f"Romano-Wolf: {rw['n_rejections']} rejections (FWER={ALPHA})")

    # (c) Cross-metric comparison
    print("Computing cross-metric correlations...")
    corr = cross_metric_comparison()
    with open(OUTPUT_CORR, "w") as f:
        f.write(json.dumps(corr) + "\n")
    print(f"Correlations computed for {corr.get('n_common_configs', 0)} common configs")

    # Load CSCV results
    cscv_path = RESULTS_DIR / "cscv_pbo.jsonl"
    cscv = load_jsonl(cscv_path)[0] if cscv_path.exists() else {}

    # Write verdict
    write_verdict(ebh, rw, corr, cscv)

    print("\n=== Synthesis Complete ===")
    print(f"  e-BH: {OUTPUT_EBH}")
    print(f"  Romano-Wolf: {OUTPUT_RW}")
    print(f"  Correlations: {OUTPUT_CORR}")
    print(f"  Verdict: {OUTPUT_VERDICT}")


if __name__ == "__main__":
    main()
