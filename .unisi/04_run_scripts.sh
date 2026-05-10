#!/bin/bash

REPO_DIR="$HOME/paper-scraper"
CODE_DIR="$REPO_DIR/paper_scraper"
OUTPUT_FOLDER_TEXT="$REPO_DIR/gemma4_26b-pdf2text-respones"
OUTPUT_FOLDER_IMAGE="$REPO_DIR/gemma4_26b-pdf2text-respones"
QUESTION_FOLDER="$REPO_DIR/QUESTIONS"
PAPERS_FOLDER="$REPO_DIR/OUTPUT_DIR/DOWNLOADED_PAPERS"
rm -rf "$OUTPUT_FOLDER_TEXT"
rm -rf "$OUTPUT_FOLDER_IMAGE"

# TESTS: (run manually)
# cd "$HOME/paper-scraper"; pixi run analyze --questions "$QUESTION_FOLDER" --papers_dir "$CODE_DIR/__HELPER_DIR__/SINGLE_PAPER_FOLDER" --output_dir "$REPO_DIR/test_1" --ollama-opts.model "gemma4:26b"; cat "$REPO_DIR/test_1/RESPONSES/attention_is_all_you_need/q1.md" 

pixi run analyze \
    --questions "$QUESTION_FOLDER" \
    --papers_dir "$PAPERS_FOLDER" \
    --output_dir "$OUTPUT_FOLDER_TEXT" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2text"

pixi run analyze \
    --questions "$QUESTION_FOLDER" \
    --papers_dir "$PAPERS_FOLDER" \
    --output_dir "$OUTPUT_FOLDER_IMAGE" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2image"

cat "$OUTPUT_FOLDER_TEXT/RESPONSES/An_Opinion_Paper_on_Aerogels_for_Biomedical_and_Environmental_Applications/q1.md"
cat "$OUTPUT_FOLDER_IMAGE/RESPONSES/An_Opinion_Paper_on_Aerogels_for_Biomedical_and_Environmental_Applications/q1.md"

# TO PUSH YOU HAVE TO LOGIN FIRST (I use a personal access token)
git add "$OUTPUT_FOLDER_TEXT"
git add "$OUTPUT_FOLDER_IMAGE"
git commit -m "UNISI SSH Server RESPONSES ($(date))"
git push
