# AGENTS.md - Paper Scraper

## Quick Commands

```bash
pixi run extract_refs                          # Grobid reference extraction
pixi run download_papers                       # Download via OpenAlex
bash scripts/analyze_deepseek.sh               # Analyze with DeepSeek V4 Flash
pixi run python scripts/resolve_smiles.py      # Drug SMILES (dict + PubChem)
pixi run python scripts/resolve_polymer_batch.py --test                 # Test server connection
pixi run python scripts/resolve_polymer_batch_orchestrator.py            # Spawn 5 terminals (all parts)
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 0     # Single part (manual)
pixi run python scripts/merge_polymer_results.py          # Merge all parts
pixi run python scripts/build_training_dataset.py     # Merge all → output/
pixi run python scripts/match_model_datasets.py       # Cross-model matching
pixi run python scripts/check_featurization_failures.py  # Check rows that fail bio featurization
pixi run python scripts/convert_to_pdcc_format.py     # Convert CSVs to PDCC format (6 cols)
pixi run python scripts/build_reviewed_dataset.py     # Build dataset from manual review
pixi run pytest                                # Run tests (skip slow/external)
```

## Architecture

| Phase | Script | Method |
|-------|--------|--------|
| Extract refs | Grobid | localhost:8070 |
| Download | OpenAlex | pyalex API |
| Analyze | ollama / opencode go | GPU server / local |
| Compile | `compile_results.py` | Merge response dirs |
| Classify | `classify_entries.py` | Add HAS_* flags |
| Drug SMILES | `resolve_smiles.py` | dict + PubChem + metal patterns |
| Polymer PSMILES | `resolve_polymer_batch.py` (parallel) + `merge_polymer_results.py` | opencode serve + WebFetch |
| Build datasets | `build_training_dataset.py` | Join + dedup + split |
| Match models | `match_model_datasets.py` | 5-field, 10% tolerance |
| Featurization check | `check_featurization_failures.py` | Validate vs real bio featurization (10 stages) |

## Pipeline

```
classified → resolve_smiles.py → drug_smiles.json

           → resolve_polymer_batch.py --total 5 --part 0  →  part0.json
           → resolve_polymer_batch.py --total 5 --part 1  →  part1.json
           → resolve_polymer_batch.py --total 5 --part 2  →  part2.json
           → resolve_polymer_batch.py --total 5 --part 3  →  part3.json
           → resolve_polymer_batch.py --total 5 --part 4  →  part4.json
                                                                ↓
                                                      merge_polymer_results.py
                                                                ↓
                                                        polymer_psmiles.json
                                                                ↓
                                           build_training_dataset.py → training_dataset_*.csv
                                                                       ↓
                                                          match_model_datasets.py (matched set)
                                                                       ↓
                                                      convert_to_pdcc_format.py → pdcc_*.csv

claude_opus_4_8_review/ → build_reviewed_dataset.py → training_dataset_reviewed.csv
                                                           ↓
                                                      convert_to_pdcc_format.py → pdcc_opus.csv
```

## Polymer Resolution (parallel, per-paper sessions)

The DeepSeek reasoning model cannot search the web. Instead, run `opencode serve`
on port 4092 with minimal config (WebFetch only, no skills). The agent reads
`CONTEXT.txt` and `reference_psmiles.csv` for context, searches the web for
"PSMILES of <polymer>", and checks the paper PDF for any SMILES strings.

**Each paper gets its own session** — no context pollution between papers.
Paper #20 gets same quality as paper #1.

### Context files in `opencode-serve-polymers/`

| File | Purpose |
|------|---------|
| `CONTEXT.txt` | Project context, rules, output format, abbreviation dictionary |
| `reference_psmiles.csv` | Curated ground-truth PSMILES for 30+ common polymers |
| `opencode.json` | Minimal config: WebFetch allowed, all skills denied. DS V4 Flash with `thinking.reasoning_effort: max` |

### Workflow:

```bash
# Terminal 0: start server once
cd opencode-serve-polymers
opencode serve --port 4092 --hostname 127.0.0.1

# All 5 terminals at once:
pixi run python scripts/resolve_polymer_batch_orchestrator.py

# Or manually:
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 0
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 1
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 2
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 3
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 4

# After all finish: merge
pixi run python scripts/merge_polymer_results.py
```

Each terminal handles ~20 papers, saving to its own part file (no locking conflicts).
Resume-safe: if a terminal crashes, re-run the same command and it skips already-done papers.

## Output Files (PDCC format — 6 cols: POLYMER_USED, DRUG, WATER_PH, CONCENTRATION, CAPACITY, SOURCE)

| File | Rows | Description |
|------|------|-------------|
| `output/pdcc_deepseek.csv` | 252 | DeepSeek V4 Flash only |
| `output/pdcc_kimi.csv` | 123 | Kimi K2.6 only |
| `output/pdcc_gemma4_image.csv` | 43 | Gemma4 (pdf2image) |
| `output/pdcc_gemma4_text.csv` | 0 | Gemma4 (pdf2text) |
| `output/pdcc_deepseek_kimi_gemma.csv` | 321 | All models combined |
| `output/pdcc_matched_deepseek_kimi.csv` | 94 | DeepSeek + Kimi agreed subset |
| `output/pdcc_opus.csv` | 60 | Manual review (Claude Opus 4) |
| `output/paper_scraper_complete_smiles.json` | 124 | Drug → SMILES (ground truth) |
| `output/paper_scraper_complete_psmiles.json` | 212 | Polymer → PSMILES (ground truth) |

### helper_output_dir/

Intermediate files from the auto pipeline (old CSVs with extra columns, featurization reports, polymer part files, old JSONs, logs). Not consumed by bio directly.

### Manual Review (`claude_opus_4_8_review/`)

Papers were manually reviewed to fix bad SMILES, range strings, and composite polymers. The review produced 4 files used by `build_reviewed_dataset.py`:
- `adsorption_data.csv` + `adsorption_data_rsm_supplementary.csv` — hand-verified data
- `drugs_smiles.json` — verified SMILES with metadata
- `polymers_psmiles.json` — curated PSMILES with notes

## Dependencies

- `bio` from `../lele-py-bioinformatics` (added as pixi pypi-dependency)
- `dimorphite-dl` may need manual install: `pixi run pip install dimorphite-dl`

## Testing

- Default skip: `requires_grobid`, `requires_ollama`, `requires_opencode_go_key`
- Run all: `pixi run pytest -o "addopts="`
