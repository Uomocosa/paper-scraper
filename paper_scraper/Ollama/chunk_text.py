from pathlib import Path

import pytest
from pypdf import PdfReader
from loguru import logger


def chunk_text(text: str, max_context_tokens: int, max_chunks: int) -> list[str]:
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
    from paper_scraper import Utils
    from paper_scraper.__global__ import SEED_PAPERS_DIR

    pdf_path = next(
        pdf for pdf in SEED_PAPERS_DIR.iterdir() if pdf.suffix.lower() == ".pdf"
    )
    text = Utils.extract_text_from_pdf(pdf_path)
    logger.info(f"First 500 chars: {text[:500]}")

    chunks = chunk_text(text, max_context_tokens=256, max_chunks=2)
    print(f"Created {len(chunks)} chunks")
    print(f"chunks[0]: {chunks[0]}")
