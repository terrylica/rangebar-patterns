"""AP-15 Verification: Compare SQL vs Python champion signals.

Usage:
    python scripts/verify_ap15_compare.py /tmp/sql_ap15_signals.tsv /tmp/python_ap15_signals.tsv

Gates:
    1. Signal count: |N_SQL - N_PY| / max(N_SQL, N_PY) < 5%
    2. Timestamp match: >95% of signals have identical timestamp_ms
    3. Entry price match: >95% of matched signals have <0.01% price difference
"""

import sys


def load_tsv(path):
    """Load TSV file, skip noise lines before header."""
    rows = []
    with open(path) as f:
        # Find the header line (starts with "timestamp_ms")
        header_line = None
        for line in f:
            if line.startswith("timestamp_ms"):
                header_line = line
                break
        if header_line is None:
            return rows
        # Parse remaining lines as TSV with that header
        header = header_line.strip().split("\t")
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) == len(header):
                rows.append(dict(zip(header, fields, strict=True)))
    return rows


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <sql_tsv> <python_tsv>")
        sys.exit(1)

    sql_rows = load_tsv(sys.argv[1])
    py_rows = load_tsv(sys.argv[2])

    print(f"SQL signals:    {len(sql_rows)}")
    print(f"Python signals: {len(py_rows)}")

    # Gate 1: Signal count alignment
    max_n = max(len(sql_rows), len(py_rows))
    if max_n == 0:
        print("FAIL: No signals found")
        sys.exit(1)

    count_diff = abs(len(sql_rows) - len(py_rows)) / max_n
    gate1 = count_diff < 0.05
    print(f"\nGate 1 - Signal Count: diff={count_diff:.4f} (<5% required) → {'PASS' if gate1 else 'FAIL'}")

    # Build lookup by timestamp
    sql_by_ts = {row["timestamp_ms"]: row for row in sql_rows}
    py_by_ts = {row["timestamp_ms"]: row for row in py_rows}

    # Gate 2: Timestamp overlap
    sql_ts = set(sql_by_ts.keys())
    py_ts = set(py_by_ts.keys())
    matched_ts = sql_ts & py_ts
    only_sql = sql_ts - py_ts
    only_py = py_ts - sql_ts

    overlap = len(matched_ts) / max_n if max_n > 0 else 0
    gate2 = overlap > 0.95
    verdict2 = "PASS" if gate2 else "FAIL"
    print(f"Gate 2 - Timestamp Match: {len(matched_ts)}/{max_n} ({overlap:.4f}) (>95%) → {verdict2}")

    if only_sql:
        print(f"  SQL-only timestamps: {len(only_sql)} (first 5: {sorted(only_sql)[:5]})")
    if only_py:
        print(f"  Python-only timestamps: {len(only_py)} (first 5: {sorted(only_py)[:5]})")

    # Gate 3: Entry price alignment on matched signals
    price_matches = 0
    price_mismatches = []
    for ts in sorted(matched_ts):
        sql_ep = float(sql_by_ts[ts]["entry_price"])
        py_ep = float(py_by_ts[ts]["entry_price"])
        if py_ep > 0:
            diff = abs(sql_ep - py_ep) / py_ep
            if diff < 0.0001:  # 0.01%
                price_matches += 1
            else:
                price_mismatches.append((ts, sql_ep, py_ep, diff))

    if len(matched_ts) > 0:
        price_match_rate = price_matches / len(matched_ts)
        gate3 = price_match_rate > 0.95
        verdict3 = "PASS" if gate3 else "FAIL"
        print(f"Gate 3 - Entry Price: {price_matches}/{len(matched_ts)} ({price_match_rate:.4f}) (>95%) → {verdict3}")
    else:
        gate3 = False
        print("Gate 3 - Entry Price: No matched signals to compare → FAIL")

    if price_mismatches:
        print("  Price mismatches (first 5):")
        for ts, sql_ep, py_ep, diff in price_mismatches[:5]:
            print(f"    ts={ts}: SQL={sql_ep:.8f} PY={py_ep:.8f} diff={diff:.6f}")

    # Overall verdict
    print(f"\n{'='*50}")
    all_pass = gate1 and gate2 and gate3
    print(f"OVERALL: {'ALL GATES PASS ✓' if all_pass else 'SOME GATES FAILED ✗'}")
    print(f"  Gate 1 (Count):  {'PASS' if gate1 else 'FAIL'}")
    print(f"  Gate 2 (Timing): {'PASS' if gate2 else 'FAIL'}")
    print(f"  Gate 3 (Price):  {'PASS' if gate3 else 'FAIL'}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
