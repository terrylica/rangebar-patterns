#!/usr/bin/env bash
# Copy Gen800 equity HTML from results/eval/ to results/published/ then deploy.
#
# Usage:
#   bash scripts/gen800_publish.sh                   # XRP @750 (default)
#   GEN800_SYMBOL=SOLUSDT GEN800_THRESHOLD=750 bash scripts/gen800_publish.sh
#
# Called by: mise run gen800:publish
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."

SYMBOL="${GEN800_SYMBOL:-XRPUSDT}"
THRESHOLD="${GEN800_THRESHOLD:-750}"
CONFIG_ID="${GEN800_CONFIG_ID:-atr32_up85_dn10_ao50__wl1d__bullish_only__p7_slt035_mb10}"

EVAL_DIR="$REPO_ROOT/results/eval/gen800"
PUBLISHED_DIR="$REPO_ROOT/results/published/gen800/${SYMBOL}_${THRESHOLD}"

echo "=== Gen800 Publish ==="
echo "  Config : $CONFIG_ID"
echo "  Symbol : $SYMBOL @${THRESHOLD}dbps"

# Locate the equity HTML in eval dir
# Source filename: equity_{safe_id}_{SYMBOL}_{THRESHOLD}.html
SAFE_ID="${CONFIG_ID//__/_}"
SRC_HTML="$EVAL_DIR/equity_${SAFE_ID}_${SYMBOL}_${THRESHOLD}.html"

if [ ! -f "$SRC_HTML" ]; then
    echo "ERROR: equity HTML not found: $SRC_HTML"
    echo "Run 'mise run gen800:reconstruct' first."
    exit 1
fi

# Destination strips the _SYMBOL_THRESHOLD suffix (published dir is already scoped)
DST_HTML="$PUBLISHED_DIR/equity_${SAFE_ID}.html"

mkdir -p "$PUBLISHED_DIR"
echo "  Copying: $(basename "$SRC_HTML") → published/gen800/${SYMBOL}_${THRESHOLD}/$(basename "$DST_HTML")"
cp "$SRC_HTML" "$DST_HTML"

FILE_SIZE=$(du -h "$DST_HTML" | cut -f1)
echo "  Size: $FILE_SIZE"

# Deploy to Cloudflare Workers
echo ""
bash "$SCRIPT_DIR/publish_findings.sh"
