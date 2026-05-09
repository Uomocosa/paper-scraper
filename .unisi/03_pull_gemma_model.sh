curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": true}'
curl http://localhost:11434/api/generate -d '{"model": "gemma4:26b", "prompt": "Hello", "stream": false}'
pixi run analyze \
    --questions "Explain this paper in 1 line." \
    --ollama-opts.base-url "http://localhost:11434" \
    --ollama-opts.model "gemma4:26b"
