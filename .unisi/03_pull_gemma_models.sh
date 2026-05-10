#!/bin/bash

curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": true}'
# curl http://localhost:11434/api/generate -d '{"model": "gemma4:26b", "prompt": "Hello", "stream": false}'

REPO_DIR="$HOME/paper-scraper"
CODE_DIR="$REPO_DIR/paper_scraper"
OUTPUT_FOLDER="$REPO_DIR/gemma4_26b-pdf2text-respones"
QUESTION_FOLDER="$REPO_DIR/QUESTIONS"
PAPERS_FOLDER="$REPO_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"
rm -rf "$OUTPUT_FOLDER"

# TESTS: (run manually)
# cd "$HOME/paper-scraper"; pixi run analyze --questions "$QUESTION_FOLDER" --papers_dir "$CODE_DIR/__HELPER_DIR__/SINGLE_PAPER_FOLDER" --output_dir "$REPO_DIR/test_1" --ollama-opts.model "gemma4:26b"; cat "$REPO_DIR/test_1/RESPONSES/attention_is_all_you_need/q1.md" 

pixi run analyze \
    --questions "$QUESTION_FOLDER" \
    --papers_dir "$PAPERS_FOLDER" \
    --output_dir "$OUTPUT_FOLDER" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2text"

pixi run analyze \
    --questions "$QUESTION_FOLDER" \
    --papers_dir "$PAPERS_FOLDER" \
    --output_dir "$OUTPUT_FOLDER" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2image"

cat "$OUTPUT_FOLDER/RESPONSES/An_Opinion_Paper_on_Aerogels_for_Biomedical_and_Environmental_Applications/q1.md"
