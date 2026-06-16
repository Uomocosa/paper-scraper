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
#   3. Re-analyze with a chosen model (REQUIRED):
#      bash scripts/reanalyze_papers.sh mimo-v2.5              # MiMo V2.5 (cheapest)
#      bash scripts/reanalyze_papers.sh kimi-k2.7              # Kimi K2.7 (good quality)
#      bash scripts/reanalyze_papers.sh deepseek-v4-pro        # DeepSeek V4 Pro
#
#   Pricing (per 1M tokens / per paper est.):
#     MiMo V2.5          $0.14/$0.33K  → ~$0.01/paper  (30 papers: $0.30)
#     MiniMax M3         $0.30/$1.20   → ~$0.02/paper  (30 papers: $0.60)
#     DeepSeek V4 Flash  $0.14/$0.28   → ~$0.01/paper  (30 papers: $0.30)
#     Kimi K2.6          $0.95/$4.00   → ~$0.06/paper  (30 papers: $1.80)
#     Kimi K2.7 Code     $0.95/$4.00   → ~$0.06/paper  (30 papers: $1.80)
#     DeepSeek V4 Pro    $1.74/$3.48   → ~$0.10/paper  (30 papers: $3.00)
#     Qwen3.7 Plus       $0.40/$1.60   → ~$0.03/paper  (30 papers: $0.90)
#     GLM-5              $1.00/$3.20   → ~$0.06/paper  (30 papers: $1.80)
#     MiMo V2.5 Pro      $1.74/$3.48   → ~$0.10/paper  (30 papers: $3.00)

set -euo pipefail
source "$(dirname "$0")/config.sh"

# Config - MODEL is required (no default)
if [ $# -lt 1 ]; then
    echo "ERROR: Model name is required."
    echo "Usage: bash scripts/reanalyze_papers.sh <model> [papers.csv]"
    echo ""
    echo "Available Go models: mimo-v2.5, kimi-k2.7, deepseek-v4-pro, deepseek-v4-flash, qwen3.7-plus, glm-5, minimax-m3"
    echo "Pricing: https://opencode.ai/docs/go"
    exit 1
fi

MODEL="$1"
INPUT_CSV="${2:-$LOCAL_DIR/papers_for_review.csv}"
PAPERS_SRC="$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"
OUTPUT_DIR_NAME="gemma_review_${MODEL//./_}"
OUTPUT_DIR="$LOCAL_DIR/$OUTPUT_DIR_NAME"
TEMP_DIR="$LOCAL_DIR/.tmp_review_papers"
TEMP_DIR_RELATIVE=".tmp_review_papers"

if [ ! -f "$INPUT_CSV" ]; then
    echo "ERROR: Paper list not found: $INPUT_CSV"
    echo "Generate it first: pixi run python scripts/list_good_papers.py --csv"
    exit 1
fi

# Read paper names from CSV (skip header)
PAPERS=()
skip_header=1
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and header
    [ -z "$line" ] && continue
    if [ "$skip_header" -eq 1 ]; then
        skip_header=0
        continue
    fi
    PAPERS+=("$line")
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
    paper="$(echo "$paper" | sed 's/[[:space:]]*$//')"
    # Try to find the PDF by prefix match
    found=$(ls "$PAPERS_SRC"/"$paper"*.pdf 2>/dev/null | head -1 || true)
    if [ -z "$found" ]; then
        # Fallback: try partial match with find
        found=$(find "$PAPERS_SRC" -maxdepth 1 -name "${paper}*.pdf" 2>/dev/null | head -1 || true)
    fi
    if [ -n "$found" ]; then
        cp "$found" "$TEMP_DIR/"
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
    --papers_dir "$TEMP_DIR_RELATIVE" \
    --questions "QUESTIONS/q1.md" \
    --output_dir "$OUTPUT_DIR_NAME" \
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
echo "Results: $OUTPUT_DIR_NAME/RESPONSES/"
echo "Compare: pixi run python scripts/compare_models.py --new $OUTPUT_DIR_NAME"
