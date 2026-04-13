import tyro
from loguru import logger

import paper_scraper
from paper_scraper.OpenAlex.download_papers_from_dois import Options as OpenAlexOptions
from paper_scraper.OpenAlex.download_papers_with_filter import (
    Filter,
    download_papers_with_filter,
    load_config,
    apply_cli_overrides,
)
from paper_scraper.OpenAlex.download_papers_from_dois import download_papers_from_dois
from paper_scraper.Utils.extract_dois_from_json import extract_dois_from_json
from paper_scraper.__global__ import EXTRACTED_REFERENCES


def main(
    mode: str = "recursive",
    concepts: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    open_access_only: bool | None = None,
    max_papers: int = 100,
    depth: int = 0,
):
    """Download papers from OpenAlex.

    Args:
        mode: Download mode - "recursive" (from seed refs) or "search" (by filters).
        concepts: OpenAlex concept IDs for search, e.g. ["C1264102"].
        year_min: Minimum publication year (search mode).
        year_max: Maximum publication year (search mode).
        open_access_only: Only open access papers (search mode).
        max_papers: Maximum papers to download (search mode).
        depth: Recursion depth (recursive mode).
    """
    if mode == "search":
        filter = load_config()
        apply_cli_overrides(
            filter, concepts, year_min, year_max, open_access_only, max_papers
        )
        download_papers_with_filter(filter, depth)
    else:
        dois = load_extracted_references()
        logger.info(f"Found {len(dois)} DOIs to download")
        opts = OpenAlexOptions(depth=depth)
        download_papers_from_dois(dois, opts)


def load_extracted_references() -> list[str]:
    if not EXTRACTED_REFERENCES.exists():
        logger.warning(f"No extracted references found at {EXTRACTED_REFERENCES}")
        return []

    with open(EXTRACTED_REFERENCES, "r") as f:
        papers_json = f.read()

    dois = extract_dois_from_json(papers_json)
    return dois


def test_usage():
    main(mode="recursive", depth=0)


def test_search():
    main(mode="search", concepts=["C1264102"], year_min=2022, max_papers=10)
