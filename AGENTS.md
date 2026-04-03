# AGENTS.md - Development Guidelines for lele-paper-scraper

## 1. Build, Lint, and Test Commands

### Python Environment Setup
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline
```bash
# Phase 1: Extract references using Grobid
python extract_refs.py

# Phase 2: Download PDFs via OpenAlex/Semantic Scholar
python download_pdfs.py

# Phase 3: Process PDFs with Marker and Ollama
python batch_process.py

# Run with Docker for Grobid
docker run -t --rm -p 8070:8070 lfoppiano/grobid:latest
```

### Testing
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_file.py

# Run a single test function
pytest tests/test_file.py::test_function_name

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_pattern"
```

### Linting and Code Quality
```bash
# Run ruff linter
ruff check .

# Run ruff with auto-fix
ruff check --fix .

# Format with ruff
ruff format .

# Run mypy type checker
mypy .
```

### Pre-commit Hooks (if configured)
```bash
# Install pre-commit
pip install pre-commit
pre-commit install
```

---

## 2. Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Keep functions small and focused (single responsibility)
- Use descriptive names for variables, functions, and classes
- Add type hints to all function signatures
- Document complex logic with docstrings

### Import Organization
Organize imports in the following order (separate with blank lines):
1. Standard library imports (`os`, `sys`, `json`, etc.)
2. Third-party imports (`requests`, `pandas`, etc.)
3. Local application imports (project modules)

```python
# Good import order
import os
import json
from typing import List, Optional, Dict

import requests
from dotenv import load_dotenv

from . import utils
from .models import Paper
```

### Formatting
- Maximum line length: 100 characters (configurable)
- Use 4 spaces for indentation (no tabs)
- Add trailing commas in multi-line imports
- Use f-strings for string formatting (preferred over `.format()` or `%`)
- Use `Black` or `ruff format` for automatic formatting

### Type Hints
- Always include return types for functions
- Use `Optional[X]` instead of `X | None` for Python < 3.10 compatibility
- Use `List[X]`, `Dict[K, V]` from `typing` module
- Prefer explicit types over `Any`

```python
# Good
def process_paper(paper_id: str, options: Optional[Dict[str, str]] = None) -> List[str]:
    ...

# Avoid
def process_paper(paper_id, options=None):  # No types
    ...
```

### Naming Conventions
- **Variables/Functions**: `snake_case` (e.g., `download_pdf`, `paper_count`)
- **Classes**: `PascalCase` (e.g., `PaperDownloader`, `ReferenceExtractor`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private methods**: prefix with underscore (e.g., `_parse_response`)
- **Module names**: `snake_case` (e.g., `extract_refs.py`)

### Error Handling
- Use specific exception types rather than catching `Exception`
- Log errors before re-raising or handling
- Use context managers (`with`) for resource management
- Provide meaningful error messages

```python
# Good
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.RequestException as e:
    logger.error(f"Failed to fetch {url}: {e}")
    raise PaperDownloadError(f"Could not download paper: {e}") from e

# Avoid bare except or catching too broad exceptions
```

### Async Code
- Use `asyncio` for I/O-bound operations
- Use `aiohttp` for async HTTP requests
- Properly handle cleanup with `async with`
- Add type hints for async functions

```python
async def fetch_paper(self, doi: str) -> Optional[bytes]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()
```

### Configuration
- Use environment variables for secrets and API keys
- Use `.env` files for local development (add to `.gitignore`)
- Use `python-dotenv` for loading environment variables
- Never commit API keys or secrets to version control

```python
from dotenv import load_dotenv

load_dotenv()  # Load .env file at startup

API_KEY = os.getenv("OPENALEX_API_KEY")
```

### Testing Guidelines
- Use `pytest` as the testing framework
- Name test files `test_*.py` or `*_test.py`
- Use descriptive test names that explain what is being tested
- Use fixtures for reusable test data
- Mock external API calls and file I/O
- Aim for high test coverage on critical paths

```python
def test_download_pdf_retries_on_failure():
    """Test that download retries on transient HTTP errors."""
    with mock.patch("requests.get") as mock_get:
        mock_get.side_effect = [requests.Timeout, MockResponse()]
        result = download_pdf("10.1234/test")
        assert result is not None
```

### Documentation
- Use docstrings for all public classes and functions
- Follow Google or NumPy docstring format
- Document parameters, return values, and exceptions
- Keep README.md updated with new features

```python
def extract_references(pdf_path: str) -> List[Reference]:
    """Extract references from a PDF using GROBID.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Reference objects extracted from the PDF.

    Raises:
        GROBIDError: If GROBID service is unavailable.
        PDFParseError: If PDF cannot be read.
    """
```

### File Organization
```
project/
├── src/                   # Source code (optional)
│   ├── __init__.py
│   └── modules/
├── tests/                 # Test files
│   ├── __init__.py
│   └── test_*.py
├── scripts/               # Executable scripts
├── config/                # Configuration files
├── Downloaded_Papers/     # Runtime data
├── Response_1/            # Output directory
├── Seed_Papers/           # Input directory
├── pyproject.toml        # Project configuration
├── .env                   # Local environment (gitignored)
└── AGENTS.md             # This file
```

---

## 3. Project-Specific Notes

### GROBID Integration
- Runs locally via Docker on port 8070
- Use `/api/processReferences` endpoint for reference extraction
- Handle connection errors gracefully (GROBID may be slow to start)

### API Rate Limiting
- OpenAlex: 100 requests/second (public), 10/second (no auth)
- Semantic Scholar: Lower limits, use caching
- Implement exponential backoff for retries

### LLM Processing
- Uses Ollama for local inference
- Models with large context windows recommended (mistral-nemo, llama3)
- Monitor VRAM usage when processing long documents
- Cache parsed PDFs to avoid re-processing

### PDF Parsing
- Primary: Marker (high fidelity for academic papers)
- Alternative: MinerU
- Handle multi-column layouts and mathematical equations

### Version Control
- Add `__pycache__/`, `*.pyc`, `.env`, `venv/`, `Downloaded_Papers/`, `Response_1/` to `.gitignore`
- Commit regularly with clear, descriptive messages
- Use feature branches for new functionality