# AGENTS.md - Paper Scraper Project

## Overview

This repo contains a local scientific paper scraping pipeline. It extracts references from seed PDFs, downloads papers via OpenAlex API, and outputs to local directories.

---

## 1. Import System: new-import-system

### Installation in Top-Level `__init__.py`

```python
import new_import_system
new_import_system.install(__file__)
```

**Example:** `paper_scraper/__init__.py`
```python
import new_import_system
new_import_system.install(__file__)
```

### Import Rules

- **NEVER use relative imports** (e.g., `from .Module import ...` is forbidden)
- **Always use absolute imports** (e.g., `import paper_scraper`, `from paper_scraper.OpenAlex import download_papers_from_dois`)

### Empty `__init__.py` Files

All `__init__.py` files EXCEPT the top-level one must be **empty**:

```
paper_scraper/
├── __init__.py          # Contains new-import-system installation
├── OpenAlex/
│   ├── __init__.py      # EMPTY
│   ├── download_papers_from_dois.py
│   └── Result.py
├── Grobid/
│   ├── __init__.py      # EMPTY
│   └── extract_references_from_pdf.py
└── Utils/
    ├── __init__.py      # EMPTY
    └── extract_dois_from_json.py
```

---

## 2. Code Granularity & Organization

### Functions vs Dataclasses/Enums

- **Functions represent actions** — they perform operations, transformations, or computations (e.g., `filter_data`, `download_file`, `calculate_score`)
- **Dataclasses and enums represent data** — they hold structured information or define fixed sets of values (e.g., `Config`, `User`, `Status`)

This is the default paradigm. Use functions for stateless operations; use dataclasses/enums when you need to group related data fields.

### Dataclasses, Enums, and Functions

**Prefer dataclasses and enums for structured data**, but regular functions are also welcome at the package level. Not everything needs to be a class or enum — use functions for stateless operations or when they provide better clarity.

**Good:**
```python
from dataclasses import dataclass, field
from enum import IntEnum

@dataclass
class Config:
    csv_file: Path
    max_size: int = 100

class Status(IntEnum):
    UNKNOWN = -1
    INACTIVE = 0
    ACTIVE = 1

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['value'] > 0]
```

**Bad:**
```python
class Config:
    def __init__(self, csv_file, max_size=100):
        self.csv_file = csv_file
        self.max_size = max_size
```

### Subpackage Naming: PascalCase

All subpackage folders must follow **PascalCase** convention:

```
✅ OpenAlex/, Grobid/, Utils/, Error/
❌ openalex/, grobid/, utils/, error/
```

### Method Subpackages: `ClassNameMethod/`

When a dataclass needs methods, create a subpackage named `ClassNameMethod/` and implement methods there.

**Structure:**
```
paper_scraper/Module/
├── MyClass.py              # Dataclass definition
└── MyClassMethod/
    ├── __init__.py         # EMPTY
    ├── my_method.py        # Method implementation
    ├── another_method.py
    └── process_data.py
```

**Dataclass references methods via the subpackage:**

```python
# paper_scraper/Module/MyClass.py
from dataclasses import dataclass
import paper_scraper

@dataclass
class MyClass:
    data: pd.DataFrame
    config: Config
    
    def my_method(self, options=MyClassMethod.my_method.Options()):
        return MyClassMethod.my_method(self.data, options)
    
    def another_method(self, options=MyClassMethod.another_method.Options()):
        return MyClassMethod.another_method(self.data, options)
```

### Function Organization in Method Modules

Each method file follows this pattern:

```python
# paper_scraper/Module/MyClassMethod/my_method.py
from dataclasses import dataclass, field
import pandas as pd
import paper_scraper

@dataclass
class Options:
    option_a: str = "default_value"
    n_points: int = 2

def my_method(df: pd.DataFrame, options: Options = Options()) -> pd.DataFrame:
    # Implementation here
    return df

def test_my_method():
    from paper_scraper.__global__ import SEED_DIR
    df = pd.read_csv(DATA_CSV)
    df = my_method(df, Options(option_a="value"))
    assert len(df) > 0

def test_method_b():
    from paper_scraper.__global__ import SEED_DIR
    df = my_method(df, Options(method="method_b"))
    assert len(df) > 0
```

---

## 3. Testing Conventions

### `test_usage()` Function Pattern

Every module (function, dataclass, enum) must have at least one `test_usage()` function with **no arguments**:

```python
def test_usage():
    from paper_scraper.__global__ import SEED_DIR
    config = Config(csv_file=SEED_DIR)
    instance = MyClass(config)
    instance.my_method()
    logger.info(f"Data shape: {instance.data.shape}")
```

### Multiple Test Functions

When testing different aspects, use descriptive names:

```python
def test_method_a():
    pass

def test_method_b():
    pass

def test_complete_workflow():
    pass
```

### Pytest Markers

Use pytest markers for test categorization:

```python
import pytest

@pytest.mark.above10s
def test_long_running():
    """Test that requires more than 10 seconds."""
    pass

@pytest.mark.skip(reason="Needed once for specific debugging")
def test_debug_one_time():
    """Skip this test after one-time use."""
    pass

@pytest.mark.todo
def test_not_yet_implemented():
    """Test for feature not yet implemented."""
    pass

@pytest.mark.unreliable
def test_external_dependency():
    """Test that depends on external factors."""
    pass

@pytest.mark.verbose
def test_with_output():
    """Test that produces visible output."""
    pass
```

**Running specific tests:**
```bash
pixi run pytest -rFP -q -s paper_scraper/Module/MyClass.py::test_usage -o "addopts="
```

---

## 4. Global Constants: `__global__.py`

Use `__global__.py` files for constants and shared configuration:

```python
# paper_scraper/__global__.py
from pathlib import Path

THIS_FOLDER = Path(__file__).parent
HELPER_DIR = THIS_FOLDER / '__HELPER_DIR__'
PAPERS_DIR = REPO_DIR / 'PAPERS'
SEED_DIR = PAPERS_DIR / 'SEED'
DOWNLOADED_DIR = PAPERS_DIR / 'DOWNLOADED'

from joblib import Memory
CACHE_MEMORY = Memory(location=".cache_dir", verbose=0)
```

Each subpackage can have its own `__global__.py`:

```python
# paper_scraper/OpenAlex/__global__.py
from pathlib import Path

THIS_FOLDER = Path(__file__).parent
HELPER_DIR = THIS_FOLDER / '__HELPER_DIR__'
```

---

## 5. Code Style Rules

### No Comments (Unless Required)

Add comments only when absolutely necessary for understanding. Code should be self-documenting.

### No `if __name__ == "__main__"`

Never use `if __name__ == "__main__":` blocks. Use test functions instead.

### Logging with loguru

Use `loguru.logger` for logging:

```python
from loguru import logger

logger.debug(f"Processing {len(df)} rows")
logger.info("Operation completed successfully")
logger.warning("Missing data detected")
```

---

## 6. Directory Structure

```
paper_scraper/
├── __init__.py              # new-import-system installation
├── __global__.py            # Global constants
├── OpenAlex/
│   ├── __init__.py          # EMPTY
│   ├── __global__.py        # Module-specific constants
│   ├── download_papers_from_dois.py
│   └── Options.py
├── Grobid/
│   ├── __init__.py          # EMPTY
│   ├── extract_references_from_pdf.py
│   └── check_connection.py
├── Utils/
│   ├── __init__.py          # EMPTY
│   └── extract_dois_from_json.py
├── Error/
│   ├── __init__.py          # EMPTY
│   ├── GrobidConnectionTimeout.py
│   ├── GrobidConnectionRefused.py
│   └── GrobidUnexpectedStatus.py
└── Secrets/
    ├── __init__.py          # EMPTY
    └── get_pyalex_api_key.py
```

### Top-Level Package Naming

The top-level package folder must be named in `snake_case` and **must match the name defined in `pyproject.toml`** under `[project].name`.

```
# pyproject.toml
[project]
name = "paper_scraper"

# Directory structure
paper_scraper/           # snake_case, matches pyproject.toml
├── __init__.py
└── ...
```

---

## 7. Pixi Tasks

Run the pipeline with these commands:

```bash
# Extract references from seed PDFs using Grobid
pixi run extract_refs

# Download papers from OpenAlex using extracted DOIs
pixi run download_papers
```

---

## 8. Running Tests

### Run All Tests
```bash
pixi run pytest
```

### Run Specific Test File
```bash
pixi run pytest paper_scraper/Module/MyClass.py
```

### Run Specific Test Function
```bash
pixi run pytest paper_scraper/Module/MyClass.py::test_usage -o "addopts="
```

### Include Verbose/Print Output
```bash
pixi run pytest -s -v paper_scraper/Module/MyClass.py::test_usage
```

### Skip Slow Tests
Tests marked with `@pytest.mark.above10s` are automatically skipped by default configuration.

---

## 9. Naming Conventions

### Package and Subpackage Naming

All package and subpackage folders must follow **PascalCase** convention:

```
✅ MyPackage/, ModuleA/, BioInformatics/, Utils/, SubPackage /
❌ paper_scraper/, module_a/, bio_informatics/, utils/, subpackage /
```

**Note:** The top-level package is the exception — it must be named in `snake_case` to match `pyproject.toml`.

**Rationale:** PascalCase improves readability and distinguishes packages from regular modules/files at a glance.

### Naming Conventions Summary

| Element | Convention | Example |
|---------|------------|---------|
| **Top-level package** | snake_case | `paper_scraper/` |
| **Subpackages** | PascalCase | `Utils/`, `BioInformatics/` |
| **Classes** | PascalCase | `MyClass`, `Config` |
| **Enums** | PascalCase | `Status`, `LogLevel` |
| **Functions** | snake_case | `my_function`, `process_data` |
| **Function files** | snake_case (matches function name) | `my_function.py` contains `def my_function()` |

**File naming for functions:** The filename must match the function name in snake_case. Do NOT use different naming patterns (e.g., file `MyFunction.py` with function `def my_function()`).

```
✅ utils/
│   └── process_data.py     # Contains: def process_data()
❌ utils/
│   └── ProcessData.py     # Contains: def process_data()
```

**Packages:** A package is any folder containing an `__init__.py` file.

### `__HELPER_DIR__` Convention

Each top-level package should contain a `__HELPER_DIR__` subfolder for non-code assets (data files, templates, etc.). The folder must contain a `.gitkeep` file to ensure the empty directory is tracked by git:

```
library/Package/
├── __init__.py
├── __HELPER_DIR__/           # Contains non-code files + .gitkeep
│   ├── .gitkeep
│   ├── template.txt
│   └── data.json
└── __globals__.py            # Import HELPER_DIR as: from library.Package.__globals__ import HELPER_DIR
```

**Import pattern:**
```python
from library.Package.__globals__ import HELPER_DIR
```
