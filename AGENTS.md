# AGENTS.md - Paper Scraper

## Quick Commands

```bash
# Extract references from seed PDFs (requires Grobid on localhost:8070)
pixi run extract_refs

# Download papers from OpenAlex
pixi run download_papers

# Analyze downloaded papers with Ollama (requires Ollama running)
pixi run analyze

# Run tests (slow tests skipped by default)
pixi run pytest

# Run specific test (include slow tests)
pixi run pytest paper_scraper/SomeModule.py::test_usage -o "addopts="
```

## Prerequisites

- **Grobid**: `podman run --rm -p 8070:8070 grobid/grobid:0.8.2-crf`
- **Ollama**: `ollama serve` (for LLM analysis)
- **API Key**: `.env` file in **parent directory** with `PYALEX_API_KEY=<key>` (openalex.org/settings/api)

## Directory Structure

| Path | Purpose |
|------|---------|
| `PAPERS/SEED/` | Input PDFs for extraction |
| `OUTPUT_DIR/` | Default output directory |
| `OUTPUT_DIR/DOWNLOADED_PAPERS/` | Downloaded PDFs |
| `OUTPUT_DIR/QUESTIONS/` | Question files (q1.md, q2.md, ...) |
| `OUTPUT_DIR/RESPONSES/` | Ollama responses |
| `OUTPUT_DIR/extracted_references.json` | Extracted references |

## Key Files

| File | Purpose |
|------|---------|
| `paper_scraper/main.py` | Unified pipeline (extract + download + analyze) |
| `paper_scraper/extract_refs.py` | Standalone reference extraction |
| `paper_scraper/download_papers.py` | Standalone paper downloader |
| `paper_scraper/__global__.py` | Constants (SEED_PAPERS_DIR, OUTPUT_DIR, GROBID_URL) |

## Main Pipeline (`main.py`)

### Config Options

```python
from paper_scraper.main import main, Config
from paper_scraper.OpenAlex import get_dois_from_filter, get_reference_dois
from paper_scraper.Ollama import Options as OllamaOptions

# Minimal: uses all defaults
config = Config()

# Extract refs from specific PDFs only
config = Config(
    seed_papers=[path1, path2],  # list[Path], single Path, or None (auto-discover)
    extract_refs_from_seed=True,
    extract_refs_from_output=False,
)

# Download papers by topic
config = Config(
    download_filter=get_dois_from_filter.Filter(
        topics=["T11948"],  # or ["C185592680"] for concepts
        year_min=2020,
        year_max=2024,
        max_papers=100,
    ),
)

# Download reference papers recursively
config = Config(
    download_reference_opts=get_reference_dois.Options(depth=2),
)

# Analyze with Ollama (requires Ollama running on localhost:11434)
config = Config(
    questions=["What are the main findings?", "What methods were used?"],  # list[str] or Path to .txt
    ollama_opts=OllamaOptions(model="gemma4:32b"),
    max_chunks=1,  # Testing mode: only first chunk. Set higher for full analysis.
)

# Parallel processing
config = Config(batch_size=4)

# Custom output directory
config = Config(
    output_dir=Path("custom/output"),  # Creates subdirs: DOWNLOADED_PAPERS/, QUESTIONS/, RESPONSES/
)
```

### Pipeline Flow

1. Extract references from seed PDFs (if `extract_refs_from_seed=True`)
2. Download papers matching filter (if `topics` provided)
3. Download reference DOIs from seed papers (if DOIs found)
4. Extract references from downloaded papers (if `extract_refs_from_output=True`)
5. Download references of downloaded papers
6. Analyze with Ollama (if `questions` provided)

### Ollama Output Structure

```
OUTPUT_DIR/
├── DOWNLOADED_PAPERS/
│   ├── paper1.pdf
│   └── paper2.pdf
├── QUESTIONS/
│   ├── q1.md  # "What are the main findings?"
│   └── q2.md  # "What methods were used?"
└── RESPONSES/
    └── paper1/
        ├── q1.md  # Question + response
        └── q2.md
```

## Package Organization

| Package | Purpose |
|---------|---------|
| `Grobid/` | PDF reference extraction via localhost:8070 |
| `OpenAlex/` | Paper downloads via OpenAlex API |
| `Ollama/` | Local LLM analysis (requires `ollama serve`) |

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Top-level package | snake_case | `paper_scraper/` |
| Subpackages | PascalCase | `OpenAlex/`, `Grobid/` |
| Modules/Functions | snake_case | `extract_refs.py`, `complete()` |

## Import System

- `paper_scraper/__init__.py`: must contain `new_import_system.install(__file__)`
- All other `__init__.py`: must be **EMPTY**

## Error Classes

- `Ollama/Error/` - ConnectionRefused, ConnectionTimeout
- `Grobid/Error/` - ConnectionRefused, ConnectionTimeout, UnexpectedStatus

## Testing

- Tests in `paper_scraper/`
- Default skips: `verbose`, `todo`, `above10s`, `unreliable`, `infinite`
- Run all: `pixi run pytest -o "addopts="`
