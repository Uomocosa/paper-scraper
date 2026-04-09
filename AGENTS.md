# Python Project Coding Conventions

## Project Overview

This document describes the coding conventions for this Python project.

---

## 1. Import System: new-import-system

### Installation in Top-Level `__init__.py`

Every top-level package `__init__.py` must install the new-import-system:

```python
import new_import_system
new_import_system.install(__file__)
```

**Example:** `my_package/__init__.py`
```python
import new_import_system
new_import_system.install(__file__)
```

### Import Rules

- **NEVER use relative imports** (e.g., `from .Module import ...` is forbidden)
- **Always use absolute imports** (e.g., `import my_package`, `from my_package.Module import MyClassMethod`)
- **No need to repeat module name** in function calls when the module name matches the function name:

```python
# Instead of this:
my_package.Module.MyClassMethod.my_function(df, options)

# Do this:
my_package.Module.MyClassMethod.my_function(df, options)
# OR if my_function is the only exported function from MyClassMethod:
my_package.Module.MyClassMethod(df, options)
```

### Empty `__init__.py` Files

All `__init__.py` files EXCEPT the top-level one must be **empty**:

```
my_package/
├── __init__.py          # Contains new-import-system installation
├── Module/
│   ├── __init__.py      # EMPTY
│   ├── MyClass.py
│   └── MyClassMethod/
│       ├── __init__.py  # EMPTY
│       └── my_method.py
```

---

## 2. Code Granularity & Organization

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

### Method Subpackages: `ClassNameMethod/`

When a dataclass needs methods, create a subpackage named `ClassNameMethod/` and implement methods there.

**Structure:**
```
my_package/Module/
├── MyClass.py              # Dataclass definition
└── MyClassMethod/
    ├── __init__.py         # EMPTY
    ├── my_method.py        # Method implementation
    ├── another_method.py
    └── process_data.py
```

**Dataclass references methods via the subpackage:**

```python
# my_package/Module/MyClass.py
from dataclasses import dataclass
import my_package

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
# my_package/Module/MyClassMethod/my_method.py
from dataclasses import dataclass, field
import pandas as pd
import my_package

@dataclass
class Options:
    option_a: str = "default_value"
    n_points: int = 2

def my_method(df: pd.DataFrame, options: Options = Options()) -> pd.DataFrame:
    # Implementation here
    return df

def test_my_method():
    from my_package.__global__ import DATA_CSV
    my_package.setup_loguru()
    df = pd.read_csv(DATA_CSV)
    df = my_method(df, Options(option_a="value"))
    assert len(df) > 0
```

---

## 3. Testing Conventions

### `test_usage()` Function Pattern

Every module (function, dataclass, enum) must have at least one `test_usage()` function with **no arguments**:

```python
def test_usage():
    from my_package.__global__ import DATA_CSV
    config = Config(csv_file=DATA_CSV)
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
pixi run pytest -rFP -q -s my_package/Module/MyClass.py::test_usage -o "addopts="
```

---

## 4. Global Constants: `__global__.py`

Use `__global__.py` files for constants and shared configuration:

```python
# my_package/__global__.py
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = REPO_DIR / 'DATA'
RESULTS_DIR = REPO_DIR / 'RESULTS'

from joblib import Memory
CACHE_MEMORY = Memory(location=".cache_dir", verbose=0)

CONFIG_DICT = {
    "key_a": "value_a",
    "key_b": "value_b",
}
```

Each subpackage can have its own `__global__.py`:

```python
# my_package/Module/__global__.py
import lele

THIS_FOLDER = lele.P(__file__).parent
HELPER_DIR = THIS_FOLDER / '__HELPER_DIR__'
```

---

## 5. Code Style Rules

### No Comments (Unless Required)

Add comments only when absolutely necessary for understanding. Code should be self-documenting.

**Good:**
```python
def filter_data(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    new_rows = []
    for group_key, group in df.groupby(['category_a', 'category_b']):
        if not (group['value'] > threshold).any():
            new_row = group.iloc[0].copy()
            new_row['value'] = threshold
            new_rows.append(new_row)
    return pd.concat([df, pd.DataFrame(new_rows)])
```

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

Setup loguru once per entry point:

```python
import my_package
my_package.setup_loguru()
```

---

## 6. Directory Structure

```
my_package/
├── __init__.py              # new-import-system installation
├── __global__.py            # Global constants
├── setup_loguru.py          # Logging configuration
├── ModuleA/
│   ├── __init__.py          # EMPTY
│   ├── __global__.py        # Module-specific constants
│   ├── Config.py            # Config dataclass
│   ├── MyClass.py           # Main dataclass
│   └── MyClassMethod/       # Methods for MyClass
│       ├── __init__.py      # EMPTY
│       ├── my_method.py
│       ├── another_method.py
│       └── ...
├── ModuleB/
│   ├── __init__.py          # EMPTY
│   ├── __global__.py        # Module-specific constants
│   ├── AnotherClass.py      # Another dataclass
│   └── AnotherClassMethod/  # Methods for AnotherClass
│       ├── __init__.py      # EMPTY
│       └── ...
└── Utils/
    ├── __init__.py          # EMPTY
    └── helper_functions.py
```

### Top-Level Package Naming

The top-level package folder must be named in `snake_case` and **must match the name defined in `pyproject.toml`** under `[project].name`.

```
# pyproject.toml
[project]
name = "my_package"

# Directory structure
my_package/           # snake_case, matches pyproject.toml
├── __init__.py
└── ...
```

---

## 7. Complete Example

### File: `my_package/Module/MyClass.py`

```python
import pandas as pd
from dataclasses import dataclass
import my_package
from my_package.Module import MyClassMethod
from loguru import logger

@dataclass
class Config:
    csv_file: Path
    param_a: float = 0.6
    param_b: float = 0.2
    param_c: float = 0.2
    max_size: Optional[int] = None
    seed: int = 42

@dataclass
class MyClass:
    data: pd.DataFrame
    config: Config
    
    def __init__(self, config: Config):
        self.data = pd.read_csv(config.csv_file)
        self.config = config
    
    @staticmethod
    def process_fn(df: pd.DataFrame) -> pd.DataFrame:
        return MyClassMethod.process(df)
        
    def my_method(self, options=MyClassMethod.my_method.Options()):
        original_len = len(self.data)
        self.data = MyClassMethod.my_method(self.data, options)
        logger.info(f"Processed: gained {len(self.data) - original_len} rows.")
        
    def another_method(self, options=MyClassMethod.another_method.Options()):
        self.data = MyClassMethod.another_method(self.data, options)
```

### File: `my_package/Module/MyClassMethod/my_method.py`

```python
from dataclasses import dataclass
import pandas as pd
import numpy as np
import my_package
from loguru import logger

@dataclass
class Options:
    method: str = "method_a"
    param: int = 2

def my_method(df: pd.DataFrame, options: Options = Options()) -> pd.DataFrame:
    METHOD_DICT = {
        "method_a": lambda df: process_a(df),
        "method_b": lambda df: process_b(df),
        "method_a_then_b": lambda df: process_b(process_a(df)),
    }
    method = METHOD_DICT[options.method]
    return method(df)

def process_a(df: pd.DataFrame) -> pd.DataFrame:
    # Implementation
    return df

def process_b(df: pd.DataFrame) -> pd.DataFrame:
    # Implementation
    return df

def test_method_a():
    from my_package.__global__ import DATA_CSV
    my_package.setup_loguru()
    df = pd.read_csv(DATA_CSV)
    df = my_method(df, Options(method="method_a"))
    assert len(df) > 0

def test_method_b():
    from my_package.__global__ import DATA_CSV
    my_package.setup_loguru()
    df = pd.read_csv(DATA_CSV)
    df = my_method(df, Options(method="method_b"))
    assert len(df) > 0
```

---

## 8. Running Tests

### Run All Tests
```bash
pixi run pytest
```

### Run Specific Test File
```bash
pixi run pytest my_package/Module/MyClass.py
```

### Run Specific Test Function
```bash
pixi run pytest my_package/Module/MyClass.py::test_usage -o "addopts="
```

### Include Verbose/Print Output
```bash
pixi run pytest -s -v my_package/Module/MyClass.py::test_usage
```

### Skip Slow Tests
Tests marked with `@pytest.mark.above10s` are automatically skipped by default configuration.

---

## 9. Naming Conventions

### Package and Subpackage Naming

All package and subpackage folders must follow **PascalCase** convention:

```
✅ MyPackage/, ModuleA/, BioInformatics/, Utils/, SubPackage /
❌ my_package/, module_a/, bio_informatics/, utils/, subpackage /
```

**Note:** The top-level package is the exception — it must be named in `snake_case` to match `pyproject.toml`.

**Rationale:** PascalCase improves readability and distinguishes packages from regular modules/files at a glance.

### Naming Conventions Summary

| Element | Convention | Example |
|---------|------------|---------|
| **Top-level package** | snake_case | `my_package/` |
| **Subpackages** | PascalCase | `Utils/`, `BioInformatics/` |
| **Classes** | PascalCase | `MyClass`, `Config` |
| **Enums** | PascalCase | `Status`, `LogLevel` |
| **Functions** | snake_case | `my_function`, `process_data` |

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
