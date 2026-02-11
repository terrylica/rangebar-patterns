#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

# Gen600 POC: Validate pipeline end-to-end using pre-generated SQL files.
# Picks 24 configs (1 per pattern, mix of LONG+SHORT) from the generated SQL.
# Runs on BigBlack, validates: 3 rows, 3 barrier profiles, basic metric sanity.
#
# PREREQUISITE: generate.sh must have run first.
# Usage: poc.sh [SYMBOL] [THRESHOLD]
#   Defaults to SOLUSDT 750

SYMBOL="${1:-SOLUSDT}"
THRESHOLD="${2:-750}"
CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

SQLDIR="/tmp/gen600_sql"
OUTDIR="/tmp/gen600_poc"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Pick 1 SQL file per pattern — use ofi_lt_p50__lookback_hurst_lt_p50 as standard test combo
PATTERNS=(
    2down 3down dud udd 2down_ng hvd vwap_l wl2d wl1d exh_l exh_l_ng
    2up_s 3up_s udu_s duu_s 2up_ng_s hvu_s vwap_s wl2u_s wl1u_s exh_s exh_s_ng
)

TEST_F1="ofi"
TEST_F2="lookback_hurst"
TEST_SUFFIX="${TEST_F1}_lt_p50__${TEST_F2}_lt_p50"

TOTAL=${#PATTERNS[@]}
SUCCESS=0
FAILED=0
SKIPPED=0

echo "=== Gen600: POC Validation (${TOTAL} patterns) ==="
echo "Asset: ${SYMBOL} @${THRESHOLD}"
echo "Test config: *__${TEST_SUFFIX}"
echo ""

for (( idx=0; idx<TOTAL; idx++ )); do
    SID="${PATTERNS[$idx]}"
    CONFIG_ID="${SID}__${TEST_SUFFIX}"
    SQL_LOCAL="${SQLDIR}/${SID}/${SYMBOL}_${THRESHOLD}/${CONFIG_ID}.sql"

    echo -n "[$((idx+1))/${TOTAL}] ${SID} ... "

    if [ ! -f "$SQL_LOCAL" ]; then
        echo "SKIP (SQL file not found: ${SQL_LOCAL})"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # scp to BigBlack, then run via remote file redirect
    scp -q "$SQL_LOCAL" "${CH_HOST}:/tmp/gen600_poc_query.sql"
    OUTPUT=$(ssh -n "${CH_HOST}" 'clickhouse-client --multiquery < /tmp/gen600_poc_query.sql' 2>&1) || {
        echo "ERROR: Query failed"
        echo "$OUTPUT" | head -3
        FAILED=$((FAILED + 1))
        continue
    }

    # Count data rows (excluding header)
    N_ROWS=$(echo "$OUTPUT" | tail -n +2 | grep -c . || true)

    if [ "$N_ROWS" -eq 0 ]; then
        echo "SKIP (0 rows — pattern too sparse after filter)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    if [ "$N_ROWS" -ne 3 ]; then
        echo "FAIL (expected 3 rows, got ${N_ROWS})"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Verify 3 barrier profiles present
    PROFILES=$(echo "$OUTPUT" | tail -n +2 | cut -f3 | sort | tr '\n' ',' | sed 's/,$//')
    if [ "$PROFILES" != "inverted,momentum,symmetric" ]; then
        echo "FAIL (profiles: ${PROFILES})"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Extract inverted row stats for display
    INV_ROW=$(echo "$OUTPUT" | tail -n +2 | grep "inverted")
    INV_BASE=$(echo "$INV_ROW" | cut -f5)
    INV_SIGS=$(echo "$INV_ROW" | cut -f6)
    INV_PF=$(echo "$INV_ROW" | cut -f13)
    INV_KELLY=$(echo "$INV_ROW" | cut -f17)

    echo "OK  base=${INV_BASE} sigs=${INV_SIGS} PF=${INV_PF} Kelly=${INV_KELLY}"
    echo "$OUTPUT" > "${OUTDIR}/${SID}.tsv"

    SUCCESS=$((SUCCESS + 1))
done

echo ""
echo "=== POC Summary ==="
echo "Success: ${SUCCESS}/${TOTAL}"
echo "Failed:  ${FAILED}"
echo "Skipped: ${SKIPPED} (too sparse or missing)"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo "POC PASSED — All non-skipped patterns produce valid 3-row output"
else
    echo "POC FAILED — ${FAILED} patterns had errors"
    exit 1
fi
