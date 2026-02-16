#!/usr/bin/env bash
set -euo pipefail

# Gen720: Walk-Forward Barrier Optimization — Multi-Formation × Multi-Asset
#
# Generates 675 SQL files: 15 templates × 15 symbols × 3 thresholds
# Each SQL has 434-barrier CROSS JOIN hardcoded via arrayJoin in the template.
# Python WFO engine handles windowing, CV, bootstrap, Vorob'ev stability.
#
# Templates: sql/gen720_wf_{FORMATION}_template.sql
# Output: /tmp/gen720_sql/{FORMATION}_{SYMBOL}_{THRESHOLD}.sql
#
# GitHub Issue: https://github.com/terrylica/rangebar-patterns/issues/28

echo "=== Gen720: Walk-Forward Barrier Optimization ==="

OUTDIR=/tmp/gen720_sql
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"

SQLDIR="$(cd "$(dirname "$0")/../../sql" && pwd)"
GIT_COMMIT=$(git -C "$(dirname "$0")/../.." rev-parse --short HEAD 2>/dev/null || echo "unknown")

# ---- Cross-Asset Alignment Constants (probed BigBlack 2026-02-15) ----
# Uses functions instead of associative arrays for bash 3 compatibility (macOS).

get_end_ts() {
    case "$1" in
        500)  echo "1770505578944" ;;
        750)  echo "1770505499361" ;;
        1000) echo "1770482794812" ;;
        *)    echo "ERROR: unknown threshold $1" >&2; exit 1 ;;
    esac
}

get_bar_count() {
    case "$1" in
        500)  echo "200000" ;;
        750)  echo "85000" ;;
        1000) echo "45000" ;;
        *)    echo "ERROR: unknown threshold $1" >&2; exit 1 ;;
    esac
}

# ---- 15 Formations (11 LONG + 2 SHORT × 2 strategies) ----
FORMATIONS=(
    udd wl1d 2down dud vwap_l hvd exh_l 3down 2down_ng exh_l_ng wl2d
    2up_ng_s exh_s 2up_ng_s_rev exh_s_rev
)

# ---- 15 Symbols ----
SYMBOLS=(
    ADAUSDT ATOMUSDT AVAXUSDT BNBUSDT BTCUSDT
    DOGEUSDT DOTUSDT ETHUSDT LINKUSDT LTCUSDT
    NEARUSDT SHIBUSDT SOLUSDT UNIUSDT XRPUSDT
)

# ---- Thresholds ----
THRESHOLDS=(500 750 1000)

echo "Formations: ${#FORMATIONS[@]}"
echo "Symbols:    ${#SYMBOLS[@]}"
echo "Thresholds: ${#THRESHOLDS[@]}"
echo "Expected:   $((${#FORMATIONS[@]} * ${#SYMBOLS[@]} * ${#THRESHOLDS[@]})) SQL files"
echo ""

# Verify all templates exist and compute SHAs
MISSING=0
TEMPLATE_SHA_LINES=""
for FMT in "${FORMATIONS[@]}"; do
    TPL="${SQLDIR}/gen720_wf_${FMT}_template.sql"
    if [ ! -f "$TPL" ]; then
        echo "ERROR: Template not found: ${TPL}"
        MISSING=$((MISSING + 1))
    else
        SHA=$(shasum -a 256 "$TPL" | cut -d' ' -f1)
        TEMPLATE_SHA_LINES="${TEMPLATE_SHA_LINES}    \"${FMT}\": \"${SHA}\""$'\n'
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo "ERROR: ${MISSING} template(s) missing. Aborting."
    exit 1
fi

# ---- Subsampling for high-density formations ----
# Prevents ClickHouse OOM when forward arrays × signal count exceeds memory.
# cityHash64(timestamp_ms) % N = 0 gives deterministic, uniform subsampling.
# @500 (200K bars): most high-density formations need subsampling.
# @750 (85K bars): only exh_l_ng (~49% density → ~42K signals) OOMs without subsampling.
# @1000 (45K bars): all formations fit in memory.
get_subsample_mod() {
    local fmt="$1" thr="$2"
    case "$thr" in
        500)
            case "$fmt" in
                exh_l_ng)              echo "16" ;;
                exh_s|exh_s_rev)       echo "8" ;;
                2down_ng)              echo "8" ;;
                exh_l|vwap_l)          echo "4" ;;
                2up_ng_s|2up_ng_s_rev) echo "4" ;;
                hvd|wl1d)              echo "2" ;;
                *)                     echo "0" ;;
            esac
            ;;
        750)
            case "$fmt" in
                exh_l_ng)              echo "8" ;;
                *)                     echo "0" ;;
            esac
            ;;
        *)  echo "0" ;;
    esac
}

TOTAL=0

for FMT in "${FORMATIONS[@]}"; do
    TPL="${SQLDIR}/gen720_wf_${FMT}_template.sql"

    for SYM in "${SYMBOLS[@]}"; do
        for THR in "${THRESHOLDS[@]}"; do
            OUTFILE="${OUTDIR}/${FMT}_${SYM}_${THR}.sql"
            END_TS=$(get_end_ts "$THR")
            BC=$(get_bar_count "$THR")

            sed \
                -e "s/__SYMBOL__/${SYM}/g" \
                -e "s/__THRESHOLD_DBPS__/${THR}/g" \
                -e "s/__END_TS_MS__/${END_TS}/g" \
                -e "s/__BAR_COUNT__/${BC}/g" \
                "$TPL" > "$OUTFILE"

            # Inject subsampling for high-density @500 formations
            MOD=$(get_subsample_mod "$FMT" "$THR")
            if [ "$MOD" != "0" ]; then
                sed -i.bak "s/AND entry_price > 0$/AND entry_price > 0\n      AND cityHash64(timestamp_ms) % ${MOD} = 0/" "$OUTFILE"
                rm -f "${OUTFILE}.bak"
            fi

            TOTAL=$((TOTAL + 1))
        done
    done
done

# Save metadata (build JSON with proper comma handling)
FORMATIONS_JSON=$(printf '"%s",' "${FORMATIONS[@]}" | sed 's/,$//')
SYMBOLS_JSON=$(printf '"%s",' "${SYMBOLS[@]}" | sed 's/,$//')
THRESHOLDS_JSON=$(printf '%s,' "${THRESHOLDS[@]}" | sed 's/,$//')

# Build template_shas JSON block
SHA_JSON=""
for FMT in "${FORMATIONS[@]}"; do
    TPL="${SQLDIR}/gen720_wf_${FMT}_template.sql"
    SHA=$(shasum -a 256 "$TPL" | cut -d' ' -f1)
    if [ -n "$SHA_JSON" ]; then
        SHA_JSON="${SHA_JSON},"$'\n'
    fi
    SHA_JSON="${SHA_JSON}    \"${FMT}\": \"${SHA}\""
done

cat > "$OUTDIR/metadata.json" << EOF
{
  "generation": 720,
  "git_commit": "${GIT_COMMIT}",
  "n_formations": ${#FORMATIONS[@]},
  "n_symbols": ${#SYMBOLS[@]},
  "n_thresholds": ${#THRESHOLDS[@]},
  "total_sql_files": ${TOTAL},
  "formations": [${FORMATIONS_JSON}],
  "symbols": [${SYMBOLS_JSON}],
  "thresholds": [${THRESHOLDS_JSON}],
  "alignment": {
    "end_ts_500": $(get_end_ts 500),
    "end_ts_750": $(get_end_ts 750),
    "end_ts_1000": $(get_end_ts 1000),
    "bar_count_500": $(get_bar_count 500),
    "bar_count_750": $(get_bar_count 750),
    "bar_count_1000": $(get_bar_count 1000)
  },
  "template_shas": {
${SHA_JSON}
  }
}
EOF

echo "=== Generated: ${TOTAL} SQL files ==="
echo "  Output: ${OUTDIR}/"
echo "  Metadata: ${OUTDIR}/metadata.json"
