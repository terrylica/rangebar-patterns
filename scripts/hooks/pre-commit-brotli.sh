#!/usr/bin/env bash
# Pre-commit hook: auto-compress large JSONL files with Brotli
#
# Behavior:
#   1. Scans staged .jsonl files exceeding 1MB (1,048,576 bytes)
#   2. Compresses them with brotli --quality=11 (best ratio, ~14-21x on NDJSON)
#   3. Unstages the large .jsonl, stages the .jsonl.br instead
#   4. Removes the local uncompressed .jsonl to save disk space
#   5. Prints a summary of compressed files
#
# Install: Add to .pre-commit-config.yaml as a local hook, or:
#   ln -sf ../../scripts/hooks/pre-commit-brotli.sh .git/hooks/pre-commit-brotli
#
# Requires: brotli (brew install brotli)

set -euo pipefail

MAX_SIZE=1048576  # 1MB

# Check brotli is available
if ! command -v brotli > /dev/null 2>&1; then
    echo "⚠️  brotli not found. Install with: brew install brotli"
    echo "   Skipping auto-compression of large JSONL files."
    # Don't block commit — just warn
    exit 0
fi

# Find staged .jsonl files that exceed MAX_SIZE
STAGED_JSONL=$(git diff --cached --name-only --diff-filter=ACM | grep '\.jsonl$' || true)

if [ -z "$STAGED_JSONL" ]; then
    exit 0
fi

COMPRESSED=0
while IFS= read -r f; do
    [ -f "$f" ] || continue
    size=$(wc -c < "$f" | tr -d ' ')
    if [ "$size" -gt "$MAX_SIZE" ]; then
        BR_FILE="${f}.br"
        brotli --quality=11 --force -o "$BR_FILE" "$f"
        BR_SIZE=$(wc -c < "$BR_FILE" | tr -d ' ')
        RATIO=$(echo "scale=1; $size/$BR_SIZE" | bc)

        # Unstage the large .jsonl, stage the .br instead
        git reset HEAD -- "$f" > /dev/null 2>&1 || true
        git add "$BR_FILE"

        # Remove local uncompressed file to save disk space
        rm -f "$f"

        echo "[brotli] $f ($(( size / 1024 ))KB) → $BR_FILE ($(( BR_SIZE / 1024 ))KB, ${RATIO}x) — original removed"
        COMPRESSED=$((COMPRESSED + 1))
    fi
done <<< "$STAGED_JSONL"

if [ "$COMPRESSED" -gt 0 ]; then
    echo "[brotli] Auto-compressed $COMPRESSED file(s). Originals removed. Commit proceeds with .br versions."
fi

exit 0
