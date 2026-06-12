#!/bin/bash
# Fast local test: analyze a few random papers to catch bugs.
# Requires Ollama running locally (tinyllama is fast on CPU).
#
# Usage:  bash scripts/test_analyze.sh          # test 5 random papers
#         bash scripts/test_analyze.sh 10        # test 10 random papers

set -euo pipefail
source "$(dirname "$0")/config.sh"

COUNT="${1:-5}"
TEMP_DIR="$LOCAL_DIR/test_analyze_temp"
PAPERS_SRC="$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"

# Check if we have papers
if [ ! -d "$PAPERS_SRC" ] || [ -z "$(ls "$PAPERS_SRC"/*.pdf 2>/dev/null)" ]; then
    echo "No PDFs found in $PAPERS_SRC"
    echo "Run download_papers.sh first."
    exit 1
fi

# Clean and prepare temp dir
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Pick random papers
echo "=== Picking $COUNT random papers ==="
ls "$PAPERS_SRC"/*.pdf | shuf -n "$COUNT" | while read f; do
    cp "$f" "$TEMP_DIR/"
    echo "  $(basename "$f")"
done

echo ""
echo "=== Running analyze on $COUNT papers (model: tinyllama, 1 chunk) ==="
cd "$LOCAL_DIR"
pixi run analyze \
    --papers_dir "$TEMP_DIR" \
    --questions "Does this paper contain experimental adsorption data (pH, concentration, capacity)? Answer YES or NO." \
    --ollama-opts.model "tinyllama" \
    --ollama-opts.max-context-tokens 2048 \
    --max-chunks 1

echo ""
echo "=== Results ==="
for d in "$TEMP_DIR/RESPONSES"/*/; do
    paper="$(basename "$d")"
    if [ -f "$d/q1.md" ]; then
        answer="$(head -5 "$d/q1.md" | tail -1)"
        echo "  $paper: $answer"
    else
        echo "  $paper: NO RESPONSE"
    fi
done

echo ""
echo "=== Done. Temp dir: $TEMP_DIR ==="
echo "Run 'rm -rf $TEMP_DIR' to clean up."
