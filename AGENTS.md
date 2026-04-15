# AGENTS.md - Paper Scraper

## Quick Commands

```bash
# Extract references from seed PDFs (requires Grobid running on localhost:8070)
pixi run extract_refs

# Download papers from OpenAlex using DOIs
pixi run download_papers

# Run tests
pixi run pytest
```

## Directory Structure

- `PAPERS/SEED/` - Input PDFs
- `PAPERS/DOWNLOADED/` - Downloaded PDFs
- `PAPERS/SEED/extracted_references.json` - Output from Grobid extraction
- `.env` - Parent dir contains `PYALEX_API_KEY` (get from openalex.org/settings/api)

## Key Files

- `paper_scraper/extract_refs.py` - Entry point for reference extraction
- `paper_scraper/download_papers.py` - Entry point for downloading papers
- `paper_scraper/__global__.py` - Global constants (SEED_DIR, DOWNLOADED_DIR, etc.)

## Import System

- Top-level `__init__.py`: must contain `new_import_system.install(__file__)`
- All other `__init__.py`: must be EMPTY

## Code Organization

- One file = one class or function + one or more test functions

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Top-level package | snake_case | `paper_scraper/` |
| Subpackages | PascalCase | `OpenAlex/`, `Grobid/`, `Ollama/` |
| Modules/Functions | snake_case | `extract_refs.py`, `complete()` |

## Error Classes

Each subpackage has its own `Error/` directory:
- `Ollama/Error/` - ConnectionRefused, ConnectionTimeout
- `Grobid/Error/` - ConnectionRefused, ConnectionTimeout, UnexpectedStatus, Error enum

## Testing

Tests are in `paper_scraper/`. Run specific test:
```bash
pixi run pytest paper_scraper/SomeModule.py::test_usage -o "addopts="
```

Skip slow tests (marked `above10s`): default behavior skips them automatically.
