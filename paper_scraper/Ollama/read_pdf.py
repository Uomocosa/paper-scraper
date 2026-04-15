from pathlib import Path
from pypdf import PdfReader
from loguru import logger


def read_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    logger.info(f"Reading PDF: {pdf_path.name}")
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
    from paper_scraper.__global__ import SEED_DIR

    pdf_path = next(pdf for pdf in SEED_DIR.iterdir() if pdf.suffix.lower() == ".pdf")
    text = read_pdf(pdf_path)
    logger.info(f"First 500 chars: {text[:500]}")
