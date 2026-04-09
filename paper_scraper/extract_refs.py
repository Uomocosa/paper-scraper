import json
from pathlib import Path

import paper_scraper
from paper_scraper.__global__ import SEED_DIR, REPO_DIR
from paper_scraper import Grobid

from loguru import logger

def extract_refs():
    logger.info("Checking Grobid connection...")
    Grobid.check_connection()
    logger.info("Grobid connection OK.")

    all_references = []

    for pdf_file in SEED_DIR.iterdir():
        if pdf_file.suffix.lower() == ".pdf":
            refs = Grobid.extract_references_from_pdf(pdf_file)

            logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
            all_references.extend(refs)

    with open(REPO_DIR / "extracted_references.json", "w", encoding="utf-8") as f:
        json.dump(all_references, f, indent=4)

    logger.info(
        f"Done! Saved a total of {len(all_references)} references to extracted_references.json"
    )


def test_usage():
    extract_refs()
