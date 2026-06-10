#!/bin/bash

curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": false}'
curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:31b", "stream": false}'
curl http://localhost:11434/api/generate -d '{"model": "gemma4:26b", "prompt": "Hello", "stream": false}'
curl http://localhost:11434/api/generate -d '{"model": "gemma4:31b", "prompt": "Hello", "stream": false}'

# nohup commands
# nohup curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:26b", "stream": false}' > ollama_pull.log 2>&1 &
# nohup curl -X POST http://localhost:11434/api/pull -d '{"name": "gemma4:31b", "stream": false}' > ollama_pull.log 2>&1 &
