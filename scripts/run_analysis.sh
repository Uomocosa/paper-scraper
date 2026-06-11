#!/bin/bash
# Step 3: Start Ollama analysis on the UNISI server in a screen session.
# The analysis runs detached — it survives SSH disconnection.
# Run this after sync_papers.sh.
#
# Monitor progress:  bash scripts/sync_results.sh --status
# Reattach to screen: ssh maggiori@mec-ai 'screen -r paper_analysis'

set -euo pipefail
source "$(dirname "$0")/config.sh"

# Write the runner script to the server
info "Writing runner script to server..."
ssh "$REMOTE" "cat > /tmp/run_paper_analysis.sh" << 'REMOTE_SCRIPT'
#!/bin/bash
set -euo pipefail

cd ~/paper-scraper

echo ">>> Pulling latest code from GitHub..."
git pull

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

echo ">>> Analysis complete!"
REMOTE_SCRIPT

# Start in screen
ssh "$REMOTE" "chmod +x /tmp/run_paper_analysis.sh && screen -dmS $SCREEN_NAME /tmp/run_paper_analysis.sh"

info "Analysis started in screen session '$SCREEN_NAME' on $REMOTE_HOST."
info ""
info "  Check status:    bash scripts/sync_results.sh --status"
info "  Monitor live:    ssh $REMOTE 'screen -r $SCREEN_NAME'"
info "  Detach from it:  Ctrl+A, then D"
info "  Kill if stuck:   ssh $REMOTE 'screen -XS $SCREEN_NAME quit'"
info ""
info "When it's done, run:  bash scripts/sync_results.sh"
