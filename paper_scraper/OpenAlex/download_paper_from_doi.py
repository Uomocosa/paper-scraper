import re
import requests
from pathlib import Path

import pyalex
from pyalex import Works

import paper_scraper
from paper_scraper import OpenAlex
from loguru import logger

Result = OpenAlex.Result
Status = OpenAlex.Result.Status
OpenAlexOptions = OpenAlex.Options.Options


def download_paper_from_doi(
    doi: str,
    output_dir: Path,
    openalex_options: OpenAlexOptions = OpenAlexOptions(),
) -> OpenAlex.Result:
    openalex_options.setup_pyalex_key()
    output_dir.mkdir(parents=True, exist_ok=True)

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
        filepath = output_dir / filename

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(pdf_url, timeout=30, headers=headers)
        if response.status_code == 200:
            if not response.content.startswith(b"%PDF"):
                logger.warning(
                    f"Downloaded content is not a PDF for {doi}: HTML page returned"
                )
                return Result(Status.ERROR)
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
    from paper_scraper.__global__ import TEMP_DOWLOADED_PAPERS_DIR

    download_paper_from_doi("10.3390/w12061530", TEMP_DOWLOADED_PAPERS_DIR)
