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


def download_papers_from_dois(
    dois: list[str],
    output_dir: Path,
    openalex_options: OpenAlexOptions = OpenAlexOptions(),
) -> dict[str, int]:
    openalex_options.setup_pyalex_key()

    results = {"SUCCESS": 0, "NOT_OPEN_ACCESS": 0, "ERROR": 0}

    for doi in dois:
        result = OpenAlex.download_paper_from_doi(doi, output_dir)
        results[result.status.name] += 1

    logger.info(f"Results:\n\t" + "\n\t".join(f"{k}: {v}" for k, v in results.items()))
    return results


def test_usage():
    from paper_scraper.__global__ import TEMP_DOWLOADED_PAPERS_DIR
    dois = [
        "10.1016/j.envpol.2004.07.011",
        "10.1016/j.nexus.2022.100076",
        "10.3390/w12061530",
    ]
    download_papers_from_dois(
        dois, 
        output_dir = TEMP_DOWLOADED_PAPERS_DIR,
    )
