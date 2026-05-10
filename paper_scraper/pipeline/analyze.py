from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from paper_scraper.__global__ import OUTPUT_DIR
from paper_scraper import Ollama
from paper_scraper.Ollama.__global__ import HandlePDFType
import lele

OllamaOptions = Ollama.Options.Options

@dataclass
class Config:
    questions: list[str] | Path | None = None
    papers_dir: Path = OUTPUT_DIR / "DOWNLOADED_PAPERS"
    output_dir: Path = OUTPUT_DIR
    ollama_opts: OllamaOptions = field(
        default_factory=lambda: OllamaOptions(model="tinyllama")
    )
    max_chunks: int = 1
    handle_pdfs: HandlePDFType = "pdf2text"

    @property
    def questions_list(self) -> list[str]:
        if self.questions is None: 
            return []
        if isinstance(self.questions, list): 
            questions = lele.List.flatten(self.questions)
            questions = [Config.get_questions_from_str(q) for q in questions]
            questions = lele.List.flatten(questions)
            return list(questions)
        return Config.get_questions_from_str(self.questions)
    
    @staticmethod
    def get_questions_from_str(question: str) -> list[str]:
        path = Path(question)
        if not path.exists(): return question
        if path.exists() and path.is_dir():
            md_files = sorted(path.glob("*.md"))
            if not md_files:
                logger.error(f"No .md file in {path} to get question from")
                return []
            questions = []
            for md_file in md_files:
                with open(md_file, "r", encoding="utf-8") as f:
                    questions.append(f.read().strip())
            return questions
        if path.exists() and path.is_file():
            if path.suffix.lower() != ".md":
                logger.error(f"Expected .md file, found {path.suffix}")
                return []
            with open(path, "r", encoding="utf-8") as f:
                return [f.read().strip()]
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


def get_analysis_results(config: Config) -> list[Path]:
    if not config.responses_dir.exists():
        return []
    return sorted(config.responses_dir.rglob("*.md"))


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

        handle_pdf = Ollama.get_handle_pdf_function(config.handle_pdfs)
        pdf_content = handle_pdf(pdf_path)
        
        if config.handle_pdfs == "pdf2image":
            chunks = pdf_content
        else:
            chunks = Ollama.chunk_text(
                pdf_content, config.ollama_opts.max_context_tokens, config.max_chunks
            )
        logger.debug(f"Created {len(chunks)} chunk(s) for {paper_name}")

        for q_idx, question in enumerate(questions, start=1):
            response_file = paper_responses_dir / f"q{q_idx}.md"

            if response_file.exists():
                logger.debug(f"Skipping {response_file.name} (already exists)")
                continue

            chunk_texts = "\n\n---\n\n".join(chunks) if isinstance(chunks[0], str) else ""

            result = Ollama.answer_question_for_paper(
                chunk_texts,
                question,
                config.ollama_opts,
                pdf_path=pdf_path,
                handle_pdfs=config.handle_pdfs,
            )

            content = f"# Question {q_idx}\n\n{question}\n\n---\n\n# Response\n\n{result.response}"
            response_file.write_text(content, encoding="utf-8")
            logger.info(f"Saved {response_file}")

    logger.info("Ollama analysis complete")



import pytest
import shutil
from paper_scraper.__global__ import TEST_SEED_PAPER_1, TEMP_OUTPUT_DIR


@pytest.mark.requires_ollama
class Tests():
    base_test_config = Config(
        questions=["Hi there!"],
        papers_dir=TEMP_OUTPUT_DIR / "DOWNLOADED_PAPERS",
        output_dir=TEMP_OUTPUT_DIR,
        max_chunks=1,
        ollama_opts=OllamaOptions(
            system_prompt="Greet me in the tone of the paper",
        )
    )

    def print_results(self, config):
        paths = get_analysis_results(config)
        print(paths)
        first_file = paths[0]
        print("ANALYSIS RESULTS:")
        print(f"\n{first_file.relative_to(config.responses_dir)}:")
        print(first_file.read_text(encoding="utf-8"))

    
    def test_pdf2text(self):
        if TEMP_OUTPUT_DIR.exists(): shutil.rmtree(TEMP_OUTPUT_DIR)
        config = self.base_test_config
        config.papers_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEST_SEED_PAPER_1, config.papers_dir / TEST_SEED_PAPER_1.name)
        analyze(config)
        self.print_results(config)

    def test_pdf2image(self):
        if TEMP_OUTPUT_DIR.exists(): shutil.rmtree(TEMP_OUTPUT_DIR)
        config = self.base_test_config
        config.ollama_opts.handle_pdfs = "pdf2image"
        config.papers_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEST_SEED_PAPER_1, config.papers_dir / TEST_SEED_PAPER_1.name)
        analyze(config)
        self.print_results(config)

    def test_read_question_from_folder(self):
        if TEMP_OUTPUT_DIR.exists(): shutil.rmtree(TEMP_OUTPUT_DIR)
        config = self.base_test_config
        config.questions = "./QUESTIONS"
        config.papers_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEST_SEED_PAPER_1, config.papers_dir / TEST_SEED_PAPER_1.name)
        analyze(config)
        self.print_results(config)
