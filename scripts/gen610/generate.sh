#!/usr/bin/env bash
set -euo pipefail

# Gen610: Barrier Grid Optimization on Cross-Asset Survivors
# Copied from: scripts/gen600/generate.sh + scripts/gen510/generate.sh
#
# Input: Top 20 cross-asset survivor configs from Gen600 analysis
# Grid: 24 barrier combos (TP × SL × max_bars)
# Assets: 10 combos (5 symbols × 2 thresholds)
# Total: 20 × 24 × 10 = 4,800 SQL files
#
# Template: sql/gen610_barrier_grid_template.sql (2down pattern only — 12/15 top configs are 2down)

echo "=== Gen610: Barrier Grid Optimization on Cross-Asset Survivors ==="

OUTDIR=/tmp/gen610_sql
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

SQLDIR="$(cd "$(dirname "$0")/../../sql" && pwd)"
TEMPLATE="${SQLDIR}/gen610_barrier_grid_template.sql"

if [ ! -f "$TEMPLATE" ]; then
    echo "ERROR: Template not found: ${TEMPLATE}"
    exit 1
fi

TEMPLATE_SHA=$(shasum -a 256 "$TEMPLATE" | cut -d' ' -f1)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# ---- Asset/Threshold Configuration ----
ALL_ASSETS=(
    "BTCUSDT|750"
    "BTCUSDT|1000"
    "ETHUSDT|750"
    "ETHUSDT|1000"
    "SOLUSDT|750"
    "SOLUSDT|1000"
    "BNBUSDT|750"
    "BNBUSDT|1000"
    "XRPUSDT|750"
    "XRPUSDT|1000"
)

# ---- Top 20 Cross-Asset Survivor Configs (from cross_asset.sh) ----
# Format: F1|S1|Q1|D1|F2|S2|Q2|D2
# All are 2down pattern (12/15 top configs are 2down)
CONFIGS=(
    "aggression_ratio|lt_p50|0.50|<|intra_kyle_lambda|gt_p50|0.50|>"
    "duration_us|lt_p50|0.50|<|lookback_duration_us|gt_p50|0.50|>"
    "turnover_imbalance|lt_p50|0.50|<|lookback_duration_us|gt_p50|0.50|>"
    "ofi|lt_p50|0.50|<|lookback_duration_us|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|intra_max_drawdown|gt_p50|0.50|>"
    "turnover_imbalance|lt_p50|0.50|<|intra_max_drawdown|gt_p50|0.50|>"
    "ofi|lt_p50|0.50|<|intra_max_drawdown|gt_p50|0.50|>"
    "turnover_imbalance|lt_p50|0.50|<|intra_garman_klass_vol|gt_p50|0.50|>"
    "ofi|lt_p50|0.50|<|intra_garman_klass_vol|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|lookback_duration_us|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|intra_garman_klass_vol|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|lookback_garman_klass_vol|gt_p50|0.50|>"
    "aggregation_density|gt_p50|0.50|>|lookback_garman_klass_vol|gt_p50|0.50|>"
    "aggregation_density|gt_p50|0.50|>|lookback_price_range|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|intra_max_runup|gt_p50|0.50|>"
    "aggression_ratio|lt_p50|0.50|<|lookback_price_range|gt_p50|0.50|>"
    "price_impact|gt_p50|0.50|>|lookback_duration_us|gt_p50|0.50|>"
    "vwap_close_deviation|gt_p50|0.50|>|lookback_price_range|gt_p50|0.50|>"
    "turnover_imbalance|lt_p50|0.50|<|lookback_garman_klass_vol|gt_p50|0.50|>"
    "ofi|lt_p50|0.50|<|lookback_garman_klass_vol|gt_p50|0.50|>"
)

# ---- Barrier Grid (24 combos) ----
# Gen510 found TP=0.25x, SL=0.50x, max_bars=100 as optimal (inverted)
# Explore around that optimum + wider range
# Format: TP_MULT|SL_MULT|MAX_BARS
BARRIERS=(
    "0.10|0.25|50"
    "0.10|0.25|100"
    "0.10|0.50|50"
    "0.10|0.50|100"
    "0.15|0.25|50"
    "0.15|0.25|100"
    "0.15|0.50|50"
    "0.15|0.50|100"
    "0.20|0.50|50"
    "0.20|0.50|100"
    "0.20|0.75|50"
    "0.20|0.75|100"
    "0.25|0.50|50"
    "0.25|0.50|100"
    "0.25|0.75|50"
    "0.25|0.75|100"
    "0.25|1.00|100"
    "0.25|1.00|200"
    "0.30|0.50|50"
    "0.30|0.50|100"
    "0.50|0.50|50"
    "0.50|0.50|100"
    "0.50|1.00|100"
    "0.50|1.00|200"
)

NUM_CONFIGS=${#CONFIGS[@]}
NUM_BARRIERS=${#BARRIERS[@]}
NUM_ASSETS=${#ALL_ASSETS[@]}
EXPECTED=$((NUM_CONFIGS * NUM_BARRIERS * NUM_ASSETS))

echo "Configs: ${NUM_CONFIGS}"
echo "Barrier combos: ${NUM_BARRIERS}"
echo "Asset combos: ${NUM_ASSETS}"
echo "Expected total: ${EXPECTED}"
echo ""

GRAND_TOTAL=0

for asset_entry in "${ALL_ASSETS[@]}"; do
    IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
    ASSET_COUNT=0

    for config in "${CONFIGS[@]}"; do
        IFS='|' read -r F1 S1 Q1 D1 F2 S2 Q2 D2 <<< "$config"
        FC="2down__${F1}_${S1}__${F2}_${S2}"

        for barrier in "${BARRIERS[@]}"; do
            IFS='|' read -r TP SL MB <<< "$barrier"

            # Barrier ID: tp025_sl050_mb100 format
            TP_ID=$(echo "$TP" | tr -d '.')
            SL_ID=$(echo "$SL" | tr -d '.')
            BARRIER_ID="tp${TP_ID}_sl${SL_ID}_mb${MB}"
            CONFIG_ID="${FC}__${BARRIER_ID}"

            # Per asset/threshold subdirectory
            ASSET_SUBDIR="${OUTDIR}/${SYMBOL}_${THRESHOLD}"
            mkdir -p "$ASSET_SUBDIR"

            sed \
                -e "s/__SYMBOL__/${SYMBOL}/g" \
                -e "s/__THRESHOLD_DBPS__/${THRESHOLD}/g" \
                -e "s/__FEATURE_COL_1__/${F1}/g" \
                -e "s/__FEATURE_COL_2__/${F2}/g" \
                -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
                -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
                -e "s/__DIRECTION_1__/${D1}/g" \
                -e "s/__DIRECTION_2__/${D2}/g" \
                -e "s/__CONFIG_ID__/${FC}/g" \
                -e "s/__TP_MULT__/${TP}/g" \
                -e "s/__SL_MULT__/${SL}/g" \
                -e "s/__MAX_BARS__/${MB}/g" \
                -e "s/__BARRIER_ID__/${BARRIER_ID}/g" \
                "$TEMPLATE" > "${ASSET_SUBDIR}/${CONFIG_ID}.sql"

            ASSET_COUNT=$((ASSET_COUNT + 1))
        done
    done

    echo "  ${SYMBOL}@${THRESHOLD}: ${ASSET_COUNT} SQL files"
    GRAND_TOTAL=$((GRAND_TOTAL + ASSET_COUNT))
done

# Save metadata
cat > "$OUTDIR/metadata.json" << EOF
{"git_commit":"${GIT_COMMIT}","template_sha":"${TEMPLATE_SHA}","num_configs":${NUM_CONFIGS},"num_barriers":${NUM_BARRIERS},"num_assets":${NUM_ASSETS},"total_sql_files":${GRAND_TOTAL}}
EOF

echo ""
echo "=== Total: ${GRAND_TOTAL} SQL files ==="
echo "  ${NUM_CONFIGS} configs x ${NUM_BARRIERS} barriers x ${NUM_ASSETS} assets"
echo "  Expected: ${EXPECTED}"
echo "  Output: ${OUTDIR}/"
