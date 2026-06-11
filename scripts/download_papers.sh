#!/bin/bash
# Step 1: Download papers from OpenAlex via targeted searches.
# Run this on your LOCAL PC (requires pixi, OpenAlex API key).
#
# Each run targets a specific data-bearing paper type.
# Keywords include isotherm/capacity/mg_g to filter for papers
# that likely contain experimental adsorption data tables.
# Run from WSL:  bash scripts/download_papers.sh

set -euo pipefail
source "$(dirname "$0")/config.sh"

TOPIC="T10016"
MAX=2000
cd "$LOCAL_DIR"

run_search() {
    local label="$1"
    local keywords="$2"
    info "=== Run: $label ==="
    pixi run scrape \
        --search-filter.topics "$TOPIC" \
        --search-filter.keywords "$keywords" \
        --search-filter.max-papers "$MAX" \
        --search-filter.open-access-only True \
        --no-extract-refs-from-seed \
        --questions None
}

# Core: pharma + polymer + adsorption with experimental data signals
run_search "Pharma + polymer + isotherm + capacity"    "pharmaceutical AND adsorption AND polymer AND isotherm AND capacity"
run_search "Antibiotic + polymer + isotherm + capacity" "antibiotic AND adsorption AND polymer AND isotherm AND capacity"
run_search "Drug + hydrogel + kinetic + capacity"       "drug AND adsorption AND hydrogel AND kinetic AND capacity"
run_search "Pharma + polymer + Langmuir + capacity"     "pharmaceutical AND adsorption AND polymer AND Langmuir AND capacity"
run_search "Antibiotic + polymer + kinetic + capacity"  "antibiotic AND adsorption AND polymer AND kinetic AND capacity"
run_search "Dye + polymer + isotherm + capacity"        "dye AND adsorption AND polymer AND isotherm AND capacity"

info "Done. Papers saved to $LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"
