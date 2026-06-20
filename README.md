# Paper Scraper — Automated Literature Review Pipeline

Automated snowballing literature-review agent: extract references from seed PDFs,
download papers via OpenAlex, analyze with local or cloud LLMs (Ollama, OpenCode Go),
resolve chemical structures via PubChem and web search, and compile into a clean
CSV ready for ML training.

## Architecture

```
SEED_PAPERS/  →  Grobid  →  DOIs  →  OpenAlex  →  PDFs  →  LLM Analysis  →  Raw CSV
                                                                                │
                                                                                ▼
                                                                        Drug SMILES:
                                                                        dict + PubChem
                                                                        + metal patterns
                                                                                │
                                                                                ▼
                                                                        Polymer PSMILES:
                                                                        opencode serve agent
                                                                        (WebFetch → PubChem
                                                                         Wikipedia, polymer DBs)
                                                                                │
                                                                                ▼
                                                                        training_dataset_deepseek.csv
                                                                        training_dataset_matched.csv
```

| Phase | Name | Tool | Output |
|-------|------|------|--------|
| 1 | Citation Extraction | Grobid (localhost:8070) | Extracted DOIs |
| 2 | Crawl & Download | OpenAlex API (pyalex) | PDFs in `OUTPUT_DIR/DOWNLOADED_PAPERS/` |
| 3a | AI Analysis (GPU server) | Ollama + gemma4:26b | `gemma4_26b-*-respones/` |
| 3b | AI Analysis (local, no GPU) | OpenCode Go → any model | `review_*/` or custom dirs |
| 4 | Data Compilation | `compile_results.py` | `compiled_adsorption_data.csv` |
| 5 | Quality Filtering | `classify_entries.py` | `classified_adsorption_data.csv` |
| 6a | Drug SMILES Resolution | `resolve_smiles.py` (dict + PubChem + metal) | `output/drug_smiles.json` |
| 6b | Polymer PSMILES Resolution | `resolve_polymer_psmiles_via_opencode.py` (web search) | `output/polymer_psmiles.json` |
| 7 | Build Training Datasets | `build_training_dataset.py` + `match_model_datasets.py` | `output/training_dataset_*.csv` |

## Quick Start

### Prerequisites

- **Python 3.11+** with **pixi** (`pipx install pixi`)
- **OpenCode**: `curl -fsSL https://opencode.ai/install | bash` (for polymer PSMILES resolution)
- **Grobid**: `docker run --rm -p 8070:8070 grobid/grobid:0.9.0-full` (for reference extraction)
- **API Key**: Create `.env` in the **parent directory** with:
  ```
  PYALEX_API_KEY=<your_openalex_key>   # openalex.org/settings/api
  OPENCODE_GO_KEY=<your_go_key>        # opencode.ai/go (optional, for cloud analysis)
  ```

### Full pipeline

```bash
# 1. Download papers
bash scripts/download_papers.sh

# 2. Analyze with DeepSeek V4 Flash (local, no GPU)
bash scripts/analyze_deepseek.sh

# 3. Compile results
pixi run python scripts/compile_results.py
pixi run python scripts/classify_entries.py

# 4. Resolve SMILES/PSMILES
pixi run python scripts/resolve_smiles.py
pixi run python scripts/resolve_polymer_psmiles_via_opencode.py

# 5. Build training datasets
pixi run python scripts/build_training_dataset.py
pixi run python scripts/match_model_datasets.py
```

## Pipeline Data Flow

```
classified_adsorption_data.csv (20,807 rows, 277 papers)
        │
        ▼ filter: HAS_POLYMER=yes + HAS_MOLECULE=yes + all 5 fields
        │
  ┌─────┴─────┐
  │  977 rows  │  (131 papers)
  └─────┬─────┘
        │
  ┌─────┴──────────────────────────────────┐
  │  DRUG SMILES:                          │  resolve_smiles.py
  │    39 hardcoded dict                   │
  │    54 PubChem REST API                 │
  │     9 metal/ion patterns               │
  │   ─────────────────────                │
  │  102/125 resolved (82%)                │
  │                                        │
  │  POLYMER PSMILES:                      │  resolve_polymer_psmiles_via_opencode.py
  │    opencode serve agent on port 4092   │
  │    WebFetch → PubChem, Wikipedia,      │
  │    polymer databases                   │
  │    One API call per paper DOI          │
  └─────┬──────────────────────────────────┘
        │
        ▼ join + drop unresolved
        │
  ┌─────┴──────────────────────────────────────────┐
  │  training_dataset_deepseek.csv   379 rows      │  build_training_dataset.py
  │  training_dataset_kimi.csv       243 rows      │
  │  training_dataset.csv            469 rows      │
  │                                                 │  match_model_datasets.py
  │  training_dataset_matched.csv    205 rows      │  (5-field, 10% tolerance, greedy)
  └─────────────────────────────────────────────────┘
```

## Scripts Reference

See `scripts/README.md` for a complete, organized reference.

### Key scripts

| Script | Description |
|--------|-------------|
| `scripts/resolve_smiles.py` | Drug SMILES via dict + PubChem REST API + metal patterns. No AI. |
| `scripts/resolve_polymer_psmiles_via_opencode.py` | Polymer PSMILES via local `opencode serve` agent with WebFetch internet search. |
| `scripts/build_training_dataset.py` | Filter all5-valid rows, apply SMILES/PSMILES, deduplicate, split by model. |
| `scripts/match_model_datasets.py` | Cross-model matching (5-field, 10% tolerance, greedy assignment). |

## Polymer PSMILES Resolution (parallel, per-paper sessions)

Polymer SMILES cannot be obtained from standard chemical databases (PubChem only has
small-molecule SMILES, not polymer repeating-unit SMILES). The DeepSeek V4 Flash
reasoning model (used via OpenCode Go API) is unsuitable because it cannot search
the web and spends its entire token budget on reasoning without producing output.

Instead, run `opencode serve` on port 4092 with minimal config (WebFetch only,
no skills). The agent searches PubChem/Wikipedia/polymer databases in real time.

**Each paper gets its own session** — no context pollution between papers.
Paper #20 gets same quality as paper #1 because the agent starts fresh.

Configuration at `opencode-serve-polymers/opencode.json`:

```json
{
  "permission": {
    "tool": {
      "WebFetch": "allow"
    },
    "skill": {
      "*": "deny"
    }
  }
}
```

### Workflow

**1. Start the server** (keep this terminal open):
```bash
cd opencode-serve-polymers
opencode serve --port 4092 --hostname 127.0.0.1
```

**2. In another terminal, spawn all 5 parallel workers:**
```bash
pixi run python scripts/resolve_polymer_batch_orchestrator.py
```

Or manually launch each partition in its own terminal:
```bash
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 0
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 1
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 2
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 3
pixi run python scripts/resolve_polymer_batch.py --total 5 --part 4
```

**3. After all finish:**
```bash
pixi run python scripts/merge_polymer_results.py
```
```

Each terminal handles ~20 papers (~1.5 hours). Resume-safe: if a terminal crashes,
re-run the same command and it skips already-done papers.

## SMILES Resolution Strategy (Drugs)

Drug SMILES are resolved WITHOUT AI — only deterministic lookups:

| Stage | Method | Resolved |
|-------|--------|----------|
| 1 | Hardcoded SMILES_DICT (pharmaceuticals, common dyes) | 39 |
| 2 | PubChem REST API (`/rest/pug/compound/name/{name}/property/ConnectivitySMILES`) | 54 |
| 3 | Metal/ion regex patterns (`Cu(II)` → `[Cu+2]`, `Cr(VI)` → `[Cr]`, etc.) | 9 |
| **Total** | | **102/125 (82%)** |

If PubChem does not have a molecule's SMILES, it is likely not a valid molecule
or the name is incorrect. Unresolved drugs (23) are dropped from the final dataset.

## Output Files

| File | Generated by | Rows/Size | Description |
|------|-------------|-----------|-------------|
| `compiled_adsorption_data.csv` | compile_results.py | 20,807 rows | Raw merge of all model responses |
| `classified_adsorption_data.csv` | classify_entries.py | 20,807 rows | Adds HAS_* quality flags |
| `ready_for_bioinformatics.csv` | filter_for_bioinformatics.py | 1,347 rows | (Deprecated) Pre-SMILES filtering |
| `output/drug_smiles.json` | resolve_smiles.py | 125 entries | Drug → SMILES mapping |
| `output/polymer_psmiles.json` | resolve_polymer_batch.py + merge_polymer_results.py | ~210 entries | Polymer → PSMILES mapping |
| `output/training_dataset_deepseek.csv` | build_training_dataset.py | 379 rows | DeepSeek-only, includes KIMI_MATCHED flag |
| `output/training_dataset_kimi.csv` | build_training_dataset.py | 243 rows | Kimi-only |
| `output/training_dataset_matched.csv` | match_model_datasets.py | 205 rows | Gold standard: both models agree |
| `output/training_dataset.csv` | build_training_dataset.py | 469 rows | All models combined |
| `output/resolve_smiles.log` | resolve_smiles.py | — | Full resolution log |
| `model_comparison.csv` | compare_models.py | ~120 rows | DeepSeek vs Kimi per-paper agreement |

## Cross-Model Validation

### Comparison workflow

```bash
# 1. Select papers
pixi run python scripts/select_for_review.py --complete 30

# 2. Re-analyze with another model
bash scripts/reanalyze_papers.sh mimo-v2.5

# 3. Compare results (5-field matching, 10% tolerance)
pixi run python scripts/compare_models.py --new review_mimo-v2_5
```

### Agreement (PSMILES-matched)

| Model pair | Common papers | Matched rows | Agreement |
|-----------|--------------|-------------|-----------|
| DeepSeek V4 Flash vs Kimi K2.6 (SMILES-matched) | 57 | 205 / 469 | 49% |

The 49% agreement (vs 24% with raw names) reflects the improvement from matching
on resolved PSMILES/SMILES rather than free-text polymer names. The 205 matched
rows in `training_dataset_matched.csv` are the gold standard — both models
independently extracted the same data point within 10% tolerance.

## OllamaOptions fields

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `tinyllama` | Model name. Supported: `gemma4:26b`, `deepseek-v4-flash`, `kimi-k2.6`, etc. |
| `base_url` | `http://localhost:11434` | API base URL |
| `completion_path` | `/api/chat` | Endpoint path. Use `/chat/completions` for OpenAI-compatible |
| `api_key_env` | `""` | Env var name. Set to `OPENCODE_GO_KEY` for Go |
| `system_prompt_file` | `""` | Path to system prompt file |
| `temperature` | `1.0` | LLM temperature |
| `max_context_tokens` | `256` | Context window (32768 for Go models) |
| `handle_pdfs` | `"pdf2text"` | `"pdf2text"` or `"pdf2image"` |

## Search Configuration

```python
SearchFilter(
    topics="T10016",                        # OpenAlex topic ID
    keywords="pharmaceutical && adsorption && polymer",
    max_papers=5000,
    open_access_only=False,
    year_min=2020,
    year_max=2024,
)
```

Topic IDs: `T10016` (Adsorption), `T11781` (Wastewater Treatment), `T14252` (Water Treatment).
Operators: `&&` (AND), `||` (OR), `!` (NOT), parentheses.

## Testing

```bash
pixi run pytest                          # Default (skip slow/external)
pixi run pytest -o "addopts="            # All including slow
pixi run pytest -o "addopts=" -m requires_opencode_go_key  # DeepSeek Go tests
```

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
├── output/                         # Generated datasets
│   ├── drug_smiles.json
│   ├── polymer_psmiles.json
│   ├── training_dataset_deepseek.csv
│   ├── training_dataset_kimi.csv
│   ├── training_dataset_matched.csv
│   ├── training_dataset.csv
│   └── resolve_smiles.log
├── opencode-serve-polymers/        # opencode serve config
│   └── opencode.json
├── paper_scraper/                  # Python package
│   ├── OpenAlex/                   # Paper search + download
│   ├── Ollama/                     # LLM API wrapper
│   ├── Grobid/                     # Reference extraction
│   ├── Utils/                      # PDF utilities
│   ├── pipeline/                   # Pipeline orchestration
│   └── Secrets/                    # API key loading
├── scripts/
│   ├── resolve_smiles.py           # Drug SMILES resolution
│   ├── resolve_polymer_psmiles_via_opencode.py  # Polymer PSMILES via serve
│   ├── build_training_dataset.py   # Filter + join + split
│   ├── match_model_datasets.py     # Cross-model matching
│   └── ... (see scripts/README.md)
├── compiled_adsorption_data.csv    # ~20K rows
├── classified_adsorption_data.csv  # With quality flags
├── ready_for_bioinformatics.csv    # ~1.3K rows (deprecated)
├── model_comparison.csv            # DeepSeek vs Kimi
└── pixi.toml                       # Dependencies
```

## Version

Current: v0.1.0
