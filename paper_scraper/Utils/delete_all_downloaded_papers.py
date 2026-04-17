from pathlib import Path

import paper_scraper
from paper_scraper.__global__ import TEMP_DOWLOADED_PAPERS_DIR
from loguru import logger


def delete_all_downloaded_papers() -> int:
    deleted = 0
    for pdf_file in TEMP_DOWLOADED_PAPERS_DIR.glob("*.pdf"):
        pdf_file.unlink()
        logger.info(f"Deleted: {pdf_file.name}")
        deleted += 1
    logger.info(f"Deleted {deleted} PDF files")
    return deleted


def test_usage():
    count = delete_all_downloaded_papers()
    logger.info(f"Test deleted {count} files")
