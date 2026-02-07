#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen500: Cross-Asset 2-Feature Sweep — Generate SQL ==="

OUTDIR=/tmp/gen500_sql
rm -rf "$OUTDIR"

# ---- Asset Configuration ----
# Phase A: All 9 altcoins @500dbps (full 2F grid)
ASSETS_500=(
    "DOGEUSDT|500"
    "XRPUSDT|500"
    "LINKUSDT|500"
    "MATICUSDT|500"
    "NEARUSDT|500"
    "ADAUSDT|500"
    "AVAXUSDT|500"
    "LTCUSDT|500"
    "DOTUSDT|500"
)

# Phase B: BTC/ETH/BNB @250dbps (no @500 data for these)
ASSETS_250=(
    "BTCUSDT|250"
    "ETHUSDT|250"
    "BNBUSDT|250"
)

# Combine all assets
ALL_ASSETS=("${ASSETS_500[@]}" "${ASSETS_250[@]}")

# 8 candidate features (same as Gen400)
FEATURES=(ofi aggression_ratio turnover_imbalance price_impact vwap_close_deviation volume_per_trade aggregation_density duration_us)

# 6 quantile/direction combos (same as Gen400)
GRID_FULL=(
    "0.50|>|gt_p50"
    "0.50|<|lt_p50"
    "0.75|>|gt_p75"
    "0.25|<|lt_p25"
    "0.90|>|gt_p90"
    "0.10|<|lt_p10"
)

TEMPLATE="sql/gen500_2feature_template.sql"
TEMPLATE_SHA=$(shasum -a 256 "$TEMPLATE" | cut -d' ' -f1)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

TOTAL_COUNT=0

for asset_entry in "${ALL_ASSETS[@]}"; do
    IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"

    # Create per-asset subfolder
    ASSET_DIR="${OUTDIR}/${SYMBOL}_${THRESHOLD}"
    mkdir -p "$ASSET_DIR"

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
                        -e "s/__SYMBOL__/${SYMBOL}/g" \
                        -e "s/__THRESHOLD_DBPS__/${THRESHOLD}/g" \
                        -e "s/__FEATURE_COL_1__/${F1}/g" \
                        -e "s/__FEATURE_COL_2__/${F2}/g" \
                        -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
                        -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
                        -e "s/__DIRECTION_1__/${D1}/g" \
                        -e "s/__DIRECTION_2__/${D2}/g" \
                        -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
                        "$TEMPLATE" > "${ASSET_DIR}/${CONFIG_ID}.sql"
                done
            done
        done
    done

    echo "  ${SYMBOL}@${THRESHOLD}: ${COUNT} SQL files"
    TOTAL_COUNT=$((TOTAL_COUNT + COUNT))
done

# Save metadata for telemetry
cat > "$OUTDIR/metadata.json" <<EOF
{"template_sha":"${TEMPLATE_SHA}","git_commit":"${GIT_COMMIT}","template_file":"${TEMPLATE}"}
EOF

echo ""
echo "=== Total: ${TOTAL_COUNT} SQL files across ${#ALL_ASSETS[@]} assets ==="
echo "  9 altcoins @500dbps: $((${#ASSETS_500[@]} * 1008)) files"
echo "  3 majors @250dbps:   $((${#ASSETS_250[@]} * 1008)) files"
echo "  Output: ${OUTDIR}/"
