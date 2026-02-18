"""Gen800: Stagnation-first ranking of sweep results.

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

Ranking philosophy: lowest underwater ratio ranks #1.
  Primary sort: underwater_ratio ascending (least total time underwater)
  Secondary sort: max_underwater_bars ascending (shortest longest-stagnation)
  Gates: PF > 1.0, n_trades >= 30, Omega > 1.0

Usage:
    uv run -p 3.13 python scripts/gen800_rank.py
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS_DIR = Path("results/eval/gen800")
SWEEP_FILE = RESULTS_DIR / "gen800_sweep.jsonl"
TOP50_FILE = RESULTS_DIR / "gen800_top50.jsonl"
REPORT_FILE = RESULTS_DIR / "gen800_report.md"

# Gates
MIN_TRADES = 30
MIN_PF = 1.0
MIN_OMEGA = 1.0


def main():
    if not SWEEP_FILE.exists():
        print(f"ERROR: {SWEEP_FILE} not found. Run gen800:sweep first.")
        raise SystemExit(1)

    # Load results
    rows = []
    n_total = 0
    n_ok = 0
    n_skipped = 0
    n_error = 0

    with open(SWEEP_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            row = json.loads(line)
            status = row.get("status", "")
            if status == "ok":
                n_ok += 1
                rows.append(row)
            elif status == "skipped":
                n_skipped += 1
            elif status == "error":
                n_error += 1

    print(f"Loaded {n_total} lines: {n_ok} ok, {n_skipped} skipped, {n_error} errors")

    # Apply gates
    gated = []
    for row in rows:
        n_trades = row.get("n_trades", 0)
        pf = row.get("profit_factor")
        omega = row.get("omega")

        if n_trades < MIN_TRADES:
            continue
        if pf is None or pf <= MIN_PF:
            continue
        if omega is None or omega <= MIN_OMEGA:
            continue

        gated.append(row)

    print(f"After gates (n>={MIN_TRADES}, PF>{MIN_PF}, Omega>{MIN_OMEGA}): {len(gated)} / {n_ok}")

    if not gated:
        print("No configs pass gates. Writing empty report.")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        TOP50_FILE.write_text("")
        REPORT_FILE.write_text("# Gen800 Report\n\nNo configs pass gates.\n")
        return

    # Sort: primary = underwater_ratio ASC, secondary = max_underwater_bars ASC
    gated.sort(key=lambda r: (r.get("underwater_ratio", 1.0), r.get("max_underwater_bars", 999999)))

    # Assign ranks
    for i, row in enumerate(gated):
        row["rank"] = i + 1

    # Top 50
    top50 = gated[:50]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOP50_FILE, "w") as f:
        for row in top50:
            f.write(json.dumps(row, default=str) + "\n")

    print(f"\nTop 50 written to {TOP50_FILE}")

    # Report
    report_lines = [
        "# Gen800 Stagnation-First Ranking Report",
        "",
        f"**Total configs**: {n_ok}",
        f"**After gates** (n>={MIN_TRADES}, PF>{MIN_PF}, Omega>{MIN_OMEGA}): {len(gated)}",
        f"**Skipped**: {n_skipped} | **Errors**: {n_error}",
        "",
        "## Ranking: Lowest Underwater Ratio",
        "",
        "| Rank | Config ID | Max UW Bars | UW Ratio | PF | Omega | N Trades | Win Rate |",
        "|------|-----------|-------------|----------|----|-------|----------|----------|",
    ]

    for row in top50[:20]:
        report_lines.append(
            f"| {row['rank']} "
            f"| `{row['config_id'][:60]}` "
            f"| {row['max_underwater_bars']} "
            f"| {row['underwater_ratio']:.3f} "
            f"| {row.get('profit_factor', 0):.2f} "
            f"| {row.get('omega', 0):.2f} "
            f"| {row['n_trades']} "
            f"| {row.get('win_rate', 0):.1%} |"
        )

    # Pattern distribution
    pattern_counts: dict[str, int] = {}
    gate_counts: dict[str, int] = {}
    for row in gated:
        p = row.get("pattern", "?")
        g = row.get("regime_gate", "?")
        pattern_counts[p] = pattern_counts.get(p, 0) + 1
        gate_counts[g] = gate_counts.get(g, 0) + 1

    report_lines.extend([
        "",
        "## Distribution (Gate-Passing Configs)",
        "",
        "### By Pattern",
        "",
        "| Pattern | Count |",
        "|---------|-------|",
    ])
    for p, c in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {p} | {c} |")

    report_lines.extend([
        "",
        "### By Regime Gate",
        "",
        "| Gate | Count |",
        "|------|-------|",
    ])
    for g, c in sorted(gate_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {g} | {c} |")

    # Stagnation statistics
    uw_bars = [r["max_underwater_bars"] for r in gated]
    uw_ratios = [r["underwater_ratio"] for r in gated]

    report_lines.extend([
        "",
        "## Stagnation Statistics (Gate-Passing Configs)",
        "",
        f"- **max_underwater_bars**: min={min(uw_bars)}, "
        f"median={sorted(uw_bars)[len(uw_bars)//2]}, max={max(uw_bars)}",
        f"- **underwater_ratio**: min={min(uw_ratios):.3f}, "
        f"median={sorted(uw_ratios)[len(uw_ratios)//2]:.3f}, max={max(uw_ratios):.3f}",
    ])

    report_text = "\n".join(report_lines) + "\n"
    REPORT_FILE.write_text(report_text)
    print(f"Report written to {REPORT_FILE}")

    # Print top 5
    print("\n--- Top 5 by Lowest Underwater Ratio ---")
    for row in top50[:5]:
        print(
            f"  #{row['rank']}: max_uw={row['max_underwater_bars']} "
            f"uw_ratio={row['underwater_ratio']:.3f} "
            f"PF={row.get('profit_factor', 0):.2f} "
            f"Omega={row.get('omega', 0):.2f} "
            f"n={row['n_trades']} "
            f"pattern={row['pattern']} gate={row['regime_gate']}"
        )


if __name__ == "__main__":
    main()
