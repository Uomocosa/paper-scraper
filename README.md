# Paper Scraper — Automated Literature Review Pipeline

Automated snowballing literature-review agent: extract references from seed PDFs,
download papers via OpenAlex, analyze with local or cloud LLMs (Ollama, OpenCode Go),
compile results into a clean CSV ready for ML training.

## Architecture

```
SEED_PAPERS/  →  Grobid  →  DOIs  →  OpenAlex  →  PDFs  →  LLM Analysis  →  CSV
                         ↘                                               ↙
                    Search Filter (topic + keywords)     compile_results.py
```

| Phase | Name | Tool | Output |
|-------|------|------|--------|
| 1 | Citation Extraction | Grobid (localhost:8070) | Extracted DOIs |
| 2 | Crawl & Download | OpenAlex API (pyalex) | PDFs in `OUTPUT_DIR/DOWNLOADED_PAPERS/` |
| 3a | AI Analysis (GPU server) | Ollama + gemma4:26b | `gemma4_26b-*-respones/` |
| 3b | AI Analysis (local, no GPU) | OpenCode Go → any model | `review_*/` or custom dirs |
| 4 | Data Compilation | Python scripts | `compiled_adsorption_data.csv` |
| 5 | Quality Filtering | Python scripts | `ready_for_bioinformatics.csv` |
| 6 | Smart Filter | ❌ Not implemented | — |

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
bash scripts/analyze_deepseek.sh
```

### Analyze via Ollama on UNISI GPU server

```bash
bash scripts/sync_papers.sh       # rsync PDFs + scripts to server
bash scripts/run_analysis.sh      # start analysis in screen session
bash scripts/sync_results.sh      # wait and rsync results back
```

### Compile results into CSV

```bash
pixi run python scripts/compile_results.py
pixi run python scripts/classify_entries.py
pixi run python scripts/filter_for_bioinformatics.py
```

Output: `ready_for_bioinformatics.csv` — ready for ML training.

## Full Pipeline Flow

```
                           ┌──────────────────┐
                           │  SEED_PAPERS/    │
                           └────────┬─────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  Grobid Extraction   │  Phase 1
                         │  (reference DOIs)    │
                         └──────────┬──────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
         ┌─────▼──────┐      ┌──────▼──────┐      ┌─────▼──────┐
         │ Search by  │      │ Search by   │      │ References │
         │ Topic+KW   │      │ Topic only  │      │ of refs    │
         └─────┬──────┘      └──────┬──────┘      └─────┬──────┘
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  OpenAlex Download   │  Phase 2
                         │  (OA + non-OA URLs)  │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
          ┌─────────▼─────┐ ┌───────▼───────┐ ┌─────▼─────────┐
          │  Ollama/Gemma │ │ DeepSeek V4   │ │ Kimi K2.6     │
          │  (GPU server) │ │ Flash (local) │ │ re-analysis   │
          └─────────┬─────┘ └───────┬───────┘ └─────┬─────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  compile_results.py  │  Phase 4
                         │  (merge all models)  │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  classify_entries.py │  Phase 5
                         │  (HAS_POLYMER, etc)  │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ filter_for_bioinfo  │  Phase 6
                         │  .py (clean + SMILES)│
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ ready_for_bioinfor  │
                         │ matics.csv          │
                         └─────────────────────┘
```

## Scripts Reference

### Local pipeline

| Script | Description |
|--------|-------------|
| `scripts/download_papers.sh` | Download papers from OpenAlex (6 targeted searches) |
| `scripts/analyze_deepseek.sh` | Analyze all papers locally via OpenCode Go → DeepSeek V4 Flash |

### Data compilation & cleaning

| Script | Description |
|--------|-------------|
| `scripts/compile_results.py` | Merge all model outputs into `compiled_adsorption_data.csv` |
| `scripts/classify_entries.py` | Add quality flags: HAS_POLYMER, HAS_MOLECULE, HAS_WATER_PH, HAS_CONCENTRATION, HAS_CAPACITY |
| `scripts/detect_conflicts.py` | Find papers analyzed by multiple models, compare values |
| `scripts/filter_for_bioinformatics.py` | Keep rows with polymer+molecule, deduplicate, add SMILES lookup → `ready_for_bioinformatics.csv` |
| `scripts/select_for_review.py` | Select papers for re-analysis: `--dense N`, `--diverse N`, `--complete N`, `--overlap`, supports `all` |

### Review workflow (cross-model validation)

| Script | Description |
|--------|-------------|
| `scripts/list_good_papers.py` | Rank papers by data quality, export CSV for re-analysis |
| `scripts/reanalyze_papers.sh` | Re-analyze selected papers with a different Go model (e.g., `kimi-k2.6`, `mimo-v2.5`) |
| `scripts/compare_models.py` | Compare two model outputs with 5-field matching (10% numeric tolerance) |

### UNISI server deployment

| Script | Step | Description |
|--------|------|-------------|
| `scripts/sync_papers.sh` | 1 | rsync PDFs + QUESTIONS + remote script to server |
| `scripts/run_analysis.sh` | 2 | Start Ollama analysis in a `screen` session on server |
| `scripts/sync_results.sh` | 3 | Wait for completion, rsync results back |
| `scripts/check_analysis.sh` | — | Check remote analysis log (`cat /tmp/paper_analysis.log`) |
| `scripts/run_all.sh` | 1→3 | Full pipeline in one command |
| `scripts/test_rsync.sh` | — | Verify SSH + rsync connectivity |
| `scripts/remote_analysis.sh` | — | The script that actually runs on the server (pulled by sync_papers.sh) |

### Test & iteration

| Script | Description |
|--------|-------------|
| `scripts/test_remote.sh` | Analyze N random papers on UNISI server (fast iteration) |
| `scripts/test_analyze.sh` | Analyze N random papers locally with tinyllama |

## OllamaOptions fields

Available via `--ollama-opts.<field>` in CLI, or directly via `OllamaOptions(...)` in Python.

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `tinyllama` | Model name. Supported: `gemma4:26b`, `deepseek-v4-flash`, `deepseek-v4-pro`, `kimi-k2.6`, `kimi-k2.7`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m3`, `qwen3.7-plus`, `glm-5`, etc. |
| `base_url` | `http://localhost:11434` | API base URL |
| `completion_path` | `/api/chat` | Endpoint path. Use `/chat/completions` for OpenAI-compatible APIs |
| `api_key_env` | `""` | Env var name for API key. Empty = Ollama mode (no auth). Set to `OPENCODE_GO_KEY` for Go |
| `system_prompt_file` | `""` | Path to file containing system prompt text |
| `system_prompt` | `"You are a helpful..."` | System prompt text |
| `temperature` | `1.0` | LLM temperature |
| `max_context_tokens` | `256` | Context window size (set to 32768 for Go models) |
| `handle_pdfs` | `"pdf2text"` | `"pdf2text"` or `"pdf2image"` (images sent in OpenAI-compatible format) |

## Output Directories

| Path | Purpose |
|------|---------|
| `SEED_PAPERS/` | Input PDFs for reference extraction |
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` | Downloaded PDFs |
| `OUTPUT_DIR/extracted_references.json` | Extracted references |
| `gemma4_26b-pdf2text-respones/` | Ollama text analysis results (UNISI) |
| `gemma4_26b-pdf2image-respones/` | Ollama image analysis results (UNISI) |
| `opencode_go_deepseek_v4_flash_max_pdf2text_responses/` | DeepSeek V4 Flash text results |
| `review_*/` | Re-analysis results (e.g., `review_kimi-k2_6/`) |
| `paper_scraper/__HELPER_DIR__/` | Temporary test outputs (gitignored) |

## Generated Files

| File | Contents | Rows |
|------|----------|------|
| `compiled_adsorption_data.csv` | Raw merged output from all models (POLYMER_USED, DRUG, pH, CONC, CAP, SOURCE, ANALYZED_BY, PAPER) | ~20K+ |
| `classified_adsorption_data.csv` | Same + quality flags (HAS_POLYMER, HAS_MOLECULE, HAS_WATER_PH, HAS_CONCENTRATION, HAS_CAPACITY) | ~20K |
| `conflicts_report.csv` | Papers where two models disagree | ~0-100 |
| `ready_for_bioinformatics.csv` | Filtered: polymer=yes + molecule=yes + deduplicated + PSMILES/SMILES lookup | ~1.3K |
| `papers_for_review.csv` | Selected papers for re-analysis (generated by `select_for_review.py`) | Variable |
| `model_comparison.csv` | Side-by-side model agreement per paper | Variable |

## Cross-Model Validation

The pipeline supports analyzing the same papers with multiple LLMs and comparing results.
This gives confidence scores for extracted data.

### Available Go models (OpenCode Go)

| Model | Cost/1M in | Cost/1M out | Est. cost/paper |
|-------|-----------|------------|----------------|
| DeepSeek V4 Flash | $0.14 | $0.28 | ~$0.01 |
| MiMo V2.5 | $0.14 | $0.28 | ~$0.01 |
| MiniMax M3 | $0.30 | $1.20 | ~$0.02 |
| Kimi K2.6 | $0.95 | $4.00 | ~$0.06 |
| DeepSeek V4 Pro | $1.74 | $3.48 | ~$0.10 |

All within Go's $60/month cap. MiMo V2.5 is recommended for cheap bulk re-analysis.

### Comparison workflow

```bash
# 1. Select papers
pixi run python scripts/select_for_review.py --complete 30

# 2. Re-analyze with another model
bash scripts/reanalyze_papers.sh mimo-v2.5

# 3. Compare results (5-field matching, 10% tolerance)
pixi run python scripts/compare_models.py --new review_mimo-v2_5
```

### Current agreement rates

| Model pair | Common papers | Rows matched | Agreement |
|-----------|--------------|-------------|-----------|
| DeepSeek V4 Flash vs Kimi K2.6 | 120 | 514 / ~2100 | 24% |
| DeepSeek V4 Flash vs Gemma4:26b | ~0 | — | — (gemma returned only "NO USEFUL DATA") |

The 24% agreement reflects the difficulty of exact row-to-row matching: models extract
different (polymer, drug, pH, conc, cap) combinations from the same paper, even when
both are correct. Matched rows are high-confidence; unmatched ones need manual review.

## Search Configuration

The `SearchFilter` supports:

```python
SearchFilter(
    topics="T10016",                        # OpenAlex topic ID
    keywords="pharmaceutical && adsorption && polymer",  # AND/OR/NOT supported
    max_papers=5000,
    open_access_only=False,                 # True = OA papers only
    year_min=2020,
    year_max=2024,
)
```

Topic IDs: `T10016` (Adsorption), `T11781` (Wastewater Treatment), `T14252` (Water Treatment).
Use `pixi run get_openalex_topics_codes --search-term "adsorption"` to find others.

Keywords support operators: `&&` (AND), `||` (OR), `!` (NOT), parentheses for grouping.

## Testing

```bash
# Default (skips slow/external-service tests)
pixi run pytest

# Run all including slow
pixi run pytest -o "addopts="

# Run DeepSeek Go tests (requires OPENCODE_GO_KEY in ../.env)
pixi run pytest -o "addopts=" -m requires_opencode_go_key
```

## Version

Current: v0.0.1

## Directory Structure

```
lele-paper-scraper/
├── SEED_PAPERS/                    # Input PDFs
├── OUTPUT_DIR/
│   ├── DOWNLOADED_PAPERS/          # 2000+ downloaded PDFs
│   ├── QUESTIONS/                  # Question prompts
│   └── extracted_references.json
├── gemma4_26b-pdf2text-respones/   # 2240 papers (gemma text)
├── gemma4_26b-pdf2image-respones/  # 2240 papers (gemma image)
├── opencode_go_deepseek_v4_flash_max_pdf2text_responses/  # 1711 papers (DeepSeek)
├── review_kimi-k2_6/               # 131 papers (Kimi re-analysis)
├── paper_scraper/                  # Python package
│   ├── OpenAlex/                   # Paper search + download
│   ├── Ollama/                     # LLM API wrapper (Ollama + OpenAI-compatible)
│   ├── Grobid/                     # Reference extraction
│   ├── Utils/                      # PDF text/image extraction
│   ├── pipeline/                   # extract_refs, get_dois, download, analyze
│   ├── Secrets/                    # API key loading from .env
│   └── __HELPER_DIR__/             # Temp test outputs
├── scripts/                        # Bash/Python scripts
│   ├── download_papers.sh          # 6 targeted searches
│   ├── analyze_deepseek.sh         # Full DeepSeek analysis
│   ├── compile_results.py          # Merge model outputs
│   ├── classify_entries.py         # Add quality flags
│   ├── filter_for_bioinformatics.py # Final clean CSV
│   ├── select_for_review.py        # Select papers for re-analysis
│   ├── reanalyze_papers.sh         # Re-analyze with another model
│   ├── compare_models.py           # 5-field model comparison
│   ├── list_good_papers.py         # Rank papers by quality
│   ├── detect_conflicts.py         # Find model disagreements
│   ├── sync_papers.sh              # rsync to UNISI server
│   ├── run_analysis.sh             # Start analysis on server
│   ├── sync_results.sh             # Pull results from server
│   ├── check_analysis.sh           # Check server analysis log
│   └── remote_analysis.sh          # Script that runs on server
├── compiled_adsorption_data.csv    # ~20K rows, all models
├── classified_adsorption_data.csv  # With quality flags
├── ready_for_bioinformatics.csv    # ~1.3K rows, for ML
├── model_comparison.csv            # DeepSeek vs Kimi agreement
└── pixi.toml                       # Dependencies
```
