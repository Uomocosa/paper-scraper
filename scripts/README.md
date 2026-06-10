# scripts/

Deployment pipeline for the UNISI GPU server. Runs in WSL, downloads papers
locally, then syncs to the remote server for Ollama analysis.

## Prerequisites

- **WSL** with bash, ssh, rsync
- **OpenVPN** connected to UNISI network
- **SSH** access to `maggiori@mec-ai`
- **pixi** installed in Windows (see `config.sh`)

## Scripts

| Script | Step | Description |
|--------|------|-------------|
| `download_papers.sh` | 1 | Download papers from OpenAlex (topics/keywords filter) |
| `sync_papers.sh` | 2 | rsync PDFs to remote server |
| `run_analysis.sh` | 3 | Start Ollama analysis in a `screen` session on remote |
| `sync_results.sh` | 4 | Wait for completion, rsync results back |
| `run_all.sh` | 1→4 | Full pipeline in one command |
| `test_rsync.sh` | — | Verify SSH + rsync connectivity |
| `config.sh` | — | Shared config sourced by all scripts |

## Quick start

```bash
bash scripts/run_all.sh                         # full auto pipeline
bash scripts/download_papers.sh                 # step 1 only
bash scripts/sync_results.sh --status           # check if analysis is running
```

> **Note:** The local `pixi run` commands (`pixi run scrape`, `pixi run download_papers`, etc.)
> are the primary interface. These scripts wrap them for the remote-server workflow.
