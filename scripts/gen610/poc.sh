#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

# Gen610 POC: Validate pipeline end-to-end before full sweep.
# Picks 1 config × 1 barrier × 1 asset from generated SQL.
# Copied from: scripts/gen600/poc.sh
#
# PREREQUISITE: generate.sh must have run first.
# Usage: poc.sh [SYMBOL] [THRESHOLD]

SYMBOL="${1:-SOLUSDT}"
THRESHOLD="${2:-750}"
CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

SQLDIR="/tmp/gen610_sql"
OUTDIR="/tmp/gen610_poc"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

# Pick the top-1 config + the Gen510 optimal barrier (inverted: TP=0.25, SL=0.50, max_bars=100)
TEST_CONFIG="2down__aggression_ratio_lt_p50__intra_kyle_lambda_gt_p50__tp025_sl050_mb100"
SQL_LOCAL="${SQLDIR}/${SYMBOL}_${THRESHOLD}/${TEST_CONFIG}.sql"

echo "=== Gen610: POC Validation ==="
echo "Asset: ${SYMBOL}@${THRESHOLD}"
echo "Config: ${TEST_CONFIG}"
echo ""

if [ ! -f "$SQL_LOCAL" ]; then
    echo "ERROR: SQL file not found: ${SQL_LOCAL}"
    echo "Run generate.sh first."
    exit 1
fi

# Upload and run
scp -q "$SQL_LOCAL" "${CH_HOST}:/tmp/gen610_poc_query.sql"
echo -n "Running query... "
OUTPUT=$(ssh -n "${CH_HOST}" 'clickhouse-client --multiquery < /tmp/gen610_poc_query.sql' 2>&1) || {
    echo "ERROR: Query failed"
    echo "$OUTPUT" | head -5
    exit 1
}

# Count data rows (excluding header)
N_ROWS=$(echo "$OUTPUT" | tail -n +2 | grep -c . || true)

if [ "$N_ROWS" -eq 0 ]; then
    echo "FAIL (0 rows — no signals after filter)"
    exit 1
fi

if [ "$N_ROWS" -ne 1 ]; then
    echo "FAIL (expected 1 row, got ${N_ROWS})"
    exit 1
fi

# Parse single data row
DATA=$(echo "$OUTPUT" | tail -n +2)

CONFIG_ID=$(echo "$DATA" | cut -f1)
BARRIER_ID=$(echo "$DATA" | cut -f3)
TP_MULT=$(echo "$DATA" | cut -f4)
SL_MULT=$(echo "$DATA" | cut -f5)
MAX_BARS=$(echo "$DATA" | cut -f6)
SIGNALS=$(echo "$DATA" | cut -f9)
KELLY=$(echo "$DATA" | cut -f22)
PF=$(echo "$DATA" | cut -f16)
WR=$(echo "$DATA" | cut -f15)

echo "OK"
echo ""
echo "  Config:    ${CONFIG_ID}"
echo "  Barrier:   ${BARRIER_ID} (TP=${TP_MULT}x SL=${SL_MULT}x max_bars=${MAX_BARS})"
echo "  Signals:   ${SIGNALS}"
echo "  Win Rate:  ${WR}"
echo "  PF:        ${PF}"
echo "  Kelly:     ${KELLY}"
echo ""

echo "$OUTPUT" > "${OUTDIR}/poc_result.tsv"

# Validate basic sanity
if [ "$(echo "$SIGNALS" | cut -d'.' -f1)" -lt 30 ]; then
    echo "WARNING: Low signal count (${SIGNALS}) — config may be too sparse"
fi

echo "=== POC PASSED ==="
echo "Result saved: ${OUTDIR}/poc_result.tsv"

# Also test a second barrier combo to verify parameterization works
echo ""
echo "--- Bonus: Testing a different barrier combo ---"
TEST_CONFIG2="2down__aggression_ratio_lt_p50__intra_kyle_lambda_gt_p50__tp010_sl025_mb50"
SQL_LOCAL2="${SQLDIR}/${SYMBOL}_${THRESHOLD}/${TEST_CONFIG2}.sql"

if [ -f "$SQL_LOCAL2" ]; then
    scp -q "$SQL_LOCAL2" "${CH_HOST}:/tmp/gen610_poc_query2.sql"
    echo -n "Running barrier TP=0.10 SL=0.25 max_bars=50... "
    OUTPUT2=$(ssh -n "${CH_HOST}" 'clickhouse-client --multiquery < /tmp/gen610_poc_query2.sql' 2>&1) || {
        echo "ERROR"
        exit 1
    }
    N_ROWS2=$(echo "$OUTPUT2" | tail -n +2 | grep -c . || true)
    if [ "$N_ROWS2" -eq 1 ]; then
        KELLY2=$(echo "$OUTPUT2" | tail -n +2 | cut -f22)
        SIGNALS2=$(echo "$OUTPUT2" | tail -n +2 | cut -f9)
        echo "OK (signals=${SIGNALS2}, Kelly=${KELLY2})"
    else
        echo "UNEXPECTED (${N_ROWS2} rows)"
    fi
else
    echo "SKIP (SQL file not generated for this combo)"
fi
