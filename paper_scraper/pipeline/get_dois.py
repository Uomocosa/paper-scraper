from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from paper_scraper import OpenAlex, Utils


OpenAlexOptions = OpenAlex.Options.Options
SearchFilter = OpenAlex.get_dois_from_filter.SearchFilter


@dataclass
class Config:
    extracted_references_path: Path | None = None
    filter: SearchFilter = field(default_factory=SearchFilter)
    output_dir: Path = field(default_factory=lambda: Path("OUTPUT_DIR"))


def get_dois(config: Config) -> list[str]:
    dois = []

    if config.extracted_references_path and config.extracted_references_path.exists():
        with open(config.extracted_references_path, "r", encoding="utf-8") as f:
            papers_json = f.read()
        dois = Utils.extract_dois_from_json(papers_json)
        logger.info(f"Found {len(dois)} DOIs from extracted references")
    else:
        logger.debug("No extracted_references_path provided or file not found")

    if config.filter.topics:
        filter_dois = OpenAlex.get_dois_from_filter(config.filter)
        logger.info(f"Found {len(filter_dois)} DOIs from filter")
        dois.extend(filter_dois)

    unique_dois = list(dict.fromkeys(dois))
    logger.info(f"Total unique DOIs: {len(unique_dois)}")
    return unique_dois


import pytest
from paper_scraper.__global__ import TEMP_OUTPUT_DIR


def test_usage():
    config = Config(
        extracted_references_path=TEMP_OUTPUT_DIR / "extracted_references.json",
        output_dir=TEMP_OUTPUT_DIR,
    )
    dois = get_dois(config)
    logger.info(f"Found {len(dois)} DOIs")
