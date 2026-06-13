# Paper Scraper — Automated Literature Review Pipeline

Automated snowballing literature-review agent: extract references from seed PDFs, download papers via OpenAlex, analyze with local or cloud LLMs.

## CI Status

| Python | Status |
|--------|--------|
| 3.11 | ![3.11](https://github.com/Uomocosa/paper-scraper/actions/workflows/test-3.11.yml/badge.svg) |
| 3.12 | ![3.12](https://github.com/Uomocosa/paper-scraper/actions/workflows/test-3.12.yml/badge.svg) |
| 3.13 | ![3.13](https://github.com/Uomocosa/paper-scraper/actions/workflows/test-3.13.yml/badge.svg) |
| 3.14 | ![3.14](https://github.com/Uomocosa/paper-scraper/actions/workflows/test-3.14.yml/badge.svg) |

## Architecture & Phases

| Phase | Name | Tool |
|-------|------|------|
| 0 | Setup | — |
| 1 | Citation Extraction | Grobid (localhost:8070) |
| 2 | Crawl & Download | OpenAlex API (pyalex) |
| 3a | AI Analysis (local) | Ollama + gemma4:26b on GPU server |
| 3b | AI Analysis (cloud) | OpenCode Go → DeepSeek V4 Flash (no GPU needed) |
| 4 | Smart Filter | ❌ Not implemented |

## Quick Start

### Prerequisites

- **Python 3.11+** with **pixi** (`pipx install pixi`)
- **Grobid**: `docker run --rm -p 8070:8070 grobid/grobid:0.9.0-full` (for reference extraction)
- **API Key**: Create `.env` in the **parent directory** with:
  ```
  PYALEX_API_KEY=<your_openalex_key>   # openalex.org/settings/api
  OPENCODE_GO_KEY=<your_go_key>        # opencode.ai/go (optional, for cloud analysis)
  ```

### Download papers

```bash
bash scripts/download_papers.sh
```

### Analyze with DeepSeek V4 Flash (local, no GPU)

```bash
# Requires OPENCODE_GO_KEY in ../.env (OpenCode Go subscription)
bash scripts/analyze_deepseek.sh
```

### Analyze via Ollama on UNISI GPU server

```bash
bash scripts/sync_papers.sh
bash scripts/run_analysis.sh
bash scripts/sync_results.sh
```

## Scripts

### Local pipeline

| Script | Description |
|--------|-------------|
| `scripts/download_papers.sh` | Download papers from OpenAlex (multiple targeted searches) |
| `scripts/analyze_deepseek.sh` | Analyze all papers locally via OpenCode Go → DeepSeek V4 Flash |
| `scripts/test_remote.sh` | Fast test: analyze N random papers on UNISI server |
| `scripts/test_analyze.sh` | Fast local test: analyze N random papers with tinyllama |

### UNISI server deployment

| Script | Step | Description |
|--------|------|-------------|
| `scripts/sync_papers.sh` | 1 | rsync PDFs + QUESTIONS + remote script to server |
| `scripts/run_analysis.sh` | 2 | Start Ollama analysis in a `screen` session on server |
| `scripts/sync_results.sh` | 3 | Wait for completion, rsync results back |
| `scripts/check_analysis.sh` | — | Check remote analysis log |
| `scripts/run_all.sh` | 1→3 | Full pipeline in one command |
| `scripts/test_rsync.sh` | — | Verify SSH + rsync connectivity |

## Config Options

```python
from paper_scraper.main import main, Config
from paper_scraper.OpenAlex import get_dois_from_filter
from paper_scraper.Ollama import Options as OllamaOptions

# Minimal
config = Config()

# Download with targeted search
config = Config(
    search_filter=get_dois_from_filter.SearchFilter(
        topics="T10016",
        keywords="pharmaceutical && adsorption && polymer",
        max_papers=1000,
        open_access_only=False,  # True = OA papers only
    ),
)

# Analyze with DeepSeek V4 Flash (no GPU needed)
config = Config(
    questions=["Extract adsorption data as CSV: POLYMER_USED,DRUG,..."],
    ollama_opts=OllamaOptions(
        model="deepseek-v4-flash",
        base_url="https://opencode.ai/zen/go/v1",
        completion_path="/chat/completions",
        api_key_env="OPENCODE_GO_KEY",
        system_prompt_file="/tmp/prompt.txt",
        max_context_tokens=32768,
    ),
    max_chunks=1,
    handle_pdfs="pdf2text",
)

# Analyze with Ollama (requires GPU server)
config = Config(
    questions=["..."],
    ollama_opts=OllamaOptions(model="gemma4:26b"),
)

# Parallel processing
config = Config(batch_size=4)
```

### OllamaOptions fields

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `tinyllama` | Model name |
| `base_url` | `http://localhost:11434` | API base URL |
| `completion_path` | `/api/chat` | Endpoint path (use `/chat/completions` for OpenAI-compatible APIs) |
| `api_key_env` | `""` | Env var name for API key (empty = Ollama mode) |
| `system_prompt_file` | `""` | Path to file containing system prompt |
| `system_prompt` | `"You are a helpful..."` | System prompt text |
| `temperature` | `1.0` | LLM temperature |
| `max_context_tokens` | `256` | Context window size |
| `handle_pdfs` | `"pdf2text"` | `"pdf2text"` or `"pdf2image"` |

## Directories

| Path | Purpose |
|------|---------|
| `SEED_PAPERS/` | Input PDFs for reference extraction |
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` | Downloaded PDFs |
| `OUTPUT_DIR/extracted_references.json` | Extracted references |
| `gemma4_26b-pdf2text-respones/` | Ollama text analysis results (UNISI) |
| `gemma4_26b-pdf2image-respones/` | Ollama image analysis results (UNISI) |
| `opencode_go_deepseek_v4_flash_max_pdf2text_responses/` | DeepSeek text analysis results (local) |
| `paper_scraper/__HELPER_DIR__/` | Temp test outputs (gitignored) |

## Testing

```bash
# Default (skips slow/external tests)
pixi run pytest

# Run all including slow
pixi run pytest -o "addopts="

# Run DeepSeek Go tests (requires OPENCODE_GO_KEY in ../.env)
pixi run pytest -o "addopts=" -m requires_opencode_go_key
```
