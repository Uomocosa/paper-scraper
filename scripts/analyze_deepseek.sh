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

info "Starting analysis..."
export OPENCODE_SYSTEM_PROMPT="You are a strict data extraction assistant. Extract experimental adsorption data as CSV: POLYMER_USED,DRUG,WATER_PH,CONCENTRATION,CAPACITY,SOURCE. Output ONLY CSV rows, no extra text. If no data, respond: NO USEFUL DATA"
pixi run analyze \
    --papers_dir "OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --questions "QUESTIONS/q1.md" \
    --output_dir "opencode_go_deepseek_v4_flash_max_pdf2text_responses" \
    --ollama-opts.model "deepseek-v4-flash" \
    --ollama-opts.base-url "https://opencode.ai/zen/go/v1" \
    --ollama-opts.completion-path "/chat/completions" \
    --ollama-opts.api-key-env "OPENCODE_GO_KEY" \
    --ollama-opts.max-context-tokens 32768 \
    --max-chunks 1 \
    --handle-pdfs "pdf2text"

info ""
info "=== Done ==="
info "Responses: $LOCAL_DIR/opencode_go_deepseek_v4_flash_max_pdf2text_responses/RESPONSES/"
