from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

import paper_scraper
from paper_scraper import OpenAlex
from paper_scraper import Utils
from paper_scraper.__global__ import EXTRACTED_REFERENCES

OpenAlexOptions = OpenAlex.Options.Options
DownloadFilter = OpenAlex.get_dois_from_filter.Filter
DownloadReferenceOptions = OpenAlex.get_reference_dois.Options


@dataclass
class Config:
    papers_dir: Path
    output_dir: Path
    openalex_opts: OpenAlexOptions = field(default_factory=OpenAlexOptions)
    download_filter: DownloadFilter = field(default_factory=DownloadFilter)
    download_reference_opts: DownloadReferenceOptions = field(
        default_factory=DownloadReferenceOptions
    )


def download_papers(config: Config) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.openalex_opts.setup_pyalex_key()

    dois = OpenAlex.get_dois_from_filter(config.download_filter)
    logger.info(f"Found {len(dois)} DOIs from filter")
    OpenAlex.download_papers_from_dois(dois, config.output_dir, config.openalex_opts)

    if EXTRACTED_REFERENCES.exists():
        with open(EXTRACTED_REFERENCES, "r") as f:
            papers_json = f.read()
        seed_dois = Utils.extract_dois_from_json(papers_json)
        logger.info(f"Found {len(seed_dois)} DOIs from SEED/")
        OpenAlex.get_reference_dois.from_dois(
            seed_dois,
            DownloadReferenceOptions(depth=1),
            config.openalex_opts,
        )

    downloaded_papers = list(config.papers_dir.glob("*.pdf"))
    if downloaded_papers:
        logger.info(f"Found {len(downloaded_papers)} papers in papers_dir")
        reference_dois = OpenAlex.get_reference_dois.from_papers(
            downloaded_papers,
            config.download_reference_opts,
        )
        logger.info(
            f"Found {len(reference_dois)} reference DOIs from downloaded papers"
        )
        OpenAlex.download_papers_from_dois(
            reference_dois, config.output_dir, config.openalex_opts
        )


import pytest
from paper_scraper.__global__ import DOWNLOADED_DIR, SEED_DIR


@pytest.mark.above10s
def test_usage():
    config = Config(
        papers_dir=SEED_DIR,
        output_dir=DOWNLOADED_DIR,
        openalex_opts=OpenAlexOptions(),
        download_filter=DownloadFilter(
            topics=["T11948"],
            year_min=2022,
            max_papers=2,
        ),
        download_reference_opts=DownloadReferenceOptions(
            depth=1,
        ),
    )
    download_papers(config)
