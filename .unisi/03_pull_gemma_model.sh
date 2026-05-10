curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": true}'
curl http://localhost:11434/api/generate -d '{"model": "gemma4:26b", "prompt": "Hello", "stream": false}'
pixi run analyze \
    --questions "./QUESTIONS" \
    --papers_dir "./OUTPUT_DIR/DOWNLOADED_PAPERS" \
    --output_dir "./RESPONSES/pdf2text" \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b" \
    --ollama-opts.handle-pdfs "pdf2text"

cd "OUTPUT_DIR/RESPONSES/An_Opinion_Paper_on_Aerogels_for_Biomedical_and_Environmental_Applications"
cat q1.md
