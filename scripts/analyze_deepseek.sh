#!/bin/bash
# Analyze all papers locally using OpenCode Go -> DeepSeek V4 Flash.
# Fast, cheap, and runs on any machine with internet (no GPU needed).
#
# Prerequisites:
#   1. OpenCode Go subscription (opencode.ai/go)
#   2. OPENCODE_GO_KEY in ../.env (parent dir)
#   3. Papers already downloaded in OUTPUT_DIR/DOWNLOADED_PAPERS/
#
# Run from WSL:  bash scripts/analyze_deepseek.sh

set -euo pipefail
source "$(dirname "$0")/config.sh"

cd "$LOCAL_DIR"

info "=== DeepSeek V4 Flash Analysis via OpenCode Go ==="
info "Model: deepseek-v4-flash"
info "Papers: $LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"
info "Output: $LOCAL_DIR/opencode_go_deepseek_v4_flash_max_pdf2text_responses"
info "Env key: OPENCODE_GO_KEY"
echo ""

# Check the key is set
if ! grep -q "OPENCODE_GO_KEY" "$LOCAL_DIR/../.env" 2>/dev/null; then
    warn "OPENCODE_GO_KEY not found in ../.env"
    info "Add it:  echo 'OPENCODE_GO_KEY=gsk_your_key' >> ../.env"
    exit 1
fi

SYSTEM_PROMPT="You are a strict data extraction assistant specializing in polymer chemistry and environmental science. Your ONLY job is to extract experimental data from research papers regarding the adsorption of drugs/pollutants by polymers, hydrogels, cryogels, adsorbents, or composites in water. You must output the data in CSV format with exactly 6 columns: POLYMER_USED,DRUG,WATER_PH,CONCENTRATION,CAPACITY,SOURCE. Rules: 1. Output ONLY CSV rows, no headers, no conversational text, no markdown formatting. 2. Search figures, tables, and text thoroughly. 3. If no numerical data found, respond ONLY: NO USEFUL DATA 4. Use NaN for missing values. 5. Use scientific notation for small numbers. 6. One row per unique condition. 7. SOURCE is the paper's DOI or URL."

info "Starting analysis..."
pixi run analyze \
    --papers_dir "OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --questions "QUESTIONS/q1.md" \
    --output_dir "opencode_go_deepseek_v4_flash_max_pdf2text_responses" \
    --ollama-opts.model "deepseek-v4-flash" \
    --ollama-opts.base-url "https://opencode.ai/zen/go/v1" \
    --ollama-opts.completion-path "/chat/completions" \
    --ollama-opts.api-key-env "OPENCODE_GO_KEY" \
    --ollama-opts.max-context-tokens 32768 \
    --ollama-opts.system-prompt "$SYSTEM_PROMPT" \
    --max-chunks 1 \
    --handle-pdfs "pdf2text"

info ""
info "=== Done ==="
info "Responses: $LOCAL_DIR/opencode_go_deepseek_v4_flash_max_pdf2text_responses/RESPONSES/"
