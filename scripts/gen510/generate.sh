#!/usr/bin/env bash
set -euo pipefail

echo "=== Gen510: Barrier Grid on Top Gen400 2-Feature Winners ==="

OUTDIR=/tmp/gen510_sql
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

TEMPLATE="sql/gen510_barrier_grid_2f_template.sql"
TEMPLATE_SHA=$(shasum -a 256 "$TEMPLATE" | cut -d' ' -f1)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Top 5 Gen400 2-feature winners (from logs/gen400/report_2026-02-07.txt)
# These are the configs with highest Kelly and >=200 signals
WINNERS=(
    "aggression_ratio|gt_p50|0.50|>|duration_us|lt_p50|0.50|<"
    "turnover_imbalance|gt_p50|0.50|>|aggregation_density|gt_p50|0.50|>"
    "ofi|gt_p50|0.50|>|aggregation_density|gt_p50|0.50|>"
    "aggression_ratio|gt_p50|0.50|>|aggregation_density|gt_p50|0.50|>"
    "turnover_imbalance|gt_p50|0.50|>|duration_us|lt_p50|0.50|<"
)

COUNT=0
for winner in "${WINNERS[@]}"; do
    IFS='|' read -r F1 S1 Q1 D1 F2 S2 Q2 D2 <<< "$winner"
    CONFIG_ID="${F1}_${S1}__${F2}_${S2}"

    sed \
        -e "s/__FEATURE_COL_1__/${F1}/g" \
        -e "s/__FEATURE_COL_2__/${F2}/g" \
        -e "s/__QUANTILE_PCT_1__/${Q1}/g" \
        -e "s/__QUANTILE_PCT_2__/${Q2}/g" \
        -e "s/__DIRECTION_1__/${D1}/g" \
        -e "s/__DIRECTION_2__/${D2}/g" \
        -e "s/__CONFIG_ID__/${CONFIG_ID}/g" \
        "$TEMPLATE" > "$OUTDIR/${CONFIG_ID}.sql"

    COUNT=$((COUNT + 1))
    echo "  ${CONFIG_ID}"
done

cat > "$OUTDIR/metadata.json" <<EOF
{"template_sha":"${TEMPLATE_SHA}","git_commit":"${GIT_COMMIT}","template_file":"${TEMPLATE}"}
EOF

echo ""
echo "=== Generated: ${COUNT} SQL files × 36 barrier combos each = $((COUNT * 36)) total result rows ==="
echo "  Output: ${OUTDIR}/"
