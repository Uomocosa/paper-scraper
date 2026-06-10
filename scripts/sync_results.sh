#!/bin/bash
# Step 4: Wait for analysis to finish, then sync results back from server.
# If --status is passed, just check if the screen session is still running.
#
# Usage:
#   bash scripts/sync_results.sh          # wait + sync
#   bash scripts/sync_results.sh --status # just check if running

set -euo pipefail
source "$(dirname "$0")/config.sh"

check_running() {
    if ssh "$REMOTE" "screen -list 2>/dev/null | grep -q $SCREEN_NAME"; then
        info "Analysis still running on $REMOTE_HOST (screen: $SCREEN_NAME)"
        return 0
    else
        info "Analysis is not running on $REMOTE_HOST"
        return 1
    fi
}

if [ "${1:-}" = "--status" ]; then
    check_running && exit 0 || exit 1
fi

# Wait for completion
info "Waiting for analysis to finish on $REMOTE_HOST..."
while check_running; do
    sleep 30
done

info "Analysis finished! Syncing results back to local PC..."

OUTPUTS=("gemma4_26b-pdf2text-respones" "gemma4_26b-pdf2image-respones")
for dir in "${OUTPUTS[@]}"; do
    info "  Syncing $dir..."
    rsync -avz --progress "$REMOTE:$REMOTE_REPO_DIR/$dir/" "$LOCAL_DIR/$dir/"
done

info "=== All done! ==="
info "Results:"
for dir in "${OUTPUTS[@]}"; do
    count=$(find "$LOCAL_DIR/$dir/RESPONSES" -name "*.md" 2>/dev/null | wc -l)
    info "  $dir/  ($count response files)"
done
