# Scripts Reference

## Phase 1: Data Collection

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `download_papers.sh` | Download papers from OpenAlex via pyalex (6 targeted searches) | SearchFilter config | `OUTPUT_DIR/DOWNLOADED_PAPERS/` |
| `analyze_deepseek.sh` | Analyze all papers via OpenCode Go → DeepSeek V4 Flash | PDFs + questions | `opencode_go_deepseek_v4_flash_max_pdf2text_responses/` |
| `remote_analysis.sh` | Analysis script deployed to UNISI GPU server | PDFs + questions | `gemma4_26b-*-respones/` |
| `sync_papers.sh` | rsync PDFs + QUESTIONS + remote script to UNISI server | — | — |
| `run_analysis.sh` | Start Ollama analysis in a `screen` session on server | — | — |
| `sync_results.sh` | Wait for completion, rsync results back from server | — | — |
| `check_analysis.sh` | Check remote analysis log (`cat /tmp/paper_analysis.log`) | — | — |
| `run_all.sh` | Full server pipeline in one command (sync → run → sync) | — | — |
| `test_remote.sh` | Analyze N random papers on UNISI server (fast iteration) | — | — |
| `test_analyze.sh` | Analyze N random papers locally with tinyllama | — | — |
| `test_rsync.sh` | Verify SSH + rsync connectivity to server | — | — |
| `download_and_analyze.sh` | Download + analyze in one step | — | — |

## Phase 2: Compilation & Classification

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `compile_results.py` | Merge all model response dirs into one CSV (scans RESPONSE_DIRS) | Model response directories | `compiled_adsorption_data.csv` (33,226 rows) |
| `classify_entries.py` | Add quality flags: HAS_POLYMER, HAS_MOLECULE, HAS_WATER_PH, HAS_CONCENTRATION, HAS_CAPACITY | `compiled_adsorption_data.csv` | `classified_adsorption_data.csv` |
| `filter_for_bioinformatics.py` | Filter to polymer+molecule rows, deduplicate, partial SMILES lookup | `classified_adsorption_data.csv` | `ready_for_bioinformatics.csv` (1,347 rows, deprecated) |

## Phase 3: SMILES / PSMILES Resolution

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `resolve_smiles.py` | Resolve drug SMILES via hardcoded dict + PubChem REST API + metal/ion patterns. No AI used. | `classified_adsorption_data.csv` | `output/drug_smiles.json` (102/125 resolved: 39 dict + 54 PubChem + 9 metal) |
| `resolve_polymer_batch.py` | Resolve polymer PSMILES for a partition of papers. One session per paper (no context pollution). Run N terminals in parallel with `--total N --part M`. | `classified_adsorption_data.csv` | `output/polymer_psmiles_part*.json` |
| `resolve_polymer_batch_orchestrator.py` | Spawn all 5 parts at once in separate terminals. Cleans old part files, checks server, launches everything. | — | — |
| `merge_polymer_results.py` | Merge all part files into one. | `output/polymer_psmiles_part*.json` | `output/polymer_psmiles.json` |

**Drug SMILES strategy** (deterministic, no AI):
1. Hardcoded dict — covers pharmaceuticals (aspirin, ibuprofen, tetracycline, etc.) and common dyes (methylene blue, congo red, etc.)
2. PubChem REST API — queries `/rest/pug/compound/name/{name}/property/ConnectivitySMILES`
3. Metal/ion regex patterns — `Cu(II)` → `[Cu+2]`, `Cr(VI)` → `[Cr]`, etc.
4. If PubChem has no result, the name is likely not a valid molecule — row is dropped

**Polymer PSMILES strategy** (parallel AI + web search, per-paper sessions):
- Start `opencode serve` once on port 4092 (`opencode-serve-polymers/opencode.json`: WebFetch only, no skills)
- Run `resolve_polymer_batch.py --total 5 --part M` in N separate terminals (recommended: 5)
- Each terminal handles ~20 papers, each with a **fresh session** — no context pollution
- After all finish, run `merge_polymer_results.py` to combine
- Resume-safe: re-running the same command skips already-done papers
- The DeepSeek V4 Flash reasoning model was unsuitable for this task (no web search, all tokens wasted on reasoning)`

## Phase 4: Training Dataset Construction

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `build_training_dataset.py` | Filter all5-valid rows (HAS_POLYMER=yes, HAS_MOLECULE=yes, all 3 numeric fields non-NaN), apply SMILES/PSMILES mappings, deduplicate, split by model, add KIMI_MATCHED flag | `classified_adsorption_data.csv` + `output/drug_smiles.json` + `output/polymer_psmiles.json` | `output/training_dataset_deepseek.csv` (252 rows), `output/training_dataset_kimi.csv` (123 rows), `output/training_dataset_gemma4_text.csv` (0 rows), `output/training_dataset_gemma4_image.csv` (43 rows), `output/training_dataset.csv` (321 rows) |
| `match_model_datasets.py` | Cross-model matching between DeepSeek and Kimi datasets. 5-field matching (POLYMER_PSMILES, DRUG_SMILES, WATER_PH, CONCENTRATION, CAPACITY) with 10% numeric tolerance, greedy assignment. Flags matched rows in DeepSeek CSV and outputs a gold-standard matched set. | `output/training_dataset_deepseek.csv` + `output/training_dataset_kimi.csv` | `output/training_dataset_matched_deepseek_kimi.csv` (94 rows, both models agree). Updates `training_dataset_deepseek.csv` with KIMI_MATCHED column. |

## Phase 5: Analysis & Review

| Script | Purpose |
|--------|---------|
| `select_for_review.py` | Select papers for re-analysis: `--dense N`, `--diverse N`, `--complete N`, `--overlap`, supports `all` |
| `reanalyze_papers.sh` | Re-analyze selected papers with a different Go model (requires model argument, e.g., `kimi-k2.6`, `mimo-v2.5`) |
| `compare_models.py` | Compare two model output directories with 5-field matching (10% numeric tolerance). Usage: `--new review_kimi-k2_6` |
| `detect_conflicts.py` | Find papers analyzed by 2+ models where the extracted data differs significantly |
| `list_good_papers.py` | Rank papers by data quality, export CSV for re-analysis |

## Pipeline Execution Order

```bash
# 1. Collect data
bash scripts/download_papers.sh
bash scripts/analyze_deepseek.sh

# 2. Compile and classify
pixi run python scripts/compile_results.py
pixi run python scripts/classify_entries.py

# 3. Resolve chemical structures
pixi run python scripts/resolve_smiles.py

# Polymer PSMILES (parallel, 5 terminals recommended):
# Terminal 0: cd opencode-serve-polymers && opencode serve --port 4092 --hostname 127.0.0.1
# Terminal 1: pixi run python scripts/resolve_polymer_batch.py --total 5 --part 0
# Terminal 2: pixi run python scripts/resolve_polymer_batch.py --total 5 --part 1
# Terminal 3: pixi run python scripts/resolve_polymer_batch.py --total 5 --part 2
# Terminal 4: pixi run python scripts/resolve_polymer_batch.py --total 5 --part 3
# Terminal 5: pixi run python scripts/resolve_polymer_batch.py --total 5 --part 4
pixi run python scripts/merge_polymer_results.py

# 4. Build training datasets
pixi run python scripts/build_training_dataset.py
pixi run python scripts/match_model_datasets.py

# (Optional) Re-analysis with another model
pixi run python scripts/select_for_review.py --complete all
bash scripts/reanalyze_papers.sh mimo-v2.5
pixi run python scripts/compare_models.py --new review_mimo-v2_5
```

## Output Files Quick Reference

All generated datasets live in `output/`:

| File | Rows | Quality tier |
|------|------|--------------|
| `training_dataset_deepseek.csv` | 252 | Primary — DeepSeek-only, clean SMILES/PSMILES |
| `training_dataset_kimi.csv` | 123 | Kimi-only comparison |
| `training_dataset_gemma4_image.csv` | 43 | Gemma4 (pdf2image) — lower quality, model comparison |
| `training_dataset_gemma4_text.csv` | 0 | Gemma4 (pdf2text) — no data extracted |
| `training_dataset.csv` | 321 | All models combined (deduplicated) |
| `training_dataset_matched_deepseek_kimi.csv` | 94 | Gold standard — both models agree |
