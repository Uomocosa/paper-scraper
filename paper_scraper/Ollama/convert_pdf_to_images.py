import base64
from pathlib import Path

import pytest
from loguru import logger


def convert_pdf_to_images(pdf_path: Path, output_dir: Path | None = None) -> list[Path]:
    """Convert each PDF page to a PNG image.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images. If None, uses temp directory.

    Returns:
        List of paths to generated PNG images (one per page, in order)
    """
    import fitz

    logger.info(f"Converting PDF to images: {pdf_path.name}")
    content = pdf_path.read_bytes()
    if not content.startswith(b"%PDF"):
        raise ValueError(f"File is not a valid PDF: {pdf_path}")

    if output_dir is None:
        import tempfile

        output_dir = Path(tempfile.gettempdir()) / f"paper_scraper_{pdf_path.stem}"
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap()
        image_path = output_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)
        logger.debug(f"Saved page {page_num + 1} to {image_path}")

    doc.close()
    logger.info(f"Converted {len(image_paths)} pages to images")
    return image_paths


def encode_image_to_base64(image_path: Path) -> str:
    """Encode an image file to base64 string for Ollama vision API."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@pytest.mark.requires_grobid
def test_usage():
    from paper_scraper.__global__ import TEST_SEED_PAPER_1

    image_paths = convert_pdf_to_images(TEST_SEED_PAPER_1)
    logger.info(f"Created {len(image_paths)} images")
    for path in image_paths[:3]:
        logger.info(f"  {path}")
