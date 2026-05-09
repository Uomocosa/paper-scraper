from pathlib import Path
from loguru import logger

FUNCTIONS = {
    "pdf2text": lambda pdf_path: pdf2text(pdf_path),
    "pdf2image": lambda pdf_path: pdf2image(pdf_path),
}

def get_handle_pdf_function(function_name: str):
    return FUNCTIONS[function_name]

def pdf2text(pdf_path: Path) -> str:
    from paper_scraper.Ollama.read_pdf import read_pdf
    
    logger.info(f"Converting {pdf_path.name} to text")
    return read_pdf(pdf_path)


def pdf2image(pdf_path: Path) -> list[str]:
    from paper_scraper.Ollama.convert_pdf_to_images import (
        convert_pdf_to_images,
        encode_image_to_base64,
    )
    
    logger.info(f"Converting {pdf_path.name} to images")
    image_paths = convert_pdf_to_images(pdf_path)
    base64_images = [encode_image_to_base64(path) for path in image_paths]
    return base64_images


def test_to_text():
    from paper_scraper.__global__ import TEST_SEED_PAPER_1
    result = pdf2text(TEST_SEED_PAPER_1)
    assert isinstance(result, str)
    assert len(result) > 0
    logger.info(f"Extracted text length: {len(result)} characters")


def test_to_image():
    from paper_scraper.__global__ import TEST_SEED_PAPER_1
    result = pdf2image(TEST_SEED_PAPER_1)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(img, str) for img in result)
    logger.info(f"Converted to {len(result)} base64 images")
