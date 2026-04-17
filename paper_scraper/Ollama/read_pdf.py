from pathlib import Path
from pypdf import PdfReader
from loguru import logger


def read_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
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


def chunk_text(text: str, max_context_tokens: int, max_chunks: int) -> list[str]:
    """Split text into chunks based on token estimation.

    Args:
        text: Full paper text
        max_context_tokens: Max tokens per chunk (will estimate ~4 chars per token)
        max_chunks: Maximum number of chunks to return (1 = testing mode)

    Returns:
        List of text chunks
    """
    words = text.split()
    chunk_size = max_context_tokens // 4
    chunks = []

    for i in range(min(max_chunks, (len(words) + chunk_size - 1) // chunk_size)):
        start = i * chunk_size
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

    return chunks


def test_usage():
    import paper_scraper
    from paper_scraper.__global__ import SEED_PAPERS_DIR

    pdf_path = next(pdf for pdf in SEED_PAPERS_DIR.iterdir() if pdf.suffix.lower() == ".pdf")
    text = read_pdf(pdf_path)
    logger.info(f"First 500 chars: {text[:500]}")

    chunks = chunk_text(text, max_context_tokens=256, max_chunks=2)
    logger.info(f"Created {len(chunks)} chunks")
