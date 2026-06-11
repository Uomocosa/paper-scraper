---
name: project-orientation
description: Use when the user asks to run, continue, check status, or get oriented in the lele-paper-scraper literature-review project. Determines the current pipeline phase by inspecting the filesystem state, recommends the next command, and asks clarifying questions when the path is ambiguous. Works with the local (pixi) and remote (UNISI SSH) workflows.
---

# Project Orientation — lele-paper-scraper

## 1. Final Objective

Build a **fully automated snowballing literature-review agent** with 4 phases:

| Phase | Name | Tool | Status |
|-------|------|------|--------|
| 0 | Setup | — | Prerequisites check |
| 1 | Citation Extraction | Grobid (localhost:8070) | ✅ Implemented |
| 2 | Crawl & Download | OpenAlex API (pyalex) | ✅ Implemented (2 known bugs) |
| 3 | AI Analysis | Ollama (localhost:11434) | ✅ Implemented (1 known bug in pdf2image mode) |
| 4 | Smart Filter | Ollama structured output | ❌ Not implemented |

Deployment: **download on local low-end laptop → rsync to UNISI GPU server → analyze → sync results back**.

---

## 2. Phase Detection

Inspect these filesystem markers to determine where the project is:

| Marker | Phase | Condition |
|--------|-------|-----------|
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` is empty or doesn't exist | Phase 0–1 | No papers yet |
| `OUTPUT_DIR/extracted_references.json` exists | Phase 1 done | References extracted from seed PDFs |
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` has `*.pdf` files | Phase 2 done | Papers downloaded |
| `OUTPUT_DIR/RESPONSES/` has subdirectories with `*.md` | Phase 3 started | Analysis partially or fully complete |
| `OUTPUT_DIR/RESPONSES/` has entries for **every** PDF | Phase 3 done | All papers analyzed |
| `OUTPUT_DIR/RESPONSES/` has some but not all PDFs | Phase 3 partial | Analysis interrupted or still running |

**Procedure:**
1. Count PDFs: `Get-ChildItem -Path "OUTPUT_DIR/DOWNLOADED_PAPERS" -Filter "*.pdf"`
2. Count response dirs: `Get-ChildItem -Path "OUTPUT_DIR/RESPONSES" -Directory`
3. Read `OUTPUT_DIR/QUESTIONS/` for existing questions
4. If `OUTPUT_DIR/RESPONSES/` exists and is non-empty, check `test_rsync.sh --status` or `sync_results.sh --status` if remote

---

## 3. Run Instructions

### Local Execution (Windows, pixi)

```bash
# Phase 1 — Extract references from SEED_PAPERS/ (requires Grobid)
pixi run extract_references

# Phase 2 — Download papers from OpenAlex (requires API key in ../.env)
pixi run download_papers

# Phase 3 — Analyze with Ollama (requires ollama serve)
pixi run analyze

# Unified pipeline (all phases)
pixi run scrape
```

### Remote Execution (UNISI GPU server via WSL)

```bash
# Step 1: Download papers locally (already done)
bash scripts/download_papers.sh

# Step 2: rsync PDFs to UNISI server (requires OpenVPN)
bash scripts/sync_papers.sh

# Step 3: Start analysis on server in screen session
bash scripts/run_analysis.sh

# Step 4: Wait for completion and sync results back
bash scripts/sync_results.sh

# Check if analysis is still running
bash scripts/sync_results.sh --status
```

### Prerequisites

| Requirement | For | How to check |
|-------------|-----|-------------|
| Grobid on :8070 | Phase 1 | `curl -s http://localhost:8070/api/isAlive` |
| OpenAlex API key | Phase 2 | Check `../.env` has `PYALEX_API_KEY=` |
| Ollama on :11434 | Phase 3 | `curl -s http://localhost:11434/api/tags` |
| OpenVPN to UNISI | Remote | Ping `mec-ai` or SSH test |
| SSH key to `maggiori@mec-ai` | Remote | `ssh maggiori@mec-ai "echo ok"` |
| pixi in WSL | Remote | `pixi --version` in WSL |

---

## 4. Decision Workflow

When the user says "continue", "what next", or similar:

1. **Run phase detection** (section 2).
2. **If Phase 0–1:** Ask if Grobid is running. Suggest `pixi run extract_references`.
3. **If Phase 2 done, Phase 3 not started:** Ask: *"Run analysis locally on this machine, or sync to UNISI server?"* Route accordingly.
4. **If Phase 3 partial:** Check if analysis was started via remote scripts. If yes, suggest `bash scripts/sync_results.sh --status`. If local, check `OUTPUT_DIR/RESPONSES/` and suggest `pixi run analyze` (it skips existing responses).
5. **If Phase 3 complete:** Report completion. Mention Phase 4 (Smart Filter) as the unimplemented next step.
6. **If any prerequisite is missing:** Report it clearly with the install/start command.

### Questions to ask when in doubt

- *"Are you on your local Windows machine or on the UNISI server?"*
- *"Is Grobid running on this machine?"*
- *"Is Ollama running? Which model do you want to use?"*
- *"Do you want to analyze locally (slower) or sync to UNISI and analyze there (faster, requires OpenVPN)?"*
- *"Do you have questions prepared, or should I check what's in OUTPUT_DIR/QUESTIONS/?"*
- *"Do you want to fix the known bugs first, or just run the pipeline as-is?"*

---

## 5. Known Bugs (at time of writing)

| Bug | File | Impact |
|-----|------|--------|
| Double download in `from_dois()` | `OpenAlex/get_reference_dois.py:37-43` | Every paper downloaded twice |
| `pdf2image` broken in pipeline | `pipeline/analyze.py:122` | Image chunks string-joined into garbage |
| Per-DOI API calls for filtering | `OpenAlex/get_dois_from_filter.py:437-466` | Very slow for 100+ DOIs |
| Typo `TEMP_DOWLOADED_PAPERS_DIR` | `__global__.py:18` | Missing 'n' in constant name |

See `KNOWN_BUGS.md` for full details.
