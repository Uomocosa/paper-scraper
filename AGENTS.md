# AGENTS.md - Paper Scraper

## Quick Commands

```bash
pixi run extract_refs                          # Grobid reference extraction
pixi run download_papers                       # Download via OpenAlex
bash scripts/analyze_deepseek.sh               # Analyze with DeepSeek V4 Flash
pixi run python scripts/compile_results.py     # Merge all model outputs
pixi run python scripts/classify_entries.py    # Add quality flags
pixi run python scripts/filter_for_bioinformatics.py  # Final clean CSV
pixi run pytest                                # Run tests (skip slow/external)
pixi run pytest -o "addopts=" -m requires_opencode_go_key  # DeepSeek Go tests
```

## Architecture

| Phase | Tool |
|-------|------|
| Extract refs | Grobid (localhost:8070) |
| Download | OpenAlex API (pyalex) |
| Analyze (GPU server) | Ollama + gemma4:26b |
| Analyze (local) | OpenCode Go → any model |
| Compile | `compile_results.py` |
| Filter | `classify_entries.py` + `filter_for_bioinformatics.py` |
| Validate | `compare_models.py` (5-field, 10% tolerance) |

## OllamaOptions

| Field | Use for |
|-------|---------|
| `model` | `deepseek-v4-flash`, `gemma4:26b`, `kimi-k2.6`, `mimo-v2.5` |
| `base_url` | `http://localhost:11434` (Ollama) or `https://opencode.ai/zen/go/v1` (Go) |
| `completion_path` | `/api/chat` (Ollama) or `/chat/completions` (Go) |
| `api_key_env` | `OPENCODE_GO_KEY` for Go, empty for Ollama |
| `system_prompt_file` | Path to prompt text file |
| `max_context_tokens` | 32768 for Go models |
| `handle_pdfs` | `pdf2text` (default) or `pdf2image` |

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/compile_results.py` | Merge all model response dirs into one CSV |
| `scripts/classify_entries.py` | Add HAS_POLYMER, HAS_MOLECULE, etc. flags |
| `scripts/filter_for_bioinformatics.py` | Filter to polymer+molecule rows, dedup, SMILES lookup |
| `scripts/select_for_review.py` | Select papers: `--dense N`, `--diverse N`, `--complete N`, `--overlap` |
| `scripts/reanalyze_papers.sh` | Re-analyze selected papers with another model |
| `scripts/compare_models.py` | 5-field comparison with 10% tolerance |
| `scripts/analyze_deepseek.sh` | Full DeepSeek analysis (2000+ papers) |

## Data Files

| File | Rows | Description |
|------|------|-------------|
| `compiled_adsorption_data.csv` | ~20K | Raw merged from all models |
| `classified_adsorption_data.csv` | ~20K | With HAS_* flags |
| `ready_for_bioinformatics.csv` | ~1.3K | Clean, deduplicated, for ML |
| `model_comparison.csv` | ~120 | DeepSeek vs Kimi agreement |

## Testing

- Default skip: `requires_grobid`, `requires_ollama`, `requires_opencode_go_key`
- DeepSeek Go tests: `pixi run pytest -o "addopts=" -m requires_opencode_go_key`
