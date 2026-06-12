#!/bin/bash
# Step 2: Sync downloaded PDFs to the UNISI server.
# Run this after download_papers.sh (or alone to re-sync).

set -euo pipefail
source "$(dirname "$0")/config.sh"

SCRIPT_LOCAL="$LOCAL_DIR/scripts/remote_analysis.sh"
SCRIPT_REMOTE="$REMOTE:$REMOTE_REPO_DIR/scripts/remote_analysis.sh"
QUESTIONS_LOCAL="$LOCAL_DIR/QUESTIONS/"
QUESTIONS_REMOTE="$REMOTE:$REMOTE_REPO_DIR/QUESTIONS/"
PDFS_LOCAL="$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"
PDFS_REMOTE="$REMOTE:$REMOTE_REPO_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"

info "Syncing remote analysis script..."
rsync -avz "$SCRIPT_LOCAL" "$SCRIPT_REMOTE"

info "Syncing questions to UNISI server..."
info "  From: $QUESTIONS_LOCAL"
info "  To:   $QUESTIONS_REMOTE"
rsync -avz --progress "$QUESTIONS_LOCAL" "$QUESTIONS_REMOTE"

info "Syncing PDFs to UNISI server..."
info "  From: $PDFS_LOCAL"
info "  To:   $PDFS_REMOTE"
rsync -avz --progress "$PDFS_LOCAL" "$PDFS_REMOTE"

info "Sync complete."
