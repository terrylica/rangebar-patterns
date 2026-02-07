#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen520: Multi-Threshold 2-Feature Sweep (SOLUSDT) ==="

OUTDIR=/tmp/gen520_sql
rm -rf "$OUTDIR"

# Thresholds to test (skip @100 — 5.7M bars too slow, skip @500 — already done in Gen400)
THRESHOLDS=(250 750 1000)

FEATURES=(ofi aggression_ratio turnover_imbalance price_impact vwap_close_deviation volume_per_trade aggregation_density duration_us)

GRID_FULL=(
    "0.50|>|gt_p50"
    "0.50|<|lt_p50"
    "0.75|>|gt_p75"
    "0.25|<|lt_p25"
    "0.90|>|gt_p90"
    "0.10|<|lt_p10"
)

# Reuse Gen500 template (already parameterized for symbol + threshold)
TEMPLATE="sql/gen500_2feature_template.sql"
TEMPLATE_SHA=$(shasum -a 256 "$TEMPLATE" | cut -d' ' -f1)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

TOTAL_COUNT=0

for THRESHOLD in "${THRESHOLDS[@]}"; do
    THRESH_DIR="${OUTDIR}/SOLUSDT_${THRESHOLD}"
    mkdir -p "$THRESH_DIR"

    COUNT=0
    NUM_FEAT=${#FEATURES[@]}

    for (( i=0; i<NUM_FEAT; i++ )); do
        for (( j=i+1; j<NUM_FEAT; j++ )); do
            F1="${FEATURES[$i]}"
            F2="${FEATURES[$j]}"
            for g1 in "${GRID_FULL[@]}"; do
                IFS='|' read -r Q1 D1 S1 <<< "$g1"
                for g2 in "${GRID_FULL[@]}"; do
                    IFS='|' read -r Q2 D2 S2 <<< "$g2"
                    COUNT=$((COUNT + 1))
                    CONFIG_ID="${F1}_${S1}__${F2}_${S2}"

                    sed \
                        -e "s/__SYMBOL__/SOLUSDT/g" \
                        -e "s/__THRESHOLD_DBPS__/${THRESHOLD}/g" \
                        -e "s/__FEATURE_COL_1__/${F1}/g" \
                        -e "s/__FEATURE_COL_2__/${F2}/g" \
                        -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
                        -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
                        -e "s/__DIRECTION_1__/${D1}/g" \
                        -e "s/__DIRECTION_2__/${D2}/g" \
                        -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
                        "$TEMPLATE" > "${THRESH_DIR}/${CONFIG_ID}.sql"
                done
            done
        done
    done

    echo "  SOLUSDT@${THRESHOLD}: ${COUNT} SQL files"
    TOTAL_COUNT=$((TOTAL_COUNT + COUNT))
done

cat > "$OUTDIR/metadata.json" <<EOF
{"template_sha":"${TEMPLATE_SHA}","git_commit":"${GIT_COMMIT}","template_file":"${TEMPLATE}"}
EOF

echo ""
echo "=== Total: ${TOTAL_COUNT} SQL files across ${#THRESHOLDS[@]} thresholds ==="
echo "  Output: ${OUTDIR}/"
