# AGENTS.md - Paper Scraper

## Quick Commands

```bash
# Extract references from seed PDFs (requires Grobid on localhost:8070)
pixi run extract_refs

# Download papers from OpenAlex
pixi run download_papers

# Analyze with Ollama (requires Ollama running)
pixi run analyze

# Analyze with DeepSeek V4 Flash via OpenCode Go (no GPU)
bash scripts/analyze_deepseek.sh

# Run tests (slow tests skipped by default)
pixi run pytest

# Run DeepSeek Go tests (requires OPENCODE_GO_KEY in ../.env)
pixi run pytest -o "addopts=" -m requires_opencode_go_key
```

## Prerequisites

- **Grobid**: `docker run --rm -p 8070:8070 grobid/grobid:0.9.0-full`
- **Ollama**: `ollama serve` (for local GPU analysis)
- **OpenCode Go**: Subscribe at opencode.ai/go, add `OPENCODE_GO_KEY` to `../.env`
- **API Key**: `PYALEX_API_KEY=<key>` in `../.env` (openalex.org/settings/api)

## Directory Structure

| Path | Purpose |
|------|---------|
| `SEED_PAPERS/` | Input PDFs for extraction |
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` | Downloaded PDFs |
| `OUTPUT_DIR/extracted_references.json` | Extracted references |
| `gemma4_26b-pdf2text-respones/` | Ollama text analysis (UNISI) |
| `gemma4_26b-pdf2image-respones/` | Ollama image analysis (UNISI) |
| `opencode_go_deepseek_v4_flash_max_pdf2text_responses/` | DeepSeek analysis (local) |

## Key Files

| File | Purpose |
|------|---------|
| `paper_scraper/main.py` | Unified pipeline (extract + download + analyze) |
| `paper_scraper/Ollama/Options.py` | LLM options (model, base_url, api_key_env, system_prompt_file) |
| `paper_scraper/Ollama/complete.py` | API caller (supports Ollama + OpenAI-compatible) |
| `paper_scraper/OpenAlex/get_dois_from_filter.py` | Search + download config |
| `scripts/analyze_deepseek.sh` | Local analysis via OpenCode Go |
| `scripts/remote_analysis.sh` | Server analysis script |
| `scripts/check_analysis.sh` | Check remote analysis log |
| `scripts/test_remote.sh` | Fast remote test on N papers |

## Main Pipeline (`main.py`)

### Config Options

```python
from paper_scraper.main import main, Config
from paper_scraper.OpenAlex import get_dois_from_filter, get_reference_dois
from paper_scraper.Ollama import Options as OllamaOptions

# Minimal: uses all defaults
config = Config()

# Download with targeted search
config = Config(
    search_filter=get_dois_from_filter.SearchFilter(
        topics="T10016",
        keywords="pharmaceutical && adsorption && polymer",
        max_papers=1000,
        open_access_only=False,  # False = try all papers, True = OA only
    ),
)

# Analyze with DeepSeek V4 Flash (local, no GPU)
config = Config(
    questions=["Extract adsorption data as CSV: ..."],
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

# Analyze with Ollama (requires Ollama running)
config = Config(
    questions=["What are the main findings?"],
    ollama_opts=OllamaOptions(model="gemma4:e4b"),
    max_chunks=1,
)
```

### OllamaOptions Fields

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `tinyllama` | Model name |
| `base_url` | `http://localhost:11434` | API base URL |
| `completion_path` | `/api/chat` | Endpoint path. Use `/chat/completions` for OpenAI-compatible |
| `api_key_env` | `""` | Env var name for API key. Empty = Ollama mode (no auth) |
| `system_prompt_file` | `""` | Path to file with system prompt text |
| `system_prompt` | `"You are a helpful..."` | System prompt text |
| `temperature` | `1.0` | LLM temperature |
| `max_context_tokens` | `256` | Context window size |
| `handle_pdfs` | `"pdf2text"` | `"pdf2text"` or `"pdf2image"` |

### Pipeline Flow

1. Extract references from seed PDFs (if `extract_refs_from_seed=True`)
2. Get DOIs from search filter (topic + keywords → OpenAlex)
3. Download papers
4. Extract references from downloaded papers (if `extract_refs_from_output=True`)
5. Download references of downloaded papers
6. Analyze with LLM (if `questions` provided)

## Package Organization

| Package | Purpose |
|---------|---------|
| `Grobid/` | PDF reference extraction via localhost:8070 |
| `OpenAlex/` | Paper downloads via OpenAlex API |
| `Ollama/` | LLM analysis (Ollama or OpenAI-compatible APIs) |

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Top-level package | snake_case | `paper_scraper/` |
| Subpackages | PascalCase | `OpenAlex/`, `Grobid/` |
| Modules/Functions | snake_case | `extract_refs.py`, `complete()` |

## Testing

- Tests in `paper_scraper/`
- Default skips: `verbose`, `todo`, `above10s`, `unreliable`, `infinite`, `requires_grobid`, `requires_ollama`, `requires_opencode_go_key`
- Run all: `pixi run pytest -o "addopts="`
- Run DeepSeek Go tests: `pixi run pytest -o "addopts=" -m requires_opencode_go_key`
