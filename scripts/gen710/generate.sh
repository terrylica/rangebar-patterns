#!/usr/bin/env bash
set -euo pipefail

# Gen710: Time-Decay Barrier Sweep — SL Tightening Based on Holding Period
# Copied from: scripts/gen610/generate.sh
#
# Fixed config: Universal champion (turnover_imbalance < p25 AND price_impact < p25)
# Fixed asset: SOLUSDT @500dbps
# Fixed TP: 0.25x, Fixed SL_wide: 0.50x (from Gen510 optimal)
# Grid: 4 phase1_bars × 3 sl_tight × 4 max_bars = 48 barrier combos
# Total: 48 SQL files
#
# Template: sql/gen710_time_decay_template.sql
# GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/27

echo "=== Gen710: Time-Decay Barrier Sweep ==="

OUTDIR=/tmp/gen710_sql
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

SQLDIR="$(cd "$(dirname "$0")/../../sql" && pwd)"
TEMPLATE="${SQLDIR}/gen710_time_decay_template.sql"

if [ ! -f "$TEMPLATE" ]; then
    echo "ERROR: Template not found: ${TEMPLATE}"
    exit 1
fi

TEMPLATE_SHA=$(shasum -a 256 "$TEMPLATE" | cut -d' ' -f1)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# ---- Fixed Configuration (Universal Champion) ----
SYMBOL="SOLUSDT"
THRESHOLD="500"
F1="turnover_imbalance"
Q1="0.25"
D1="<"
F2="price_impact"
Q2="0.25"
D2="<"
TP_MULT="0.25"
SL_WIDE="0.50"
FC="2down__turnover_imbalance_lt_p25__price_impact_lt_p25"

# ---- Time-Decay Barrier Grid (48 combos) ----
# Format: PHASE1_BARS|SL_TIGHT|MAX_BARS
BARRIERS=()
for P1 in 3 5 7 10; do
    for SLT in 0.25 0.10 0.00; do
        for MB in 20 30 50 100; do
            BARRIERS+=("${P1}|${SLT}|${MB}")
        done
    done
done

NUM_BARRIERS=${#BARRIERS[@]}

echo "Config: ${FC}"
echo "Asset: ${SYMBOL}@${THRESHOLD}"
echo "TP: ${TP_MULT}x  SL_wide: ${SL_WIDE}x"
echo "Barrier combos: ${NUM_BARRIERS}"
echo ""

TOTAL=0

for barrier in "${BARRIERS[@]}"; do
    IFS='|' read -r P1 SLT MB <<< "$barrier"

    # Barrier ID: p5_slt010_mb50 format
    SLT_ID=$(echo "$SLT" | tr -d '.')
    BARRIER_ID="p${P1}_slt${SLT_ID}_mb${MB}"

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
        -e "s/__TP_MULT__/${TP_MULT}/g" \
        -e "s/__SL_WIDE__/${SL_WIDE}/g" \
        -e "s/__SL_TIGHT__/${SLT}/g" \
        -e "s/__PHASE1_BARS__/${P1}/g" \
        -e "s/__MAX_BARS__/${MB}/g" \
        -e "s/__BARRIER_ID__/${BARRIER_ID}/g" \
        "$TEMPLATE" > "${OUTDIR}/${FC}__${BARRIER_ID}.sql"

    TOTAL=$((TOTAL + 1))
done

# Save metadata
cat > "$OUTDIR/metadata.json" << EOF
{"generation":710,"git_commit":"${GIT_COMMIT}","template_sha":"${TEMPLATE_SHA}","config":"${FC}","symbol":"${SYMBOL}","threshold_dbps":${THRESHOLD},"tp_mult":${TP_MULT},"sl_wide":${SL_WIDE},"total_sql_files":${TOTAL}}
EOF

echo "=== Total: ${TOTAL} SQL files ==="
echo "  Output: ${OUTDIR}/"
