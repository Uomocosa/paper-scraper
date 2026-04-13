import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tyro
from loguru import logger
from pyalex import Works

import paper_scraper
from paper_scraper import OpenAlex
from paper_scraper.OpenAlex.download_papers_from_dois import Options as OpenAlexOptions
from paper_scraper.OpenAlex.Options import SearchOptions
from paper_scraper.Utils.extract_dois_from_json import extract_dois_from_json
from paper_scraper.__global__ import EXTRACTED_REFERENCES, DOWNLOADED_DIR, PAPERS_DIR
from paper_scraper.OpenAlex.download_papers_from_dois import download_papers_from_dois


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
    config = load_config()
    apply_cli_overrides(
        config, concepts, year_min, year_max, open_access_only, max_papers
    )

    if mode == "search":
        dois = search_and_filter(config)
    else:
        dois = load_extracted_references()

    logger.info(f"Found {len(dois)} DOIs to download")
    opts = OpenAlexOptions(depth=depth)
    download_papers_from_dois(dois, opts)


def load_config() -> SearchOptions:
    config_file = PAPERS_DIR / "download_config.toml"
    if not config_file.exists():
        return SearchOptions()

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return SearchOptions()

    search = data.get("search", {}) or {}
    return SearchOptions(
        concepts=search.get("concepts"),
        year_min=search.get("year_min"),
        year_max=search.get("year_max"),
        open_access_only=search.get("open_access_only", True),
        max_papers=search.get("max_papers", 100),
    )


def apply_cli_overrides(
    config: SearchOptions,
    concepts: list[str] | None,
    year_min: int | None,
    year_max: int | None,
    open_access_only: bool | None,
    max_papers: int,
):
    if concepts is not None:
        config.concepts = concepts
    if year_min is not None:
        config.year_min = year_min
    if year_max is not None:
        config.year_max = year_max
    if open_access_only is not None:
        config.open_access_only = open_access_only
    config.max_papers = max_papers


def search_and_filter(options: SearchOptions) -> list[str]:
    query = Works()

    if options.concepts:
        query = query.filter(concepts=options.concepts)

    if options.year_min or options.year_max:
        year_filter = {}
        if options.year_min:
            year_filter[">="] = str(options.year_min)
        if options.year_max:
            year_filter["<="] = str(options.year_max)
        query = query.filter(publication_year=year_filter)

    if options.open_access_only:
        query = query.filter(is_oa=True)

    results = query.get(per_page=options.max_papers)

    dois = []
    for work in results:
        doi = work.get("doi")
        if doi:
            dois.append(doi)

    logger.info(f"Found {len(dois)} papers matching filters")
    return dois


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
