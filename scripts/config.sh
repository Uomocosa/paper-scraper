#!/bin/bash
# Shared configuration — source this in other scripts:  source "$(dirname "$0")/config.sh"

export PATH="$PATH:/mnt/c/Users/acer/AppData/Local/pixi/bin"

# pixi is installed as pixi.exe (Windows); WSL can run it but command -v won't find it.
# This function ensures calls to `pixi` work in all scripts.
pixi() { /mnt/c/Users/acer/AppData/Local/pixi/bin/pixi.exe "$@"; }

REMOTE_USER="maggiori"
REMOTE_HOST="mec-ai"
REMOTE="$REMOTE_USER@$REMOTE_HOST"
REMOTE_REPO_DIR="~/paper-scraper"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCREEN_NAME="paper_analysis"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
