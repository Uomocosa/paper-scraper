"""
# PIPELINE:
1. Extract references from seed papers (Grobid)
2. Get DOIs from references + filter
3. Download papers
4. Analyze with Ollama
"""

from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

import pytest

from paper_scraper.__global__ import (
    OUTPUT_DIR,
    SEED_PAPERS_DIR,
    TEST_SEED_PAPER_1,
    TEMP_OUTPUT_DIR,
)
from paper_scraper import OpenAlex, Ollama
from paper_scraper.pipeline import extract_refs, get_dois, download_papers, analyze


OpenAlexOptions = OpenAlex.Options.Options
DownloadFilter = OpenAlex.get_dois_from_filter.Filter
DownloadReferenceOptions = OpenAlex.get_reference_dois.Options
OllamaOptions = Ollama.Options.Options


@dataclass
class Config:
    seed_papers: list[Path] | Path | None = None
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)
    batch_size: int = 1

    openalex_opts: OpenAlexOptions = field(default_factory=OpenAlexOptions)
    filter: DownloadFilter = field(default_factory=DownloadFilter)
    download_reference_opts: DownloadReferenceOptions = field(
        default_factory=DownloadReferenceOptions
    )

    ollama_opts: OllamaOptions = field(
        default_factory=lambda: OllamaOptions(
            model="gemma4:e4b",
            max_context_tokens=32768,
        )
    )
    questions: list[str] | Path | None = None
    max_chunks: int = 10

    extract_refs_from_seed: bool = True
    extract_refs_from_output: bool = False

    @property
    def papers(self) -> list[Path]:
        if self.seed_papers is None:
            papers = list(SEED_PAPERS_DIR.glob("*.pdf"))
            logger.debug(f"Auto-discovered {len(papers)} PDFs in SEED_PAPERS_DIR")
            return papers
        if isinstance(self.seed_papers, Path):
            return (
                [self.seed_papers] if self.seed_papers.suffix.lower() == ".pdf" else []
            )
        return [p for p in self.seed_papers if p.suffix.lower() == ".pdf"]

    @property
    def papers_dir(self) -> Path:
        return self.output_dir / "DOWNLOADED_PAPERS"

    @property
    def questions_dir(self) -> Path:
        return self.output_dir / "QUESTIONS"

    @property
    def responses_dir(self) -> Path:
        return self.output_dir / "RESPONSES"

    @property
    def extracted_references_path(self) -> Path:
        return self.output_dir / "extracted_references.json"

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



@dataclass
class LocalTestConfig(Config):
    ollama_opts: OllamaOptions = field(default_factory = lambda: OllamaOptions(
        model="tinyllama",
        max_context_tokens=256,
    ))
    batch_size: int = 1
    max_chunks: int = 1


def main(config: Config) -> None:
    extract_refs(
        extract_refs.Config(
            seed_papers=config.seed_papers,
            output_dir=config.output_dir,
            batch_size=config.batch_size,
        )
    )

    dois = get_dois(
        get_dois.Config(
            extracted_references_path=config.extracted_references_path,
            filter=config.filter,
            output_dir=config.output_dir,
        )
    )

    download_papers(
        download.Config(
            dois=dois,
            output_dir=config.papers_dir,
            papers_dir=config.papers_dir,
            openalex_opts=config.openalex_opts,
            batch_size=config.batch_size,
            extract_refs=config.extract_refs_from_output,
            reference_opts=config.download_reference_opts,
        )
    )

    analyze(
        analyze.Config(
            questions=config.questions,
            papers_dir=config.papers_dir,
            output_dir=config.output_dir,
            ollama_opts=config.ollama_opts,
            max_chunks=config.max_chunks,
        )
    )

    logger.info("Pipeline complete.")


"""
IMPORTANT!
Each test MUST use a temporary directory to avoid polluting the test environment.
It cannot use the global OUTPUT_DIR
"""

@pytest.mark.requires_grobid
@pytest.mark.above10s
def test_extract_refs_only():
    """Extract references from seed papers only."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dir = Path(tmpdir) / "output"
        main(
            LocalTestConfig(
                seed_papers=[TEST_SEED_PAPER_1],
                output_dir=custom_dir,
            )
        )


@pytest.mark.requires_ollama
@pytest.mark.above10s
def test_analyze_existing_pdfs():
    """Analyze a local seed paper with Ollama (1 call)."""
    main(
        LocalTestConfig(
            seed_papers=[TEST_SEED_PAPER_1],
            output_dir=TEMP_OUTPUT_DIR,
            questions=["What is this paper about?"],
            extract_refs_from_seed=False,
        )
    )


def test_questions_dir_creation():
    """Test that questions are saved to correct directory."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        questions_dir = Path(tmpdir) / "QUESTIONS"
        questions = ["Question 1?", "Question 2?"]
        analyze._save_questions(questions, questions_dir)

        assert (questions_dir / "q1.md").exists()
        assert (questions_dir / "q2.md").exists()
        assert (questions_dir / "q1.md").read_text() == "Question 1?"
        assert (questions_dir / "q2.md").read_text() == "Question 2?"


def test_custom_output_dir():
    """Test Config with custom output directory."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dir = Path(tmpdir) / "custom_output"
        config = LocalTestConfig(
            seed_papers=[TEST_SEED_PAPER_1],
            output_dir=custom_dir,
        )

        assert config.papers_dir == custom_dir / "DOWNLOADED_PAPERS"
        assert config.questions_dir == custom_dir / "QUESTIONS"
        assert config.responses_dir == custom_dir / "RESPONSES"
        assert (
            config.extracted_references_path == custom_dir / "extracted_references.json"
        )


def test_resolved_seed_papers():
    """Test seed_papers resolution logic."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        custom_dir = Path(tmpdir) / "output"

        config = LocalTestConfig(seed_papers=[TEST_SEED_PAPER_1], output_dir=custom_dir)
        assert len(config.papers) == 1
        assert config.papers[0] == TEST_SEED_PAPER_1

        config_single = LocalTestConfig(
            seed_papers=TEST_SEED_PAPER_1, output_dir=custom_dir
        )
        assert len(config_single.papers) == 1

        config_non_pdf = LocalTestConfig(seed_papers=Path(__file__), output_dir=custom_dir)
        assert len(config_non_pdf.papers) == 0
