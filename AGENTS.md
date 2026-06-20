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

## Output Files

| File | Rows | Description |
|------|------|-------------|
| `output/training_dataset_deepseek.csv` | 379 | DeepSeek-only, with KIMI_MATCHED flag |
| `output/training_dataset_matched.csv` | 205 | Gold standard (both models agree) |
| `output/drug_smiles.json` | 125 | Drug → SMILES (102 resolved) |
| `output/polymer_psmiles.json` | ~210 | Polymer → PSMILES |

## Testing

- Default skip: `requires_grobid`, `requires_ollama`, `requires_opencode_go_key`
- Run all: `pixi run pytest -o "addopts="`
