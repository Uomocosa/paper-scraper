import re
import requests
from pathlib import Path
from dataclasses import dataclass

import pyalex
from pyalex import Works

import paper_scraper
from paper_scraper import OpenAlex
from paper_scraper import Grobid
from paper_scraper import Error
from paper_scraper import Secrets
from paper_scraper.Error.GrobidError import GrobidError
from paper_scraper.__global__ import DOWNLOADED_DIR, EXTRACTED_REFERENCES
from loguru import logger

Result = OpenAlex.Result
Status = OpenAlex.Result.Status
OpenAlexOptions = OpenAlex.Options.Options


@dataclass
class Options(OpenAlexOptions):
    depth: int = 0


def download_papers_from_dois(
    dois: list[str], options: Options = Options()
) -> dict[str, int]:
    options.setup_pyalex_key()

    results = {"SUCCESS": 0, "NOT_OPEN_ACCESS": 0, "ERROR": 0}
    current_depth = 0
    current_dois = dois

    while current_depth <= options.depth:
        dois = []
        for doi in current_dois:
            result = download_paper_from_doi(doi, options)
            results[result.status.name] += 1
            if result.status != Status.SUCCESS:
                continue
            try:
                references = Grobid.extract_references_from_pdf(result.path)
            except Exception as e:
                if e.__class__.__name__ == "GrobidUnexpectedStatus":
                    logger.warning(
                        f"Skipping {doi}: Grobid failed to parse PDF (HTTP {e.status_code})"
                    )
                    continue
                elif e.__class__.__name__ in [
                    "GrobidConnectionRefused",
                    "GrobidConnectionTimeout",
                ]:
                    logger.error(f"Grobid connection error: {e}")
                    raise
                raise
            logger.info(f"Extracted {len(references)} references from {doi}")
            dois += [ref["doi"] for ref in references if ref.get("doi")]
            logger.info(f"Next dois to download: {len(dois)}")
        current_dois = dois
        current_depth += 1

    logger.info(f"Results:\n\t" + "\n\t".join(f"{k}: {v}" for k, v in results.items()))
    return results


def download_paper_from_doi(
    doi: str, options: OpenAlex.Options = OpenAlex.Options()
) -> OpenAlex.Result:
    options.setup_pyalex_key()

    if not doi or not isinstance(doi, str):
        logger.warning(f"Skipping invalid DOI: {doi}")
        return Result(Status.ERROR)

    doi = doi.strip()
    if not doi.startswith("10."):
        logger.warning(f"Skipping invalid DOI format: {doi}")
        return Result(Status.ERROR)

    lookup_doi = f"doi:{doi}"
    try:
        work = Works()[lookup_doi]
    except Exception as e:
        logger.error(f"Failed to fetch DOI {doi}: {e}")
        return Result(Status.ERROR)

    if not work:
        logger.warning(f"Work not found for DOI: {doi}")
        return Result(Status.ERROR)

    primary_location = work.get("primary_location", {})
    pdf_url = primary_location.get("pdf_url") if primary_location else None

    if not pdf_url:
        logger.warning(f"No PDF URL available for DOI: {doi}")
        return Result(Status.NOT_OPEN_ACCESS)

    try:
        title = work.get("title", "unknown")
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.pdf"
        filepath = DOWNLOADED_DIR / filename

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(pdf_url, timeout=30, headers=headers)
        if response.status_code == 200:
            filepath.write_bytes(response.content)
            logger.info(f"Downloaded: {filename}")
            return Result(Status.SUCCESS, filepath)
        else:
            logger.warning(
                f"Failed to download PDF for {doi}: HTTP {response.status_code}"
            )
            return Result(Status.ERROR)

    except Exception as e:
        logger.error(f"Failed to download PDF for {doi}: {e}")
        return Result(Status.ERROR)


def sanitize_filename(text: str) -> str:
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:200]


def test_usage():
    dois = [
        "10.1016/j.envpol.2004.07.011",
        "10.1016/j.nexus.2022.100076",
        "10.3390/w12061530",
    ]
    download_papers_from_dois(dois)


import pytest


@pytest.mark.above10s
def test_recursion():
    dois = [
        "10.3390/w12061530",
    ]
    opts = Options(
        depth=1,
    )
    download_papers_from_dois(dois, opts)
