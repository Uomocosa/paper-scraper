from pathlib import Path

from loguru import logger

from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.PaperResponse import PaperResponse
from paper_scraper.Ollama.call_ollama import _estimate_tokens, call_ollama
from paper_scraper.Ollama.read_pdf import read_pdf


def answer_question_for_paper(
    question: str,
    paper_text: str,
    paper_name: str,
    output_dir: Path,
    options: Options = Options(),
) -> PaperResponse:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Processing: {paper_name}")

    token_count = _estimate_tokens(paper_text)

    if token_count > options.max_context_tokens:
        logger.warning(
            f"Skipping {paper_name}: {token_count} tokens > {options.max_context_tokens} limit"
        )
        return PaperResponse(
            paper_name=paper_name,
            response="",
            skipped=True,
        )

    answer = call_ollama(question, paper_text, options)

    output_path = output_dir / f"{paper_name}.md"
    output_path.write_text(answer, encoding="utf-8")
    logger.info(f"Wrote: {output_path.name}")

    return PaperResponse(
        paper_name=paper_name,
        response=answer,
        skipped=False,
    )

def test_usage():
    from paper_scraper.__global__ import POLYPHOX_PAPER
    full_text = read_pdf(POLYPHOX_PAPER)
    ollama_options = Options()
    words = full_text.split()
    safe_word_count = int(ollama_options.max_context_tokens / 4)
    safe_chunk = " ".join(words[:safe_word_count]) 
    logger.debug(f"len(safe_chunk): {len(safe_chunk)}")
    result = answer_question_for_paper(
        question="What are the main adsorption mechanisms described in this paper?",
        paper_text=safe_chunk,
        paper_name=POLYPHOX_PAPER.stem,
        output_dir=Path("RESPONSES/test_single_paper"),
        options=ollama_options,
    )
    logger.info(f"Result: {result}")
