#!/bin/bash
# This script is superseded by the modular scripts in this directory.
# Use one of the following instead:
#
#   bash scripts/run_all.sh              # full pipeline (1→2→3→4)
#   bash scripts/download_papers.sh      # step 1 — download from OpenAlex
#   bash scripts/sync_papers.sh          # step 2 — sync PDFs to server
#   bash scripts/run_analysis.sh         # step 3 — start analysis on server
#   bash scripts/sync_results.sh         # step 4 — fetch results
#   bash scripts/sync_results.sh --status  # check if analysis is still running
