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
| 3a | AI Analysis (server) | Ollama + gemma4:26b on GPU server |
| 3b | AI Analysis (local) | OpenCode Go → DeepSeek V4 Flash (no GPU) |
| 4 | Smart Filter | ❌ Not implemented |

## Quick Start

### Prerequisites

- **Python 3.11+** with **pixi** (`pipx install pixi`)
- **Grobid**: `docker run --rm -p 8070:8070 grobid/grobid:0.9.0-full` (for reference extraction)
- **API Key**: Create `.env` in the **parent directory** with:
  ```
  PYALEX_API_KEY=<your_openalex_key>   # openalex.org/settings/api
  OPENCODE_GO_KEY=<your_go_key>        # opencode.ai/go (optional)
  ```

### Download papers

```bash
bash scripts/download_papers.sh
```

### Analyze with DeepSeek V4 Flash (local, no GPU)

```bash
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

### Data compilation & cleaning pipeline

| Script | Description |
|--------|-------------|
| `scripts/compile_results.py` | Merge all model outputs into `compiled_adsorption_data.csv` |
| `scripts/detect_conflicts.py` | Find papers analyzed by multiple models, compare values |
| `scripts/classify_entries.py` | Add quality flags (HAS_POLYMER, HAS_MOLECULE, etc.) |
| `scripts/filter_for_bioinformatics.py` | Filter high-quality rows, add SMILES lookup, output `ready_for_bioinformatics.csv` |

### Review workflow (re-analyze with another model)

| Script | Description |
|--------|-------------|
| `scripts/list_good_papers.py` | Rank papers by data quality, export CSV for re-analysis |
| `scripts/reanalyze_papers.sh` | Re-analyze selected papers with a different Go model |
| `scripts/compare_models.py` | Compare extraction results between two models side-by-side |

### Remote test & iteration

| Script | Description |
|--------|-------------|
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
| `scripts/remote_analysis.sh` | — | The script that actually runs on the server |

## OllamaOptions fields

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `tinyllama` | Model name |
| `base_url` | `http://localhost:11434` | API base URL |
| `completion_path` | `/api/chat` | Endpoint path (use `/chat/completions` for OpenAI-compatible) |
| `api_key_env` | `""` | Env var name for API key (empty = Ollama mode) |
| `system_prompt_file` | `""` | Path to file containing system prompt text |
| `system_prompt` | `"You are a helpful..."` | System prompt text |
| `temperature` | `1.0` | LLM temperature |
| `max_context_tokens` | `256` | Context window size |
| `handle_pdfs` | `"pdf2text"` | `"pdf2text"` or `"pdf2image"` (images sent in OpenAI-compatible format) |

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

## Generated files

| File | Description |
|------|-------------|
| `compiled_adsorption_data.csv` | Raw merged output from all models |
| `classified_adsorption_data.csv` | Same with HAS_POLYMER, HAS_MOLECULE, HAS_* flags |
| `conflicts_report.csv` | Papers where two models disagree |
| `ready_for_bioinformatics.csv` | Clean, high-quality rows ready for ML training |
| `papers_for_review.csv` | Selected papers for re-analysis |

## Testing

```bash
# Default (skips slow/external tests)
pixi run pytest

# Run all including slow
pixi run pytest -o "addopts="

# Run DeepSeek Go tests (requires OPENCODE_GO_KEY in ../.env)
pixi run pytest -o "addopts=" -m requires_opencode_go_key
```
