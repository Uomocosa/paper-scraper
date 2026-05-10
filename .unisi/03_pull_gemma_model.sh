#!/bin/bash

curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": true}'
# curl http://localhost:11434/api/generate -d '{"model": "gemma4:26b", "prompt": "Hello", "stream": false}'

OUTPUT_FOLDER="./pdf2text-respones"
rm -rf "$OUTPUT_FOLDER"

pixi run analyze \
    --questions "./QUESTIONS" \
    --papers_dir "./OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --output_dir "$OUTPUT_FOLDER" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2text"


cd "$HOME/paper-scraper/pdf2text-respones/An_Opinion_Paper_on_Aerogels_for_Biomedical_and_Environmental_Applications"
cat q1.md
