# scripts/

Deployment pipeline for the UNISI GPU server and local analysis scripts.

## Local Scripts

| Script | Description |
|--------|-------------|
| `download_papers.sh` | Download papers from OpenAlex (multiple targeted searches) |
| `analyze_deepseek.sh` | Analyze all papers locally via OpenCode Go → DeepSeek V4 Flash |
| `test_analyze.sh` | Fast local test: analyze N random papers with tinyllama |
| `config.sh` | Shared config sourced by all scripts |

## Remote Scripts (UNISI GPU Server)

| Script | Step | Description |
|--------|------|-------------|
| `download_papers.sh` | 1 | Download papers locally from OpenAlex |
| `sync_papers.sh` | 2 | rsync PDFs + QUESTIONS + `remote_analysis.sh` to server |
| `run_analysis.sh` | 3 | Start Ollama analysis in a `screen` session on remote |
| `sync_results.sh` | 4 | Wait for completion, rsync results back |
| `check_analysis.sh` | — | Read the server's analysis log to see what happened |
| `run_all.sh` | 1→4 | Full pipeline in one command |
| `test_remote.sh` | — | Fast test: analyze N random papers on server |
| `test_rsync.sh` | — | Verify SSH + rsync connectivity |
| `remote_analysis.sh` | — | The script that actually runs on the server (pulled by `sync_papers.sh`) |
| `config.sh` | — | Shared config sourced by all scripts |

## Prerequisites

### For local scripts (`analyze_deepseek.sh`, `download_papers.sh`)

- **pixi** installed (see `config.sh`)
- **OpenAlex API key** in `../.env`: `PYALEX_API_KEY=<key>`
- **OpenCode Go key** in `../.env`: `OPENCODE_GO_KEY=<key>` (for `analyze_deepseek.sh`)

### For remote scripts (`sync_papers.sh`, `run_analysis.sh`, etc.)

- **WSL** with bash, ssh, rsync
- **OpenVPN** connected to UNISI network
- **SSH** access to `maggiori@mec-ai`
- **pixi** installed in Windows (see `config.sh`)

## Quick start

### Local analysis with DeepSeek V4 Flash

```bash
bash scripts/analyze_deepseek.sh
```

### Full remote pipeline (UNISI server)

```bash
bash scripts/download_papers.sh       # step 1: download locally
bash scripts/sync_papers.sh           # step 2: sync to server
bash scripts/run_analysis.sh          # step 3: start analysis on server
bash scripts/sync_results.sh          # step 4: fetch results
```

### Fast iteration on server

```bash
bash scripts/test_remote.sh 5         # analyze 5 random papers on server
bash scripts/check_analysis.sh        # see the log
```
