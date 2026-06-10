#!/bin/bash
# Step 1: Download up to 1000 papers from OpenAlex via the pipeline.
# Run this on your LOCAL PC (requires pixi, OpenAlex API key, OpenVPN to UNISI).

set -euo pipefail
source "$(dirname "$0")/config.sh"

info "Downloading up to 1000 papers from OpenAlex..."
cd "$LOCAL_DIR"
pixi run scrape \
    --search-filter.topics "T10016 || T11781 || T14252" \
    --search-filter.keywords "poly || polymer || polymers || adsorption || pollutant || hydrogel || adsorbent || wastewater" \
    --search-filter.max-papers 1000 \
    --questions None

info "Done. Papers saved to $LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS/"
