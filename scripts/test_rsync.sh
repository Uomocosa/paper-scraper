#!/bin/bash
# Quick test: sends an empty example.md to UNISI server and back.
# Run this first to verify OpenVPN + SSH + rsync all work.

set -euo pipefail

REMOTE_USER="maggiori"
REMOTE_HOST="mec-ai"
REMOTE="$REMOTE_USER@$REMOTE_HOST"
REMOTE_DIR="/tmp"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create a tiny test file
TEST_FILE="$LOCAL_DIR/scripts/__rsync_test__.md"
echo "rsync test: $(date)" > "$TEST_FILE"

info "1/3: Sending test file TO server..."
rsync -avz "$TEST_FILE" "$REMOTE:$REMOTE_DIR/__rsync_test__.md"

info "2/3: Fetching test file BACK from server..."
rsync -avz "$REMOTE:$REMOTE_DIR/__rsync_test__.md" "$LOCAL_DIR/scripts/__rsync_test__back__.md"

# Cleanup remote
ssh "$REMOTE" "rm -f $REMOTE_DIR/__rsync_test__.md"
rm -f "$TEST_FILE"

# Verify the round-trip
if [ -f "$LOCAL_DIR/scripts/__rsync_test__back__.md" ]; then
    info "3/3: SUCCESS — rsync round-trip works!"
    cat "$LOCAL_DIR/scripts/__rsync_test__back__.md"
    rm -f "$LOCAL_DIR/scripts/__rsync_test__back__.md"
else
    error "FAILED — file not found after round-trip"
    exit 1
fi
