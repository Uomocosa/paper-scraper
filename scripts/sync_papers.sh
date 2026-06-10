#!/bin/bash
# Step 2: Sync downloaded PDFs to the UNISI server.
# Run this after download_papers.sh (or alone to re-sync).

set -euo pipefail
source "$(dirname "$0")/config.sh"

PDFS_LOCAL="$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"
PDFS_REMOTE="$REMOTE:$REMOTE_REPO_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"

info "Syncing PDFs to UNISI server..."
info "  From: $PDFS_LOCAL"
info "  To:   $PDFS_REMOTE"
rsync -avz --progress "$PDFS_LOCAL" "$PDFS_REMOTE"

info "Sync complete."
