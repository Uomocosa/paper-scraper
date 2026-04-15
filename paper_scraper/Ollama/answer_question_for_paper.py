from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.AnalysisResult import AnalysisResult
from paper_scraper.Ollama.complete import _estimate_tokens, complete
from loguru import logger


def answer_question_for_paper(
    paper_text: str,
    question: str,
    options: Options = Options(),
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


import pytest
from paper_scraper.Ollama.read_pdf import read_pdf
from paper_scraper.__global__ import POLYPHOX_PAPER


@pytest.mark.above10s
def test_usage():
    full_text = read_pdf(POLYPHOX_PAPER)
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
