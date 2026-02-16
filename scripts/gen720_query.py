"""Ad-hoc DuckDB queries on Gen720 Parquet telemetry.

Thin CLI wrapper for post-hoc analysis of Tier 1 Parquet fold results.

Usage:
    python scripts/gen720_query.py top-barriers
    python scripts/gen720_query.py cross-asset --barrier-id p5_slt010_mb100
    python scripts/gen720_query.py strategy-comparison
    python scripts/gen720_query.py custom --sql "SELECT ..."

GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "eval" / "gen720"
LONG_PARQUET = RESULTS_DIR / "folds" / "long_folds.parquet"
SHORT_PARQUET = RESULTS_DIR / "folds" / "short_folds.parquet"


def _resolve_parquet(direction: str) -> Path:
    """Resolve Parquet path, checking existence."""
    p = LONG_PARQUET if direction == "long" else SHORT_PARQUET
    if not p.exists():
        print(f"ERROR: {p} not found. Run walk-forward pipeline first.")
        sys.exit(1)
    return p


CANNED_QUERIES: dict[str, str] = {
    "top-barriers": """
        SELECT barrier_id,
               COUNT(*) AS n_folds,
               AVG(omega) AS avg_omega,
               STDDEV(omega) / NULLIF(AVG(omega), 0) AS omega_cv,
               AVG(rachev) AS avg_rachev,
               AVG(profit_factor) AS avg_pf,
               SUM(CASE WHEN omega > 1.0 AND rachev > 0.30 THEN 1 ELSE 0 END)::FLOAT
                   / COUNT(*) AS tamrs_viable_pct
        FROM read_parquet('{parquet}')
        GROUP BY barrier_id
        HAVING n_folds >= 50
        ORDER BY tamrs_viable_pct DESC, omega_cv ASC
        LIMIT 20
    """,
    "cross-asset": """
        SELECT symbol, threshold, formation,
               AVG(omega) AS avg_omega,
               AVG(rachev) AS avg_rachev,
               AVG(profit_factor) AS avg_pf,
               COUNT(*) AS n_folds
        FROM read_parquet('{parquet}')
        WHERE barrier_id = '{barrier_id}'
        GROUP BY symbol, threshold, formation
        ORDER BY avg_omega DESC
    """,
    "strategy-comparison": """
        SELECT formation, barrier_id,
               AVG(CASE WHEN strategy = 'B_reverse' THEN omega END) AS b_omega,
               AVG(CASE WHEN strategy = 'A_mirrored' THEN omega END) AS a_omega,
               AVG(CASE WHEN strategy = 'B_reverse' THEN omega END)
                   - AVG(CASE WHEN strategy = 'A_mirrored' THEN omega END) AS b_minus_a,
               AVG(CASE WHEN strategy = 'B_reverse' THEN rachev END) AS b_rachev,
               AVG(CASE WHEN strategy = 'A_mirrored' THEN rachev END) AS a_rachev
        FROM read_parquet('{parquet}')
        GROUP BY formation, barrier_id
        HAVING a_omega IS NOT NULL AND b_omega IS NOT NULL
        ORDER BY b_minus_a DESC
        LIMIT 20
    """,
    "formation-summary": """
        SELECT formation,
               COUNT(DISTINCT barrier_id) AS n_barriers,
               COUNT(DISTINCT symbol || '_' || CAST(threshold AS VARCHAR)) AS n_combos,
               COUNT(*) AS n_folds,
               AVG(omega) AS avg_omega,
               AVG(rachev) AS avg_rachev,
               AVG(win_rate) AS avg_wr,
               AVG(total_return) AS avg_return
        FROM read_parquet('{parquet}')
        GROUP BY formation
        ORDER BY avg_omega DESC
    """,
    "fold-stability": """
        SELECT barrier_id, fold_id,
               AVG(omega) AS avg_omega,
               AVG(rachev) AS avg_rachev,
               COUNT(*) AS n_combos
        FROM read_parquet('{parquet}')
        WHERE barrier_id = '{barrier_id}'
        GROUP BY barrier_id, fold_id
        ORDER BY fold_id
    """,
}


def run_query(query_name: str, args: argparse.Namespace) -> None:
    """Execute a canned or custom DuckDB query on Gen720 Parquet."""
    if query_name == "custom":
        if not args.sql:
            print("ERROR: --sql required for custom queries")
            sys.exit(1)
        sql = args.sql
    else:
        if query_name not in CANNED_QUERIES:
            print(f"ERROR: Unknown query '{query_name}'")
            print(f"Available: {', '.join(CANNED_QUERIES)}, custom")
            sys.exit(1)
        sql = CANNED_QUERIES[query_name]

    # Determine direction and resolve parquet
    direction = args.direction
    if query_name == "strategy-comparison" and direction == "long":
        direction = "short"
        print("NOTE: strategy-comparison uses SHORT parquet (overriding --direction)")

    parquet = _resolve_parquet(direction)

    # Substitute placeholders
    sql = sql.replace("{parquet}", str(parquet))
    if args.barrier_id:
        sql = sql.replace("{barrier_id}", args.barrier_id)
    elif "{barrier_id}" in sql:
        print("ERROR: This query requires --barrier-id")
        sys.exit(1)

    # Execute
    con = duckdb.connect(":memory:")
    try:
        result = con.execute(sql)
        columns = [desc[0] for desc in result.description]

        # Print header
        header = " | ".join(f"{c:>18}" for c in columns)
        print(header)
        print("-" * len(header))

        # Print rows
        n = 0
        for row in result.fetchall():
            formatted = []
            for val in row:
                if val is None:
                    formatted.append(f"{'NULL':>18}")
                elif isinstance(val, float):
                    formatted.append(f"{val:>18.4f}")
                elif isinstance(val, int):
                    formatted.append(f"{val:>18d}")
                else:
                    formatted.append(f"{str(val):>18}")
            print(" | ".join(formatted))
            n += 1

        print(f"\n({n} rows)")
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DuckDB queries on Gen720 Tier 1 Parquet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Canned queries:\n"
            "  top-barriers         Top 20 barriers by TAMRS-viable %% across folds\n"
            "  cross-asset          Per-symbol/threshold breakdown for a barrier\n"
            "  strategy-comparison  SHORT Strategy B vs A by barrier\n"
            "  formation-summary    Per-formation aggregate stats\n"
            "  fold-stability       Per-fold metrics for a specific barrier\n"
            "  custom               Run arbitrary SQL (use --sql)\n"
        ),
    )
    parser.add_argument("query", help="Query name or 'custom'")
    parser.add_argument(
        "--direction",
        choices=["long", "short"],
        default="long",
        help="Which Parquet to query (default: long)",
    )
    parser.add_argument("--barrier-id", help="Barrier ID for filtering (e.g. p5_slt010_mb100)")
    parser.add_argument("--sql", help="Custom SQL for 'custom' query type")
    args = parser.parse_args()

    run_query(args.query, args)


if __name__ == "__main__":
    main()
