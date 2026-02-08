#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen400: Pre-Generate All SQL Files ==="

OUTDIR=/tmp/gen400_sql
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR/2f" "$OUTDIR/3f" "$OUTDIR/4f"

# 8 candidate features
FEATURES=(ofi aggression_ratio turnover_imbalance price_impact vwap_close_deviation volume_per_trade aggregation_density duration_us)

# 6 quantile/direction combos for phases 1+2
GRID_FULL=(
    "0.50|>|gt_p50"
    "0.50|<|lt_p50"
    "0.75|>|gt_p75"
    "0.25|<|lt_p25"
    "0.90|>|gt_p90"
    "0.10|<|lt_p10"
)

# 2 combos for phase 3 (p50 only)
GRID_P50=(
    "0.50|>|gt_p50"
    "0.50|<|lt_p50"
)

TEMPLATE_2F="sql/gen400_2feature_template.sql"
TEMPLATE_3F="sql/gen400_3feature_template.sql"
TEMPLATE_4F="sql/gen400_4feature_template.sql"

# Barrier parameters from mise [env]
TP_MULT="${RBP_TP_MULT:-0.5}"
SL_MULT="${RBP_SL_MULT:-0.25}"
MAX_BARS="${RBP_MAX_BARS:-50}"
MAX_BARS_PLUS1=$((MAX_BARS + 1))

SHA_2F=$(shasum -a 256 "$TEMPLATE_2F" | cut -d' ' -f1)
SHA_3F=$(shasum -a 256 "$TEMPLATE_3F" | cut -d' ' -f1)
SHA_4F=$(shasum -a 256 "$TEMPLATE_4F" | cut -d' ' -f1)

# Save template SHAs for telemetry
cat > "$OUTDIR/template_shas.json" <<EOF
{"2f":"${SHA_2F}","3f":"${SHA_3F}","4f":"${SHA_4F}"}
EOF

GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "$GIT_COMMIT" > "$OUTDIR/git_commit.txt"

COUNT_2F=0
COUNT_3F=0
COUNT_4F=0

NUM_FEAT=${#FEATURES[@]}

echo ""
echo "--- Phase 1: 2-Feature Combinations ---"
for (( i=0; i<NUM_FEAT; i++ )); do
    for (( j=i+1; j<NUM_FEAT; j++ )); do
        F1="${FEATURES[$i]}"
        F2="${FEATURES[$j]}"
        for g1 in "${GRID_FULL[@]}"; do
            IFS='|' read -r Q1 D1 S1 <<< "$g1"
            for g2 in "${GRID_FULL[@]}"; do
                IFS='|' read -r Q2 D2 S2 <<< "$g2"
                COUNT_2F=$((COUNT_2F + 1))
                CONFIG_ID="${F1}_${S1}__${F2}_${S2}"

                sed \
                    -e "s/__FEATURE_COL_1__/${F1}/g" \
                    -e "s/__FEATURE_COL_2__/${F2}/g" \
                    -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
                    -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
                    -e "s/__DIRECTION_1__/${D1}/g" \
                    -e "s/__DIRECTION_2__/${D2}/g" \
                    -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
                    -e "s/__TP_MULT__/${TP_MULT}/g" \
                    -e "s/__SL_MULT__/${SL_MULT}/g" \
                    -e "s/__MAX_BARS__/${MAX_BARS}/g" \
                    -e "s/__MAX_BARS_PLUS1__/${MAX_BARS_PLUS1}/g" \
                    "$TEMPLATE_2F" > "$OUTDIR/2f/${CONFIG_ID}.sql"
            done
        done
    done
done
echo "  Generated: ${COUNT_2F} files"

echo ""
echo "--- Phase 2: 3-Feature Combinations ---"
for (( i=0; i<NUM_FEAT; i++ )); do
    for (( j=i+1; j<NUM_FEAT; j++ )); do
        for (( k=j+1; k<NUM_FEAT; k++ )); do
            F1="${FEATURES[$i]}"
            F2="${FEATURES[$j]}"
            F3="${FEATURES[$k]}"
            for g1 in "${GRID_FULL[@]}"; do
                IFS='|' read -r Q1 D1 S1 <<< "$g1"
                for g2 in "${GRID_FULL[@]}"; do
                    IFS='|' read -r Q2 D2 S2 <<< "$g2"
                    for g3 in "${GRID_FULL[@]}"; do
                        IFS='|' read -r Q3 D3 S3 <<< "$g3"
                        COUNT_3F=$((COUNT_3F + 1))
                        CONFIG_ID="${F1}_${S1}__${F2}_${S2}__${F3}_${S3}"

                        sed \
                            -e "s/__FEATURE_COL_1__/${F1}/g" \
                            -e "s/__FEATURE_COL_2__/${F2}/g" \
                            -e "s/__FEATURE_COL_3__/${F3}/g" \
                            -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
                            -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
                            -e "s/__QUANTILE_PCT_3__/${Q3}/g" \
                            -e "s/__DIRECTION_1__/${D1}/g" \
                            -e "s/__DIRECTION_2__/${D2}/g" \
                            -e "s/__DIRECTION_3__/${D3}/g" \
                            -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
                            -e "s/__TP_MULT__/${TP_MULT}/g" \
                            -e "s/__SL_MULT__/${SL_MULT}/g" \
                            -e "s/__MAX_BARS__/${MAX_BARS}/g" \
                            -e "s/__MAX_BARS_PLUS1__/${MAX_BARS_PLUS1}/g" \
                            "$TEMPLATE_3F" > "$OUTDIR/3f/${CONFIG_ID}.sql"
                    done
                done
            done
        done
    done
done
echo "  Generated: ${COUNT_3F} files"

echo ""
echo "--- Phase 3: 4-Feature Combinations (p50 only) ---"
for (( i=0; i<NUM_FEAT; i++ )); do
    for (( j=i+1; j<NUM_FEAT; j++ )); do
        for (( k=j+1; k<NUM_FEAT; k++ )); do
            for (( l=k+1; l<NUM_FEAT; l++ )); do
                F1="${FEATURES[$i]}"
                F2="${FEATURES[$j]}"
                F3="${FEATURES[$k]}"
                F4="${FEATURES[$l]}"
                for g1 in "${GRID_P50[@]}"; do
                    IFS='|' read -r Q1 D1 S1 <<< "$g1"
                    for g2 in "${GRID_P50[@]}"; do
                        IFS='|' read -r Q2 D2 S2 <<< "$g2"
                        for g3 in "${GRID_P50[@]}"; do
                            IFS='|' read -r Q3 D3 S3 <<< "$g3"
                            for g4 in "${GRID_P50[@]}"; do
                                IFS='|' read -r Q4 D4 S4 <<< "$g4"
                                COUNT_4F=$((COUNT_4F + 1))
                                CONFIG_ID="${F1}_${S1}__${F2}_${S2}__${F3}_${S3}__${F4}_${S4}"

                                sed \
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
                                    -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
                                    -e "s/__TP_MULT__/${TP_MULT}/g" \
                                    -e "s/__SL_MULT__/${SL_MULT}/g" \
                                    -e "s/__MAX_BARS__/${MAX_BARS}/g" \
                                    -e "s/__MAX_BARS_PLUS1__/${MAX_BARS_PLUS1}/g" \
                                    "$TEMPLATE_4F" > "$OUTDIR/4f/${CONFIG_ID}.sql"
                            done
                        done
                    done
                done
            done
        done
    done
done
echo "  Generated: ${COUNT_4F} files"

TOTAL=$((COUNT_2F + COUNT_3F + COUNT_4F))
echo ""
echo "=== Total: ${TOTAL} SQL files ==="
echo "  2-feature: ${COUNT_2F} in $OUTDIR/2f/"
echo "  3-feature: ${COUNT_3F} in $OUTDIR/3f/"
echo "  4-feature: ${COUNT_4F} in $OUTDIR/4f/"
echo "  Template SHAs: $OUTDIR/template_shas.json"
