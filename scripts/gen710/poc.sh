#!/usr/bin/env bash
# shellcheck disable=SC2029
set -euo pipefail

# Gen710 POC: Validate time-decay barrier SQL end-to-end.
# Runs 3 configs to verify two-segment SL scan works correctly.
# Copied from: scripts/gen610/poc.sh
#
# PREREQUISITE: generate.sh must have run first.
# Usage: poc.sh
# GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/27

CH_HOST="${RANGEBAR_CH_HOST:?Set RANGEBAR_CH_HOST}"

SQLDIR="/tmp/gen710_sql"
OUTDIR="/tmp/gen710_poc"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

FC="2down__turnover_imbalance_lt_p25__price_impact_lt_p25"

echo "=== Gen710: POC Validation ==="
echo "Config: ${FC}"
echo "Asset: SOLUSDT@500"
echo ""

# Test 3 barrier combos spanning the parameter range
# Gen710 output columns (1-indexed):
#   1:config_id 2:base_pattern 3:barrier_id 4:tp_mult 5:sl_wide 6:sl_tight
#   7:phase1_bars 8:max_bars 9:total_bars 10:base_signals 11:filtered_signals
#   12:signal_coverage 13:tp_count 14:sl_count 15:time_count 16:incomplete_count
#   17:win_rate 18:profit_factor 19:avg_win_pct 20:avg_loss_pct 21:expected_value_pct
#   22:kelly_fraction 23:avg_bars_held 24:median_exit_bar 25:signal_min_ts_ms
#   26:signal_max_ts_ms 27:total_return

TESTS=(
    "p5_slt025_mb100|SL tightening 0.50 -> 0.25 after 5 bars, max 100"
    "p5_slt010_mb50|SL tightening 0.50 -> 0.10 after 5 bars, max 50"
    "p3_slt000_mb30|Breakeven SL after 3 bars, max 30"
)

ALL_PASS=true

for test_entry in "${TESTS[@]}"; do
    IFS='|' read -r BARRIER_ID DESC <<< "$test_entry"
    SQL_FILE="${SQLDIR}/${FC}__${BARRIER_ID}.sql"

    echo -n "Test: ${DESC}... "

    if [ ! -f "$SQL_FILE" ]; then
        echo "FAIL (SQL file not found: ${SQL_FILE})"
        echo "Run generate.sh first."
        ALL_PASS=false
        continue
    fi

    scp -q "$SQL_FILE" "${CH_HOST}:/tmp/gen710_poc_query.sql"
    OUTPUT=$(ssh -n "${CH_HOST}" 'clickhouse-client --multiquery < /tmp/gen710_poc_query.sql' 2>&1) || {
        echo "FAIL (query error)"
        echo "$OUTPUT" | head -3
        ALL_PASS=false
        continue
    }

    N_ROWS=$(echo "$OUTPUT" | tail -n +2 | grep -c . || true)

    if [ "$N_ROWS" -ne 1 ]; then
        echo "FAIL (expected 1 row, got ${N_ROWS})"
        ALL_PASS=false
        continue
    fi

    DATA=$(echo "$OUTPUT" | tail -n +2)
    SIGNALS=$(echo "$DATA" | cut -f11)
    WR=$(echo "$DATA" | cut -f17)
    PF=$(echo "$DATA" | cut -f18)
    KELLY=$(echo "$DATA" | cut -f22)
    P1_BARS=$(echo "$DATA" | cut -f7)
    SL_TIGHT=$(echo "$DATA" | cut -f6)
    MB=$(echo "$DATA" | cut -f8)

    echo "OK"
    echo "    Barrier: phase1=${P1_BARS} sl_tight=${SL_TIGHT}x max_bars=${MB}"
    echo "    Signals: ${SIGNALS}  WR: ${WR}  PF: ${PF}  Kelly: ${KELLY}"
    echo ""

    echo "$OUTPUT" > "${OUTDIR}/${BARRIER_ID}.tsv"
done

# Validation gate: baseline comparison
# The p5_slt025_mb100 config (mild tightening) should produce similar signals
# to the champion baseline (111 trades with TP=0.25x SL=0.50x max_bars=100)
echo "--- Baseline Check ---"
BASELINE_TSV="${OUTDIR}/p5_slt025_mb100.tsv"
if [ -f "$BASELINE_TSV" ]; then
    BASELINE_SIGNALS=$(tail -n +2 "$BASELINE_TSV" | cut -f11)
    echo "Time-decay signals (p5_slt025_mb100): ${BASELINE_SIGNALS}"
    echo "Champion baseline: 111 trades"
    echo "(Signal count should match — time-decay only changes exits, not entries)"
fi

echo ""
if $ALL_PASS; then
    echo "=== POC PASSED — all 3 configs executed successfully ==="
else
    echo "=== POC FAILED — check errors above ==="
    exit 1
fi
