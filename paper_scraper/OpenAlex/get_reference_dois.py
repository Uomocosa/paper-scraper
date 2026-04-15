from pathlib import Path
from typing import Iterator
from dataclasses import dataclass
from loguru import logger
import paper_scraper
from paper_scraper import OpenAlex
from paper_scraper import Grobid
from paper_scraper.Grobid.Error import (
    ConnectionRefused,
    ConnectionTimeout,
    UnexpectedStatus,
)
from paper_scraper.OpenAlex.download_papers_from_dois import download_papers_from_dois
from paper_scraper.OpenAlex.Result import Status

OpenAlexOptions = OpenAlex.Options.Options


@dataclass
class Options:
    depth: int = 1


def from_dois(
    dois: list[str],
    options: Options = Options(),
    openalex_options: OpenAlexOptions = OpenAlexOptions(),
) -> list[str]:
    openalex_options.setup_pyalex_key()

    all_dois = []
    current_dois = dois
    current_depth = 0

    while current_depth < options.depth:
        next_dois = []
        results = OpenAlex.download_papers_from_dois(current_dois, openalex_options)

        for doi in current_dois:
            result = OpenAlex.download_paper_from_doi(doi, openalex_options)
            if result.status != Status.SUCCESS:
                continue
            try:
                references = Grobid.extract_references_from_pdf(result.path)
            except UnexpectedStatus:
                logger.warning(f"Skipping {doi}: Grobid failed to parse PDF")
                continue
            except (ConnectionRefused, ConnectionTimeout):
                logger.error(f"Grobid connection error")
                raise

            logger.info(f"Extracted {len(references)} references from {doi}")
            next_dois += [ref["doi"] for ref in references if ref.get("doi")]

        all_dois.extend(next_dois)
        current_dois = next_dois
        current_depth += 1

    return all_dois


def from_papers(
    paper_paths: list[Path],
    options: Options = Options(),
) -> list[str]:
    all_dois = []
    current_paths = paper_paths
    current_depth = 0

    while current_depth < options.depth:
        next_dois = []
        for paper_path in current_paths:
            try:
                references = Grobid.extract_references_from_pdf(paper_path)
            except UnexpectedStatus:
                logger.warning(
                    f"Skipping {paper_path.name}: Grobid failed to parse PDF"
                )
                continue
            except (ConnectionRefused, ConnectionTimeout):
                logger.error(f"Grobid connection error")
                raise

            logger.info(
                f"Extracted {len(references)} references from {paper_path.name}"
            )
            next_dois += [ref["doi"] for ref in references if ref.get("doi")]

        all_dois.extend(next_dois)
        current_dois = next_dois
        current_depth += 1

    return all_dois


def download_paper_result(doi: str) -> OpenAlex.Result:
    return


def test_usage():
    dois = ["10.3390/w12061530"]
    result_dois = from_dois(dois, Options(depth=1))
    logger.info(f"Found {len(result_dois)} reference DOIs: {result_dois}")
