#!/bin/bash
# Fast remote test: analyze N random papers on the UNISI server.
# Use this to iterate quickly: fix a bug, run this, check results.
#
# Usage:  bash scripts/test_remote.sh            # test 5 random papers
#         bash scripts/test_remote.sh 10          # test 10 random papers
#         bash scripts/test_remote.sh 5 image     # pdf2image mode

set -euo pipefail
source "$(dirname "$0")/config.sh"

COUNT="${1:-5}"
MODE="${2:-text}"
OUTPUT_DIR="gemma4_test_${MODE}"
REMOTE_TEST_DIR="/tmp/test_papers_$$"
LOCAL_TEST_DIR="$LOCAL_DIR/test_remote_temp"

info "=== Remote test: $COUNT random papers ($MODE mode) ==="

# Pick random papers locally
mkdir -p "$LOCAL_TEST_DIR"
ls "$LOCAL_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"/*.pdf 2>/dev/null | shuf -n "$COUNT" | while read f; do
    cp "$f" "$LOCAL_TEST_DIR/"
    echo "  $(basename "$f")"
done

# Rsync test papers + analysis script to server
info "Uploading $COUNT papers to $REMOTE:$REMOTE_TEST_DIR"
rsync -avz "$LOCAL_TEST_DIR/" "$REMOTE:$REMOTE_TEST_DIR/"
rm -rf "$LOCAL_TEST_DIR"
rsync -avz "$LOCAL_DIR/scripts/remote_analysis.sh" "$REMOTE:/tmp/remote_analysis.sh"

# Write the test runner script locally, then rsync to server
mkdir -p "$LOCAL_DIR/.tmp"
cat > "$LOCAL_DIR/.tmp/run_test.sh" << TESTSCRIPT
#!/bin/bash
set -euo pipefail
exec > /tmp/test_analysis.log 2>&1
echo '=== TEST STARTED $(date) ==='
cd ~/paper-scraper
echo '>>> Pulling latest code...'
git fetch origin
git reset --hard origin/main
echo '>>> Installing deps...'
pixi install
echo '>>> Running analyze on $COUNT papers ($MODE mode)...'
pixi run analyze \
    --questions "\$HOME/paper-scraper/QUESTIONS" \
    --papers_dir "$REMOTE_TEST_DIR" \
    --output_dir "\$HOME/paper-scraper/$OUTPUT_DIR" \
    --ollama-opts.model "gemma4:26b" \
    --max-chunks 1 \
    --handle-pdfs "pdf2$MODE"
echo '=== TEST COMPLETE ==='
TESTSCRIPT

rsync -avz "$LOCAL_DIR/.tmp/run_test.sh" "$REMOTE:/tmp/run_test.sh"
rm -rf "$LOCAL_DIR/.tmp"

ssh "$REMOTE" "chmod +x /tmp/run_test.sh && screen -dmS test_analysis /tmp/run_test.sh"

info "Test started in screen 'test_analysis' on $REMOTE_HOST"
info ""
info "  Check status:  ssh $REMOTE_HOST 'screen -list | grep test_analysis'"
info "  See log:       ssh $REMOTE_HOST 'tail -30 /tmp/test_analysis.log'"
info "  Monitor live:  ssh $REMOTE_HOST 'screen -r test_analysis'"
info "  Detach:        Ctrl+A, D"
info ""
info "When done, fetch results:"
info "  rsync -avz $REMOTE:\$REMOTE_REPO_DIR/$OUTPUT_DIR/RESPONSES/ $LOCAL_DIR/$OUTPUT_DIR/ && cat $LOCAL_DIR/$OUTPUT_DIR/RESPONSES/*/q1.md | head -5"
