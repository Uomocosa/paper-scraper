import json
from pathlib import Path

from paper_scraper.__global__ import SEED_PAPERS_DIR
from paper_scraper import Grobid

from loguru import logger

from paper_scraper.__global__ import TEMP_OUTPUT_DIR


def extract_refs(papers: list[Path], extracted_references_path: Path):
    logger.info("Checking Grobid connection...")
    Grobid.check_connection()
    logger.info("Grobid connection OK.")

    all_references = []

    for pdf_file in papers:
        if pdf_file.suffix.lower() == ".pdf":
            refs = Grobid.extract_references_from_pdf(pdf_file)

            logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
            all_references.extend(refs)

    extracted_references_path.parent.mkdir(parents=True, exist_ok=True)
    with open(extracted_references_path, "w", encoding="utf-8") as f:
        json.dump(all_references, f, indent=4)

    logger.info(
        f"Done! Saved a total of {len(all_references)} references to {extracted_references_path}"
    )


def test_usage():
    papers = list(SEED_PAPERS_DIR.iterdir())
    extracted_path = TEMP_OUTPUT_DIR / "extracted_references.json"
    extract_refs(papers, extracted_path)
