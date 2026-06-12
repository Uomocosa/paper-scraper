#!/bin/bash
# This script runs on the UNISI server (pushed via sync_papers.sh).
# It pulls latest code, installs deps, and runs Ollama analysis.
# All output is logged to /tmp/paper_analysis.log.

set -euo pipefail

exec > /tmp/paper_analysis.log 2>&1

echo "=== PAPER ANALYSIS STARTED $(date) ==="

cd ~/paper-scraper

echo ">>> Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

if ! command -v pixi &>/dev/null; then
    echo ">>> Installing pixi..."
    curl -fsSL https://pixi.sh/install.sh | sh
fi
export PATH="$HOME/.pixi/bin:$PATH"

echo ">>> Installing Python dependencies..."
pixi install

echo ">>> Running pdf2text analysis..."
pixi run analyze \
    --questions "$HOME/paper-scraper/QUESTIONS" \
    --papers_dir "$HOME/paper-scraper/OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --output_dir "$HOME/paper-scraper/gemma4_26b-pdf2text-respones" \
    --ollama-opts.model "gemma4:26b" \
    --handle-pdfs "pdf2text"

echo ">>> Running pdf2image analysis..."
pixi run analyze \
    --questions "$HOME/paper-scraper/QUESTIONS" \
    --papers_dir "$HOME/paper-scraper/OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --output_dir "$HOME/paper-scraper/gemma4_26b-pdf2image-respones" \
    --ollama-opts.model "gemma4:26b" \
    --handle-pdfs "pdf2image"

echo "=== PAPER ANALYSIS COMPLETE $(date) ==="
