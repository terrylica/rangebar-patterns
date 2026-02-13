"""Gen600 Oracle: exh_l pattern variant — thin wrapper around gen600_oracle_compare.py.

ADR: docs/adr/2026-02-06-repository-creation.md
GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/14

Delegates to the parameterized oracle comparison script with exh_l-specific defaults.

Usage:
    uv run --python 3.13 python scripts/gen600_oracle_compare_exh_l.py \
        --sql-tsv /tmp/sql_exh_l_solusdt_750_trades.tsv \
        --symbol SOLUSDT --threshold 750

Equivalent to:
    uv run --python 3.13 python scripts/gen600_oracle_compare.py \
        --sql-tsv /tmp/sql_exh_l_solusdt_750_trades.tsv \
        --symbol SOLUSDT --threshold 750 \
        --pattern exh_l \
        --feature1 opposite_wick_pct --dir1 lt --q1 0.50 \
        --feature2 intra_garman_klass_vol --dir2 gt --q2 0.50 \
        --tp-mult 0.25 --sl-mult 0.50 --max-bars 100 \
        --extra-columns intra_max_drawdown,intra_garman_klass_vol
"""

import sys

if __name__ == "__main__":
    # Inject exh_l defaults, then delegate to the canonical script
    defaults = [
        "--pattern", "exh_l",
        "--feature1", "opposite_wick_pct", "--dir1", "lt", "--q1", "0.50",
        "--feature2", "intra_garman_klass_vol", "--dir2", "gt", "--q2", "0.50",
        "--tp-mult", "0.25", "--sl-mult", "0.50", "--max-bars", "100",
        "--extra-columns", "intra_max_drawdown,intra_garman_klass_vol",
    ]

    # Only inject defaults for args not already provided by the user
    provided = set(sys.argv[1:])
    args_to_inject = []
    i = 0
    while i < len(defaults):
        flag = defaults[i]
        if flag.startswith("--") and flag not in provided:
            args_to_inject.extend([defaults[i], defaults[i + 1]])
        i += 2

    sys.argv[1:1] = args_to_inject

    from gen600_oracle_compare import main
    main()
