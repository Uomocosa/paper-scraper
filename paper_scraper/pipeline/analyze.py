from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from paper_scraper import Ollama
from paper_scraper.Ollama import Options as OllamaOptions


@dataclass
class Config:
    questions: list[str] | Path | None = None
    papers_dir: Path = field(
        default_factory=lambda: Path("OUTPUT_DIR") / "DOWNLOADED_PAPERS"
    )
    output_dir: Path = field(default_factory=lambda: Path("OUTPUT_DIR"))
    ollama_opts: OllamaOptions = field(
        default_factory=lambda: OllamaOptions(model="tinyllama")
    )
    max_chunks: int = 1

    @property
    def questions_list(self) -> list[str]:
        if self.questions is None:
            return []
        if isinstance(self.questions, list):
            return self.questions
        if isinstance(self.questions, Path) and self.questions.suffix.lower() == ".txt":
            with open(self.questions, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return []

    @property
    def questions_dir(self) -> Path:
        return self.output_dir / "QUESTIONS"

    @property
    def responses_dir(self) -> Path:
        return self.output_dir / "RESPONSES"


def _save_questions(questions: list[str], questions_dir: Path) -> None:
    questions_dir.mkdir(parents=True, exist_ok=True)
    for q_idx, question in enumerate(questions, start=1):
        question_file = questions_dir / f"q{q_idx}.md"
        question_file.write_text(question, encoding="utf-8")
    logger.info(f"Saved {len(questions)} question(s) to {questions_dir}")


def analyze(config: Config) -> None:
    questions = config.questions_list
    if not questions:
        logger.debug("No questions provided, skipping analysis")
        return

    logger.info(f"Starting Ollama analysis with {len(questions)} question(s)")

    _save_questions(questions, config.questions_dir)
    config.responses_dir.mkdir(parents=True, exist_ok=True)

    papers = list(config.papers_dir.glob("*.pdf"))
    if not papers:
        logger.warning(f"No PDFs found in {config.papers_dir}")
        return

    logger.info(f"Found {len(papers)} PDFs to analyze")

    for pdf_path in papers:
        paper_name = pdf_path.stem
        paper_responses_dir = config.responses_dir / paper_name
        paper_responses_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Analyzing {paper_name}")
        full_text = Ollama.read_pdf(pdf_path)
        chunks = Ollama.chunk_text(
            full_text, config.ollama_opts.max_context_tokens, config.max_chunks
        )
        logger.debug(f"Created {len(chunks)} chunk(s) for {paper_name}")

        for q_idx, question in enumerate(questions, start=1):
            response_file = paper_responses_dir / f"q{q_idx}.md"

            if response_file.exists():
                logger.debug(f"Skipping {response_file.name} (already exists)")
                continue

            chunk_texts = "\n\n---\n\n".join(chunks)
            result = Ollama.answer_question_for_paper(
                chunk_texts, question, config.ollama_opts
            )

            content = f"# Question {q_idx}\n\n{question}\n\n---\n\n# Response\n\n{result.response}"
            response_file.write_text(content, encoding="utf-8")
            logger.info(f"Saved {response_file}")

    logger.info("Ollama analysis complete")



import pytest
from paper_scraper.__global__ import TEST_SEED_PAPER_1, TEMP_OUTPUT_DIR


@pytest.mark.requires_ollama
def test_usage():
    config = Config(
        questions=["What is this paper about?"],
        papers_dir=TEMP_OUTPUT_DIR / "DOWNLOADED_PAPERS",
        output_dir=TEMP_OUTPUT_DIR,
        max_chunks=1,
    )
    analyze(config)
