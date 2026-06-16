#!/bin/bash
# Re-analyze selected papers with a different AI model via OpenCode Go.
#
# Usage:
#   1. Generate paper list:
#      pixi run python scripts/list_good_papers.py --csv
#      pixi run python scripts/list_good_papers.py --csv --all
#
#   2. Edit papers_for_review.csv, keep only papers you want.
#
#   3. Re-analyze with a different model:
#      bash scripts/reanalyze_papers.sh                    # uses MiMo V2.5 (cheapest)
#      bash scripts/reanalyze_papers.sh kimi-k2.7          # use Kimi K2.7
#      bash scripts/reanalyze_papers.sh deepseek-v4-pro    # use DeepSeek V4 Pro
#      bash scripts/reanalyze_papers.sh mimo-v2.5 mylist.csv   # custom model + file

set -euo pipefail
source "$(dirname "$0")/config.sh"

# Config
MODEL="${1:-mimo-v2.5}"
INPUT_CSV="${2:-$LOCAL_DIR/papers_for_review.csv}"
PAPERS_SRC="$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"
OUTPUT_DIR="$LOCAL_DIR/gemma_review_${MODEL//./_}"
TEMP_DIR="$LOCAL_DIR/.tmp_review_papers"

if [ ! -f "$INPUT_CSV" ]; then
    echo "ERROR: Paper list not found: $INPUT_CSV"
    echo "Generate it first: pixi run python scripts/list_good_papers.py --csv"
    exit 1
fi

# Read paper names from CSV (skip header)
PAPERS=()
while IFS=, read -r name; do
    if [ "$name" != "PAPER" ] && [ -n "$name" ]; then
        PAPERS+=("$name")
    fi
done < "$INPUT_CSV"

if [ ${#PAPERS[@]} -eq 0 ]; then
    echo "ERROR: No papers found in $INPUT_CSV"
    exit 1
fi

echo "=== Re-analyzing ${#PAPERS[@]} papers with model: $MODEL ==="
echo ""

# Copy selected papers to temp dir
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

copied=0
not_found=0
for paper in "${PAPERS[@]}"; do
    # Try to find the PDF (exact match or partial match)
    found=$(ls "$PAPERS_SRC" 2>/dev/null | grep -i "$(echo "$paper" | sed 's/[][(){}*?$^|]/\\&/g')" | head -1 || true)
    if [ -n "$found" ]; then
        cp "$PAPERS_SRC/$found" "$TEMP_DIR/"
        copied=$((copied + 1))
    else
        echo "  NOT FOUND: $paper"
        not_found=$((not_found + 1))
    fi
done

if [ "$copied" -eq 0 ]; then
    echo "ERROR: No papers could be found in $PAPERS_SRC"
    exit 1
fi

echo "Copied $copied papers to temp dir ($not_found not found)"
echo ""

# Run analysis with the chosen model
echo "Running analysis with model: $MODEL"
cd "$LOCAL_DIR"
pixi run analyze \
    --papers_dir "$TEMP_DIR" \
    --questions "QUESTIONS/q1.md" \
    --output_dir "$OUTPUT_DIR" \
    --ollama-opts.model "$MODEL" \
    --ollama-opts.base-url "https://opencode.ai/zen/go/v1" \
    --ollama-opts.completion-path "/chat/completions" \
    --ollama-opts.api-key-env "OPENCODE_GO_KEY" \
    --ollama-opts.system-prompt "Extract adsorption data as CSV: POLYMER_USED,DRUG,WATER_PH,CONCENTRATION,CAPACITY,SOURCE. No header row. No units in numbers. NaN for missing. Only values explicitly in the text. If no data: NO USEFUL DATA" \
    --ollama-opts.max-context-tokens 32768 \
    --max-chunks 1 \
    --handle-pdfs "pdf2text"

# Cleanup temp
rm -rf "$TEMP_DIR"

echo ""
echo "=== Done ==="
echo "Results: $OUTPUT_DIR/RESPONSES/"
echo "Compare: pixi run python scripts/compare_models.py --new $OUTPUT_DIR"
