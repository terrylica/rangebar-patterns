#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen600: Hybrid Feature Sweep — Generate SQL ==="

OUTDIR=/tmp/gen600_sql
rm -rf "$OUTDIR"

SQLDIR="$(cd "$(dirname "$0")/../../sql" && pwd)"

# ---- Asset/Threshold Configuration ----
# 5 assets x 2 thresholds = 10 combos
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

# ---- 22 Templates (11 LONG + 11 SHORT) ----
# Format: template_file|short_id
TEMPLATES=(
    "gen600_2down_template.sql|2down"
    "gen600_3down_template.sql|3down"
    "gen600_dud_template.sql|dud"
    "gen600_udd_template.sql|udd"
    "gen600_2down_ng_template.sql|2down_ng"
    "gen600_hvd_template.sql|hvd"
    "gen600_vwap_l_template.sql|vwap_l"
    "gen600_wl2d_template.sql|wl2d"
    "gen600_wl1d_template.sql|wl1d"
    "gen600_exh_l_template.sql|exh_l"
    "gen600_exh_l_ng_template.sql|exh_l_ng"
    "gen600_2up_s_template.sql|2up_s"
    "gen600_3up_s_template.sql|3up_s"
    "gen600_udu_s_template.sql|udu_s"
    "gen600_duu_s_template.sql|duu_s"
    "gen600_2up_ng_s_template.sql|2up_ng_s"
    "gen600_hvu_s_template.sql|hvu_s"
    "gen600_vwap_s_template.sql|vwap_s"
    "gen600_wl2u_s_template.sql|wl2u_s"
    "gen600_wl1u_s_template.sql|wl1u_s"
    "gen600_exh_s_template.sql|exh_s"
    "gen600_exh_s_ng_template.sql|exh_s_ng"
)

# ---- Feature Lists ----
# 9 bar-level features (8 original + opposite_wick_pct computed inline)
BAR_FEATURES=(
    ofi
    aggression_ratio
    turnover_imbalance
    price_impact
    vwap_close_deviation
    volume_per_trade
    aggregation_density
    duration_us
    opposite_wick_pct
)

# 38 lookback/intra features (16 lookback + 22 intra)
CROSS_FEATURES=(
    lookback_ofi
    lookback_intensity
    lookback_hurst
    lookback_permutation_entropy
    lookback_garman_klass_vol
    lookback_kaufman_er
    lookback_burstiness
    lookback_volume_skew
    lookback_volume_kurt
    lookback_price_range
    lookback_vwap_raw
    lookback_vwap_position
    lookback_count_imbalance
    lookback_kyle_lambda
    lookback_trade_count
    lookback_duration_us
    intra_bull_epoch_density
    intra_bear_epoch_density
    intra_bull_excess_gain
    intra_bear_excess_gain
    intra_bull_cv
    intra_bear_cv
    intra_max_drawdown
    intra_max_runup
    intra_trade_count
    intra_ofi
    intra_duration_us
    intra_intensity
    intra_vwap_position
    intra_count_imbalance
    intra_kyle_lambda
    intra_burstiness
    intra_volume_skew
    intra_volume_kurt
    intra_kaufman_er
    intra_garman_klass_vol
    intra_hurst
    intra_permutation_entropy
)

# ---- Quantile Grid (Phase 1: p50 only) ----
# 4 combos: gt_p50 x gt_p50, gt_p50 x lt_p50, lt_p50 x gt_p50, lt_p50 x lt_p50
GRID=(
    "0.50|>|gt_p50"
    "0.50|<|lt_p50"
)

# ---- Provenance ----
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# ---- Generate ----
GRAND_TOTAL=0
NUM_BAR=${#BAR_FEATURES[@]}
NUM_CROSS=${#CROSS_FEATURES[@]}
NUM_TEMPLATES=${#TEMPLATES[@]}
NUM_ASSETS=${#ALL_ASSETS[@]}

echo "Templates: ${NUM_TEMPLATES}"
echo "Feature pairs: $((NUM_BAR * NUM_CROSS)) (${NUM_BAR} bar-level x ${NUM_CROSS} lookback/intra)"
echo "Quantile combos per pair: 4 (2 directions x 2 directions)"
echo "Asset/threshold combos: ${NUM_ASSETS}"
echo ""

for asset_entry in "${ALL_ASSETS[@]}"; do
    IFS='|' read -r SYMBOL THRESHOLD <<< "$asset_entry"
    ASSET_COUNT=0

    for tpl_entry in "${TEMPLATES[@]}"; do
        IFS='|' read -r TFILE SID <<< "$tpl_entry"
        TPL_PATH="${SQLDIR}/${TFILE}"

        # Per-pattern/asset/threshold subdirectory
        PATTERN_DIR="${OUTDIR}/${SID}/${SYMBOL}_${THRESHOLD}"
        mkdir -p "$PATTERN_DIR"

        for (( i=0; i<NUM_BAR; i++ )); do
            F1="${BAR_FEATURES[$i]}"

            for (( j=0; j<NUM_CROSS; j++ )); do
                F2="${CROSS_FEATURES[$j]}"

                for g1 in "${GRID[@]}"; do
                    IFS='|' read -r Q1 D1 S1 <<< "$g1"

                    for g2 in "${GRID[@]}"; do
                        IFS='|' read -r Q2 D2 S2 <<< "$g2"

                        CONFIG_ID="${SID}__${F1}_${S1}__${F2}_${S2}"

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
                            "$TPL_PATH" > "${PATTERN_DIR}/${CONFIG_ID}.sql"

                        ASSET_COUNT=$((ASSET_COUNT + 1))
                    done
                done
            done
        done
    done

    echo "  ${SYMBOL}@${THRESHOLD}: ${ASSET_COUNT} SQL files"
    GRAND_TOTAL=$((GRAND_TOTAL + ASSET_COUNT))
done

# ---- Save metadata for telemetry ----
# Build template SHA JSON fragment inline
SHA_JSON="{"
FIRST=true
for tpl_entry in "${TEMPLATES[@]}"; do
    IFS='|' read -r TFILE SID <<< "$tpl_entry"
    SHA=$(shasum -a 256 "${SQLDIR}/${TFILE}" | cut -d' ' -f1)
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        SHA_JSON="${SHA_JSON},"
    fi
    SHA_JSON="${SHA_JSON}\"${SID}\":\"${SHA}\""
done
SHA_JSON="${SHA_JSON}}"

cat > "$OUTDIR/metadata.json" <<EOF
{"git_commit":"${GIT_COMMIT}","template_shas":${SHA_JSON},"num_templates":${NUM_TEMPLATES},"num_bar_features":${NUM_BAR},"num_cross_features":${NUM_CROSS},"num_assets":${NUM_ASSETS},"total_sql_files":${GRAND_TOTAL}}
EOF

echo ""
echo "=== Total: ${GRAND_TOTAL} SQL files ==="
echo "  ${NUM_TEMPLATES} templates x ${NUM_BAR}x${NUM_CROSS} pairs x 4 combos x ${NUM_ASSETS} combos"
echo "  Expected: $((NUM_TEMPLATES * NUM_BAR * NUM_CROSS * 4 * NUM_ASSETS))"
echo "  Output: ${OUTDIR}/"
