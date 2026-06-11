#!/bin/bash
# Step 1: Download papers from OpenAlex via multiple targeted searches.
# Run this on your LOCAL PC (requires pixi, OpenAlex API key).
#
# Each run targets a specific angle on polymer+pharmaceutical adsorption.
# Already-downloaded papers are re-downloaded (fast, just overwrites).
# Run from WSL:  bash scripts/download_papers.sh

set -euo pipefail
source "$(dirname "$0")/config.sh"

TOPIC="T10016"
MAX=1000
cd "$LOCAL_DIR"

run_search() {
    local label="$1"
    local keywords="$2"
    info "=== Run: $label ==="
    pixi run scrape \
        --search-filter.topics "$TOPIC" \
        --search-filter.keywords "$keywords" \
        --search-filter.max-papers "$MAX" \
        --questions None
}

run_search "Pharmaceutical + adsorption + polymer"  "pharmaceutical && adsorption && polymer"
run_search "Antibiotic + adsorption + polymer"      "antibiotic && adsorption && polymer"
run_search "Drug removal + hydrogel"                "drug && removal && hydrogel"
run_search "Dye + adsorption + polymer + isotherm"  "dye && adsorption && polymer && isotherm"
run_search "Heavy metal + adsorption + polymer"      "heavy && metal && adsorption && polymer"

info "Done. Papers saved to $LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"
