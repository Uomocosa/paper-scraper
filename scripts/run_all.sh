#!/bin/bash
# Full pipeline: download → sync → analyze → sync results back.
# Each step can also be run individually (see sibling scripts).
#
# Usage:  bash scripts/run_all.sh

set -euo pipefail
source "$(dirname "$0")/config.sh"

info "=== Starting full pipeline ==="
echo ""

info "Step 1/4 — Download papers from OpenAlex..."
bash "$LOCAL_DIR/scripts/download_papers.sh"
echo ""

info "Step 2/4 — Sync PDFs to UNISI server..."
bash "$LOCAL_DIR/scripts/sync_papers.sh"
echo ""

info "Step 3/4 — Start analysis on server (screen session)..."
bash "$LOCAL_DIR/scripts/run_analysis.sh"
echo ""

info "Step 4/4 — Wait for results and sync back..."
bash "$LOCAL_DIR/scripts/sync_results.sh"
echo ""

info "=== Pipeline complete ==="
