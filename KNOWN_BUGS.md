# Known Bugs

## 1. Double download in `get_reference_dois.from_dois()`

**File:** `paper_scraper/OpenAlex/get_reference_dois.py:37-43`

Every paper is downloaded twice: first via the batch `download_papers_from_dois()` call (line 37-39), then again via the individual `download_paper_from_doi()` loop (line 41-42).

```python
results = OpenAlex.download_papers_from_dois(...)  # batch download

for doi in current_dois:
    result = OpenAlex.download_paper_from_doi(...)  # individual download (same papers again)
```

The individual loop exists solely to get the file path for Grobid extraction, but `download_papers_from_dois` already returns that information.

---

## 3. Dead stub `download_paper_result()` returns `None`

**File:** `paper_scraper/OpenAlex/get_reference_dois.py:98-99`

```python
def download_paper_result(doi: str) -> OpenAlex.Result:
    return
```

The function body is just `return` (returns `None`) despite the return type annotation promising `OpenAlex.Result`. It is never called anywhere in the codebase.

---

## 4. Per-DOI API calls for year and OA post-filtering (performance bug)

**File:** `paper_scraper/OpenAlex/get_dois_from_filter.py:437-466`

`_filter_by_year()` and `_filter_open_access_only()` call `Works()[f"doi:{doi}"]` in a loop — one individual API call per DOI:

```python
for doi in dois:
    work = Works()[f"doi:{doi}"]
    ...
```

For hundreds of DOIs, this is extremely slow and likely to hit OpenAlex rate limits. These should be batched or applied at query time rather than post-filtered.

---

## 5. Typo: `TEMP_DOWLOADED_PAPERS_DIR` (missing 'n')

**File:** `paper_scraper/__global__.py:18,19,29`

The constant is misspelled as `TEMP_DOWLOADED_PAPERS_DIR` instead of `TEMP_DOWNLOADED_PAPERS_DIR`. Used in:

- `paper_scraper/OpenAlex/get_reference_dois.py:8` (import and test usage)
- `paper_scraper/OpenAlex/download_paper_from_doi.py` (test usage, line not shown)
- `paper_scraper/Utils/delete_all_downloaded_papers.py`

---

## 6. Import-time side effects in `__global__.py`

**File:** `paper_scraper/__global__.py:26-29`

Module-level assertions and `mkdir` calls execute at import time:

```python
assert SEED_PAPERS_DIR.exists(), f"SEED_PAPERS_DIR does not exist: {SEED_PAPERS_DIR}"
TEMP_DOWLOADED_PAPERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
```

- Import fails entirely if `SEED_PAPERS_DIR` does not exist.
- Directories are created as a side effect of importing the module.
- `TEMP_DOWLOADED_PAPERS_DIR.mkdir()` is called twice (lines 19 and 29).

---

## 7. Unused import in `download_paper_from_doi.py`

**File:** `paper_scraper/OpenAlex/download_paper_from_doi.py:16`

```python
OpenAlexOptions = OpenAlex.Options.Options
```

This variable is assigned but never used in the module. It shadows the import from `paper_scraper` for no purpose.
