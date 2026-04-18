from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from paper_scraper import Grobid
from paper_scraper.__global__ import SEED_PAPERS_DIR

import json


@dataclass
class Config:
    seed_papers: list[Path] | Path | None = None
    output_dir: Path = field(
        default_factory=lambda: SEED_PAPERS_DIR.parent / "OUTPUT_DIR"
    )
    batch_size: int = 1

    @property
    def papers(self) -> list[Path]:
        if self.seed_papers is None:
            papers = list(SEED_PAPERS_DIR.glob("*.pdf"))
            logger.debug(f"Auto-discovered {len(papers)} PDFs in SEED_PAPERS_DIR")
            return papers
        if isinstance(self.seed_papers, Path):
            return (
                [self.seed_papers] if self.seed_papers.suffix.lower() == ".pdf" else []
            )
        return [p for p in self.seed_papers if p.suffix.lower() == ".pdf"]

    @property
    def extracted_references_path(self) -> Path:
        return self.output_dir / "extracted_references.json"


def extract_refs(config: Config) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info("Checking Grobid connection...")
    Grobid.check_connection()
    logger.info("Grobid connection OK.")

    config.output_dir.mkdir(parents=True, exist_ok=True)

    papers = config.papers
    logger.info(f"Processing {len(papers)} seed paper(s)")

    all_references = []

    if config.batch_size > 1:
        with ThreadPoolExecutor(max_workers=config.batch_size) as executor:
            futures = {
                executor.submit(Grobid.extract_references_from_pdf, p): p
                for p in papers
            }
            for future in as_completed(futures):
                pdf_file = futures[future]
                try:
                    refs = future.result()
                    logger.info(
                        f"Extracted {len(refs)} references from {pdf_file.name}."
                    )
                    all_references.extend(refs)
                except Exception as e:
                    logger.error(f"Failed to extract refs from {pdf_file.name}: {e}")
    else:
        for pdf_file in papers:
            refs = Grobid.extract_references_from_pdf(pdf_file)
            logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
            all_references.extend(refs)

    with open(config.extracted_references_path, "w", encoding="utf-8") as f:
        json.dump(all_references, f, indent=4)

    logger.info(
        f"Saved {len(all_references)} references to {config.extracted_references_path}"
    )

    return all_references


import pytest
@pytest.mark.requires_grobid
def test_usage():
    from paper_scraper.__global__ import TEST_SEED_PAPER_1, TEMP_OUTPUT_DIR
    config = Config(
        seed_papers=[TEST_SEED_PAPER_1],
        output_dir=TEMP_OUTPUT_DIR,
        batch_size=1,
    )
    extract_refs(config)
