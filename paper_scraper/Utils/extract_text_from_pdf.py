from pathlib import Path

import pytest
from pypdf import PdfReader
from loguru import logger


def extract_text_from_pdf(pdf_path: Path) -> str:
    logger.info(f"Reading PDF: {pdf_path.name}")
    content = pdf_path.read_bytes()
    if not content.startswith(b"%PDF"):
        raise ValueError(f"File is not a valid PDF: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    text_parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            text_parts.append(text)
    result = "\n\n".join(text_parts)
    logger.info(f"Extracted {len(result)} characters from {pdf_path.name}")
    return result



def test_usage():
    import paper_scraper
    from paper_scraper.__global__ import SEED_PAPERS_DIR

    pdf_path = next(
        pdf for pdf in SEED_PAPERS_DIR.iterdir() if pdf.suffix.lower() == ".pdf"
    )
    text = extract_text_from_pdf(pdf_path)
    print(f"First 500 chars: {text[:500]}")
