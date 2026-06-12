#!/bin/bash
# Check the remote analysis log on the UNISI server.
# Shows the full output of the last run so you can see what happened.
#
# Usage:
#   bash scripts/check_analysis.sh          # show last 100 lines
#   bash scripts/check_analysis.sh --full   # show entire log
#   bash scripts/check_analysis.sh --tail N # show last N lines

set -euo pipefail
source "$(dirname "$0")/config.sh"

if [ "${1:-}" = "--full" ]; then
    ssh "$REMOTE" "cat /tmp/paper_analysis.log"
elif [ "${1:-}" = "--tail" ]; then
    n="${2:-50}"
    ssh "$REMOTE" "tail -$n /tmp/paper_analysis.log"
else
    echo "=== Last 50 lines of /tmp/paper_analysis.log on $REMOTE_HOST ==="
    ssh "$REMOTE" "tail -50 /tmp/paper_analysis.log"
    echo ""
    echo "Full log:  bash scripts/check_analysis.sh --full"
    echo "Tail N:    bash scripts/check_analysis.sh --tail 100"
fi
