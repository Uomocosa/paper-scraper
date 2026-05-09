from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from paper_scraper import OpenAlex, Utils
from paper_scraper.__global__ import OUTPUT_DIR

OpenAlexOptions = OpenAlex.Options.Options
SearchFilter = OpenAlex.get_dois_from_filter.SearchFilter


@dataclass
class Config:
    extracted_references_path: Path | None = None
    search_filter: SearchFilter = field(default_factory=lambda: SearchFilter())
    output_dir: Path = OUTPUT_DIR


def get_dois(config: Config) -> list[str]:
    dois = []

    if config.extracted_references_path and config.extracted_references_path.exists():
        with open(config.extracted_references_path, "r", encoding="utf-8") as f:
            papers_json = f.read()
        dois = Utils.extract_dois_from_json(papers_json)
        logger.info(f"Found {len(dois)} DOIs from extracted references")
    else:
        logger.debug("No extracted_references_path provided or file not found")

    if config.search_filter.topics:
        filter_dois = OpenAlex.get_dois_from_filter(config.search_filter)
        logger.info(f"Found {len(filter_dois)} DOIs from search_filter")
        dois.extend(filter_dois)

    unique_dois = list(dict.fromkeys(dois))
    logger.info(f"Total unique DOIs: {len(unique_dois)}")
    return unique_dois




import pytest
@pytest.mark.requires_grobid
def test_usage():
    from paper_scraper.__global__ import TEMP_OUTPUT_DIR
    config = Config(
        extracted_references_path=TEMP_OUTPUT_DIR / "extracted_references.json",
        output_dir=TEMP_OUTPUT_DIR,
    )
    dois = get_dois(config)
    logger.info(f"Found {len(dois)} DOIs")
