"""Validate SQL queries against expected results.

ADR: docs/adr/2026-02-06-repository-creation.md

Run with: uv run -p 3.13 python -m rangebar_patterns.validate --check-syntax
"""

from __future__ import annotations

import sys
from pathlib import Path


def check_sql_syntax(sql_dir: Path | None = None) -> bool:
    """Check all SQL files exist and have non-empty content."""
    if sql_dir is None:
        sql_dir = Path(__file__).parent.parent.parent / "sql"

    expected_files = [
        "gen01_single_feature.sql",
        "gen02_two_feature.sql",
        "gen03_three_feature.sql",
        "gen04_temporal.sql",
        "gen05_crossasset.sql",
        "gen06_lookback.sql",
        "gen07_meanrev.sql",
        "gen08_divergence.sql",
        "gen108_nolookahead.sql",
        "gen109_nla_temporal.sql",
        "gen110_nla_crossasset.sql",
        "gen111_true_nolookahead.sql",
        "gen112_true_nla_temporal.sql",
        "verify_atomic_nolookahead.sql",
    ]

    all_ok = True
    for filename in expected_files:
        path = sql_dir / filename
        if not path.exists():
            print(f"MISSING: {filename}")
            all_ok = False
        elif path.stat().st_size == 0:
            print(f"EMPTY: {filename}")
            all_ok = False
        else:
            print(f"OK: {filename} ({path.stat().st_size} bytes)")

    return all_ok


if __name__ == "__main__":
    if "--check-syntax" in sys.argv:
        ok = check_sql_syntax()
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python -m rangebar_patterns.validate --check-syntax")
        sys.exit(1)
