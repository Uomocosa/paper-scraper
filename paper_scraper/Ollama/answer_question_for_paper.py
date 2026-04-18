from pathlib import Path

from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.AnalysisResult import AnalysisResult
from paper_scraper.Ollama.complete import _estimate_tokens, complete
from loguru import logger


def answer_question_for_paper(
    paper_text: str,
    question: str,
    options: Options = Options(),
    pdf_path: Path | None = None,
    handle_pdfs: str | None = None,
) -> AnalysisResult:
    if handle_pdfs is None:
        handle_pdfs = options.handle_pdfs

    if handle_pdfs == "pdf2image":
        return _answer_with_images(pdf_path, question, options)
    else:
        return _answer_with_text(paper_text, question, options)


def _answer_with_text(
    paper_text: str,
    question: str,
    options: Options,
) -> AnalysisResult:
    messages = [
        {"role": "system", "content": options.system_prompt},
        {
            "role": "user",
            "content": f"Paper:\n\n{paper_text}\n\n---\n\nQuestion: {question}\n\nPlease answer based only on the paper above.",
        },
    ]
    response = complete(messages, options)
    return AnalysisResult(response=response, skipped=False)


def _answer_with_images(
    pdf_path: Path | None,
    question: str,
    options: Options,
) -> AnalysisResult:
    if pdf_path is None:
        raise ValueError("pdf_path is required for pdf2image mode")

    from paper_scraper.Ollama.convert_pdf_to_images import (
        convert_pdf_to_images,
        encode_image_to_base64,
    )

    image_paths = convert_pdf_to_images(pdf_path)
    logger.info(f"Processing {len(image_paths)} page images for question")

    responses = []
    for i, image_path in enumerate(image_paths):
        base64_image = encode_image_to_base64(image_path)
        messages = [
            {"role": "system", "content": options.system_prompt},
            {
                "role": "user",
                "content": f"Page {i + 1} of the paper:\n\nQuestion: {question}\n\nPlease answer based only on the page image above.",
                "images": [base64_image],
            },
        ]
        page_response = complete(messages, options)
        responses.append(f"--- Page {i + 1} ---\n{page_response}")

    combined_response = "\n\n".join(responses)
    return AnalysisResult(response=combined_response, skipped=False)


import pytest
from paper_scraper.Ollama.read_pdf import read_pdf
from paper_scraper.__global__ import TEST_SEED_PAPER_1


@pytest.mark.above10s
def test_usage():
    full_text = read_pdf(TEST_SEED_PAPER_1)
    ollama_options = Options()
    words = full_text.split()
    safe_word_count = int(ollama_options.max_context_tokens / 4)
    safe_chunk = " ".join(words[:safe_word_count])
    logger.debug(f"len(safe_chunk): {len(safe_chunk)}")

    result = answer_question_for_paper(
        paper_text=safe_chunk,
        question="What are the main adsorption mechanisms described in this paper?",
        options=ollama_options,
    )
    logger.info(f"Result: {result}")
