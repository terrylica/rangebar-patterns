#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen400: Fail-Fast POC (10 configs) ==="
echo ""

OUTDIR=/tmp/gen400_poc
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

TEMPLATE_2F="sql/gen400_2feature_template.sql"
TEMPLATE_3F="sql/gen400_3feature_template.sql"
TEMPLATE_4F="sql/gen400_4feature_template.sql"

LOG_FILE="/tmp/gen400_poc.jsonl"
rm -f "$LOG_FILE"

GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
SHA_2F=$(shasum -a 256 "$TEMPLATE_2F" | cut -d' ' -f1)
SHA_3F=$(shasum -a 256 "$TEMPLATE_3F" | cut -d' ' -f1)
SHA_4F=$(shasum -a 256 "$TEMPLATE_4F" | cut -d' ' -f1)

# POC configs: top features from Gen300, all at p50
# Format: n_features|feat1|feat2[|feat3[|feat4]]|q1|q2[|q3[|q4]]|d1|d2[|d3[|d4]]|config_id|template_sha|template_file
POC_CONFIGS=(
    # 5 two-feature combos
    "2|price_impact|ofi|0.50|0.50|<|<|price_impact_lt_p50__ofi_lt_p50|${SHA_2F}|${TEMPLATE_2F}"
    "2|price_impact|duration_us|0.50|0.50|<|<|price_impact_lt_p50__duration_us_lt_p50|${SHA_2F}|${TEMPLATE_2F}"
    "2|ofi|volume_per_trade|0.50|0.50|<|>|ofi_lt_p50__volume_per_trade_gt_p50|${SHA_2F}|${TEMPLATE_2F}"
    "2|price_impact|aggression_ratio|0.50|0.50|<|<|price_impact_lt_p50__aggression_ratio_lt_p50|${SHA_2F}|${TEMPLATE_2F}"
    "2|ofi|aggression_ratio|0.50|0.50|<|<|ofi_lt_p50__aggression_ratio_lt_p50|${SHA_2F}|${TEMPLATE_2F}"
    # 3 three-feature combos
    "3|price_impact|ofi|duration_us|0.50|0.50|0.50|<|<|<|price_impact_lt_p50__ofi_lt_p50__duration_us_lt_p50|${SHA_3F}|${TEMPLATE_3F}"
    "3|price_impact|ofi|aggression_ratio|0.50|0.50|0.50|<|<|<|price_impact_lt_p50__ofi_lt_p50__aggression_ratio_lt_p50|${SHA_3F}|${TEMPLATE_3F}"
    "3|ofi|volume_per_trade|duration_us|0.50|0.50|0.50|<|>|<|ofi_lt_p50__volume_per_trade_gt_p50__duration_us_lt_p50|${SHA_3F}|${TEMPLATE_3F}"
    # 2 four-feature combos
    "4|price_impact|ofi|duration_us|aggression_ratio|0.50|0.50|0.50|0.50|<|<|<|<|price_impact_lt_p50__ofi_lt_p50__duration_us_lt_p50__aggression_ratio_lt_p50|${SHA_4F}|${TEMPLATE_4F}"
    "4|price_impact|ofi|volume_per_trade|duration_us|0.50|0.50|0.50|0.50|<|<|>|<|price_impact_lt_p50__ofi_lt_p50__volume_per_trade_gt_p50__duration_us_lt_p50|${SHA_4F}|${TEMPLATE_4F}"
)

TOTAL=${#POC_CONFIGS[@]}
SUCCESS=0
FAILED=0

for (( idx=0; idx<TOTAL; idx++ )); do
    CONFIG="${POC_CONFIGS[$idx]}"
    N_FEAT=$(echo "$CONFIG" | cut -d'|' -f1)

    if [ "$N_FEAT" = "2" ]; then
        IFS='|' read -r _ F1 F2 Q1 Q2 D1 D2 CID TSHA TFILE <<< "$CONFIG"
        SQL=$(sed \
            -e "s/__FEATURE_COL_1__/${F1}/g" \
            -e "s/__FEATURE_COL_2__/${F2}/g" \
            -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
            -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
            -e "s/__DIRECTION_1__/${D1}/g" \
            -e "s/__DIRECTION_2__/${D2}/g" \
            -e "s/__CONFIG_ID__/${CID}/g" \
            "$TFILE")
        PHASE=1
    elif [ "$N_FEAT" = "3" ]; then
        IFS='|' read -r _ F1 F2 F3 Q1 Q2 Q3 D1 D2 D3 CID TSHA TFILE <<< "$CONFIG"
        SQL=$(sed \
            -e "s/__FEATURE_COL_1__/${F1}/g" \
            -e "s/__FEATURE_COL_2__/${F2}/g" \
            -e "s/__FEATURE_COL_3__/${F3}/g" \
            -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
            -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
            -e "s/__QUANTILE_PCT_3__/${Q3}/g" \
            -e "s/__DIRECTION_1__/${D1}/g" \
            -e "s/__DIRECTION_2__/${D2}/g" \
            -e "s/__DIRECTION_3__/${D3}/g" \
            -e "s/__CONFIG_ID__/${CID}/g" \
            "$TFILE")
        PHASE=2
    elif [ "$N_FEAT" = "4" ]; then
        IFS='|' read -r _ F1 F2 F3 F4 Q1 Q2 Q3 Q4 D1 D2 D3 D4 CID TSHA TFILE <<< "$CONFIG"
        SQL=$(sed \
            -e "s/__FEATURE_COL_1__/${F1}/g" \
            -e "s/__FEATURE_COL_2__/${F2}/g" \
            -e "s/__FEATURE_COL_3__/${F3}/g" \
            -e "s/__FEATURE_COL_4__/${F4}/g" \
            -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
            -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
            -e "s/__QUANTILE_PCT_3__/${Q3}/g" \
            -e "s/__QUANTILE_PCT_4__/${Q4}/g" \
            -e "s/__DIRECTION_1__/${D1}/g" \
            -e "s/__DIRECTION_2__/${D2}/g" \
            -e "s/__DIRECTION_3__/${D3}/g" \
            -e "s/__DIRECTION_4__/${D4}/g" \
            -e "s/__CONFIG_ID__/${CID}/g" \
            "$TFILE")
        PHASE=3
    fi

    echo "[$((idx+1))/${TOTAL}] ${CID} (${N_FEAT}F) ..."

    QUERY_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    START_S=$(date +%s)
    OUTPUT=$(echo "$SQL" | ssh "${RANGEBAR_CH_HOST}" 'clickhouse-client --multiquery' 2>&1) || {
        END_S=$(date +%s)
        DURATION=$((END_S - START_S))
        QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        echo "  ERROR: Query failed"
        ERROR_MSG=$(echo "$OUTPUT" | tr '"' "'" | tr '\n' ' ' | head -c 500)
        echo "{\"timestamp\":\"${QUERY_END}\",\"generation\":400,\"phase\":${PHASE},\"n_features\":${N_FEAT},\"config_id\":\"${CID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"${RANGEBAR_CH_HOST}\",\"template_file\":\"${TFILE}\",\"template_sha256\":\"${TSHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":null,\"raw_output\":\"\",\"skipped\":false,\"error\":true,\"error_message\":\"${ERROR_MSG}\"}" >> "$LOG_FILE"
        FAILED=$((FAILED + 1))
        continue
    }
    END_S=$(date +%s)
    DURATION=$((END_S - START_S))
    QUERY_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    DATA_LINE=$(echo "$OUTPUT" | tail -n 1)
    RAW_OUTPUT=$(echo "$DATA_LINE" | tr '"' "'" | tr '	' '|')

    FILTERED_SIGNALS=$(echo "$DATA_LINE" | cut -f2)
    TP_COUNT=$(echo "$DATA_LINE" | cut -f3)
    SL_COUNT=$(echo "$DATA_LINE" | cut -f4)
    TIME_COUNT=$(echo "$DATA_LINE" | cut -f5)
    INCOMPLETE_COUNT=$(echo "$DATA_LINE" | cut -f6)
    WIN_RATE=$(echo "$DATA_LINE" | cut -f7)
    PROFIT_FACTOR=$(echo "$DATA_LINE" | cut -f8)
    AVG_WIN=$(echo "$DATA_LINE" | cut -f9)
    AVG_LOSS=$(echo "$DATA_LINE" | cut -f10)
    EV_PCT=$(echo "$DATA_LINE" | cut -f11)
    AVG_BARS=$(echo "$DATA_LINE" | cut -f12)
    KELLY=$(echo "$DATA_LINE" | cut -f13)

    # Handle ClickHouse NULL (\N) and empty values
    for var in WIN_RATE PROFIT_FACTOR AVG_WIN AVG_LOSS EV_PCT AVG_BARS KELLY; do
        eval "val=\$$var"
        if [ "$val" = '\N' ] || [ -z "$val" ]; then
            eval "$var=null"
        fi
    done
    FILTERED_SIGNALS=${FILTERED_SIGNALS:-0}
    TP_COUNT=${TP_COUNT:-0}
    SL_COUNT=${SL_COUNT:-0}
    TIME_COUNT=${TIME_COUNT:-0}
    INCOMPLETE_COUNT=${INCOMPLETE_COUNT:-0}

    SKIPPED="false"
    SKIP_REASON="null"
    if [ "$FILTERED_SIGNALS" -lt 100 ] 2>/dev/null; then
        SKIPPED="true"
        SKIP_REASON="\"<100 signals (${FILTERED_SIGNALS})\""
    fi

    echo "  signals=${FILTERED_SIGNALS} Kelly=${KELLY} PF=${PROFIT_FACTOR} (${DURATION}s)"

    echo "{\"timestamp\":\"${QUERY_END}\",\"generation\":400,\"phase\":${PHASE},\"n_features\":${N_FEAT},\"config_id\":\"${CID}\",\"environment\":{\"symbol\":\"SOLUSDT\",\"threshold_dbps\":500,\"clickhouse_host\":\"${RANGEBAR_CH_HOST}\",\"template_file\":\"${TFILE}\",\"template_sha256\":\"${TSHA}\",\"git_commit\":\"${GIT_COMMIT}\",\"quantile_method\":\"rolling_1000_signal\"},\"timing\":{\"query_start_utc\":\"${QUERY_START}\",\"query_end_utc\":\"${QUERY_END}\",\"query_duration_s\":${DURATION}},\"results\":{\"filtered_signals\":${FILTERED_SIGNALS},\"tp_count\":${TP_COUNT},\"sl_count\":${SL_COUNT},\"time_count\":${TIME_COUNT},\"incomplete_count\":${INCOMPLETE_COUNT},\"win_rate\":${WIN_RATE},\"profit_factor\":${PROFIT_FACTOR},\"avg_win_pct\":${AVG_WIN},\"avg_loss_pct\":${AVG_LOSS},\"expected_value_pct\":${EV_PCT},\"avg_bars_held\":${AVG_BARS},\"kelly_fraction\":${KELLY}},\"raw_output\":\"${RAW_OUTPUT}\",\"skipped\":${SKIPPED},\"skip_reason\":${SKIP_REASON},\"error\":false,\"error_message\":null}" >> "$LOG_FILE"

    SUCCESS=$((SUCCESS + 1))
done

echo ""
echo "=== POC Complete ==="
echo "Success: ${SUCCESS}/${TOTAL}, Failed: ${FAILED}"
echo "Results: ${LOG_FILE}"

echo ""
echo "--- POC Validation ---"

# 1. JSON validity
echo -n "1. JSON validity: "
CORRUPT=$(python3 -c "
import json
corrupt = 0
for line in open('${LOG_FILE}'):
    try: json.loads(line)
    except: corrupt += 1
print(corrupt)
")
if [ "$CORRUPT" = "0" ]; then echo "PASS"; else echo "FAIL (${CORRUPT} corrupt lines)"; fi

# 2. Required fields
echo -n "2. Required fields: "
MISSING=$(python3 -c "
import json
missing = 0
for line in open('${LOG_FILE}'):
    d = json.loads(line)
    for key in ['timestamp','config_id','generation','phase','n_features','environment','timing']:
        if key not in d: missing += 1
    if d.get('environment',{}).get('quantile_method') != 'rolling_1000_signal': missing += 1
print(missing)
")
if [ "$MISSING" = "0" ]; then echo "PASS"; else echo "FAIL (${MISSING} missing)"; fi

# 3. Signal count monotonicity (more features -> fewer signals)
echo -n "3. Signal monotonicity: "
python3 << 'PYEOF'
import json
by_nf = {}
for line in open('/tmp/gen400_poc.jsonl'):
    d = json.loads(line)
    if d.get('error'): continue
    nf = d['n_features']
    sigs = d['results']['filtered_signals']
    by_nf.setdefault(nf, []).append(sigs)
avgs = {nf: sum(s)/len(s) for nf, s in by_nf.items()}
nfs = sorted(avgs.keys())
mono = all(avgs[nfs[i]] >= avgs[nfs[i+1]] for i in range(len(nfs)-1))
if mono:
    parts = [f'{nf}F avg={avgs[nf]:.0f}' for nf in nfs]
    print(f"PASS ({', '.join(parts)})")
else:
    print(f"WARN (not monotonic: {avgs})")
PYEOF

# 4. No expanding windows
echo -n "4. Quantile method: "
METHODS=$(python3 -c "
import json
methods = set()
for line in open('${LOG_FILE}'):
    d = json.loads(line)
    methods.add(d.get('environment',{}).get('quantile_method','UNKNOWN'))
print(' '.join(methods))
")
if [ "$METHODS" = "rolling_1000_signal" ]; then echo "PASS"; else echo "FAIL (${METHODS})"; fi

echo ""
if [ "$FAILED" = "0" ] && [ "$CORRUPT" = "0" ] && [ "$MISSING" = "0" ]; then
    echo "POC PASSED - Ready for full sweep submission"
else
    echo "POC FAILED - Fix issues before submitting full sweep"
fi
