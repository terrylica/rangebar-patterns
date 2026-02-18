#!/usr/bin/env bash
set -euo pipefail
# Deploy results/published/ to Cloudflare Workers (static assets).
# Reads credentials from 1Password Claude Automation vault.
# Usage: bash scripts/publish_findings.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLISH_DIR="$SCRIPT_DIR/../results/published"
OP_ITEM_ID="ewtid322w2bozkzqfg4my2kd5m"

echo "=== Publish Findings to Cloudflare Workers ==="

# 1. Fetch credentials from 1Password
echo "Fetching Cloudflare credentials from 1Password..."
CLOUDFLARE_ACCOUNT_ID=$(OP_SERVICE_ACCOUNT_TOKEN="$(cat ~/.claude/.secrets/op-service-account-token)" \
  op item get "$OP_ITEM_ID" --vault "Claude Automation" --fields "account_id")
export CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN=$(OP_SERVICE_ACCOUNT_TOKEN="$(cat ~/.claude/.secrets/op-service-account-token)" \
  op item get "$OP_ITEM_ID" --vault "Claude Automation" --fields "credential" --reveal)
export CLOUDFLARE_API_TOKEN

echo "  Account ID: ${CLOUDFLARE_ACCOUNT_ID:0:8}..."
echo "  Token: ${CLOUDFLARE_API_TOKEN:0:8}..."

# 2. Auto-generate index.html from published HTML files
echo "Generating index.html..."
INDEX="$PUBLISH_DIR/index.html"

cat > "$INDEX" << 'HEADER'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Range Bar Patterns — Published Findings</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }
    h1 { border-bottom: 2px solid #0066cc; padding-bottom: 8px; }
    h2 { color: #555; margin-top: 32px; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .file-list { list-style: none; padding: 0; }
    .file-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    .file-list li:last-child { border-bottom: none; }
    .meta { color: #888; font-size: 0.85em; margin-left: 12px; }
    footer { margin-top: 40px; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 12px; }
  </style>
</head>
<body>
  <h1>Range Bar Patterns — Published Findings</h1>
  <p>Interactive Bokeh HTML equity curves from backtesting.py reconstruction.</p>
HEADER

# Find all HTML files under gen*/ directories (not index.html itself)
cd "$PUBLISH_DIR"
FOUND=0
CURRENT_GEN=""

# Sort by gen/symbol/threshold for grouping
while IFS= read -r html_file; do
  [ -z "$html_file" ] && continue
  FOUND=$((FOUND + 1))

  # Extract generation (gen800), symbol, threshold from path
  gen_dir=$(echo "$html_file" | cut -d'/' -f1)
  sym_thr=$(echo "$html_file" | cut -d'/' -f2)

  # Start new section for each generation
  if [ "$gen_dir" != "$CURRENT_GEN" ]; then
    CURRENT_GEN="$gen_dir"
    gen_upper=$(echo "$gen_dir" | tr '[:lower:]' '[:upper:]')
    echo "  <h2>$gen_upper</h2>" >> "$INDEX"
    echo "  <ul class=\"file-list\">" >> "$INDEX"
  fi

  # File size
  fsize=$(du -h "$html_file" | cut -f1 | tr -d ' ')
  fname=$(basename "$html_file" .html)

  echo "  <li><a href=\"$html_file\">$sym_thr / $fname</a> <span class=\"meta\">($fsize)</span></li>" >> "$INDEX"

done < <(find . -path './gen*/*.html' -type f | sed 's|^\./||' | sort)

# Close the last list if any files found
if [ "$FOUND" -gt 0 ] && [ -n "$CURRENT_GEN" ]; then
  echo "  </ul>" >> "$INDEX"
fi

if [ "$FOUND" -eq 0 ]; then
  echo "  <p><em>No published findings yet.</em></p>" >> "$INDEX"
fi

# Footer with timestamp
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
cat >> "$INDEX" << FOOTER
  <footer>
    Published: $TIMESTAMP | $FOUND charts |
    <a href="https://github.com/terrylica/rangebar-patterns">GitHub</a>
  </footer>
</body>
</html>
FOOTER

echo "  Generated index.html ($FOUND charts)"

# 3. Deploy via wrangler
echo "Deploying to Cloudflare Workers..."
cd "$PUBLISH_DIR"
npx wrangler deploy 2>&1

echo ""
echo "=== Deploy complete ==="
echo "URL: https://rangebar-findings.terry-301.workers.dev/"
