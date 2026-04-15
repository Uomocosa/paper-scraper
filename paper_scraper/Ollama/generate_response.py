from pathlib import Path

from loguru import logger

from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.PaperResponse import PaperResponse
from paper_scraper.Ollama.QuestionResponse import QuestionResponse
from paper_scraper.Ollama.generate_for_paper import answer_question_for_paper
from paper_scraper.Ollama.read_pdf import read_pdf


def generate_response(
    question: str,
    papers_dir: Path,
    output_dir: Path,
    options: Options = Options(),
) -> QuestionResponse:
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(p for p in papers_dir.iterdir() if p.suffix.lower() == ".pdf")

    result = QuestionResponse(question=question)

    for pdf_path in pdf_files:
        paper_text = read_pdf(pdf_path)
        paper_response = answer_question_for_paper(
            question, paper_text, pdf_path.stem, output_dir, options
        )
        result.papers.append(paper_response)
        if paper_response.skipped:
            result.skipped_papers.append(pdf_path.name)

    if result.skipped_papers:
        skipped_path = output_dir / "paper_skipped.txt"
        with open(skipped_path, "w", encoding="utf-8") as f:
            for name in result.skipped_papers:
                f.write(f"{name}\n")

    return result


def batch_generate(
    questions: list[str],
    papers_dir: Path,
    responses_dir: Path,
    options: Options = Options(),
) -> list[QuestionResponse]:
    results = []
    for question in questions:
        output_dir = responses_dir / sanitize_filename(question)
        logger.info(f"Processing question: {question[:50]}...")
        result = generate_response(question, papers_dir, output_dir, options)
        results.append(result)

    logger.info(f"Done! Processed {len(results)} questions.")
    return results


def sanitize_filename(text: str) -> str:
    import re

    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:100]


def test_usage():
    from paper_scraper.__global__ import SEED_DIR

    question = "What are the main adsorption mechanisms described in this paper?"
    papers_dir = SEED_DIR
    output_dir = Path("RESPONSES/test_question")
    result = generate_response(question, papers_dir, output_dir)
    logger.info(f"Results: {result.papers}")
