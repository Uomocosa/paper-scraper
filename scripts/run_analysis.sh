#!/bin/bash
# Step 3: Start Ollama analysis on the UNISI server in a screen session.
# The analysis runs detached — it survives SSH disconnection.
# Run this after sync_papers.sh.
#
# All output is logged to /tmp/paper_analysis.log on the server.
# Check it:  bash scripts/check_analysis.sh
# Monitor:   ssh maggiori@mec-ai 'screen -r paper_analysis'

set -euo pipefail
source "$(dirname "$0")/config.sh"

REMOTE_SCRIPT="$REMOTE_REPO_DIR/scripts/remote_analysis.sh"

info "Starting remote analysis script on server..."
ssh "$REMOTE" "chmod +x $REMOTE_SCRIPT && screen -dmS $SCREEN_NAME $REMOTE_SCRIPT"

info "Analysis started in screen session '$SCREEN_NAME' on $REMOTE_HOST."
info ""
info "  Check status:    bash scripts/sync_results.sh --status"
info "  See full log:    bash scripts/check_analysis.sh"
info "  Monitor live:    ssh $REMOTE 'screen -r $SCREEN_NAME'"
info "  Detach from it:  Ctrl+A, then D"
info "  Kill if stuck:   ssh $REMOTE 'screen -XS $SCREEN_NAME quit'"
info ""
info "When it's done, run:  bash scripts/sync_results.sh"
