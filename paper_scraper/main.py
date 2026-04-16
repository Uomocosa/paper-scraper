from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

import pytest
from paper_scraper import Grobid
from paper_scraper import OpenAlex
from paper_scraper import Ollama
from paper_scraper.__global__ import SEED_DIR, OUTPUT_DIR

OpenAlexOptions = OpenAlex.Options.Options
DownloadFilter = OpenAlex.get_dois_from_filter.Filter
DownloadReferenceOptions = OpenAlex.get_reference_dois.Options
OllamaOptions = Ollama.Options.Options


@dataclass
class Config:
    seed_papers: list[Path] | Path | None = None
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)

    openalex_opts: OpenAlexOptions = field(default_factory=OpenAlexOptions)
    download_filter: DownloadFilter = field(default_factory=DownloadFilter)
    download_reference_opts: DownloadReferenceOptions = field(
        default_factory=DownloadReferenceOptions
    )

    ollama_opts: OllamaOptions = field(default_factory=OllamaOptions)
    questions: list[str] | Path | None = None
    max_chunks: int = 1

    batch_size: int = 1
    extract_refs_from_seed: bool = True
    extract_refs_from_output: bool = False

    def __post_init__(self):
        if self.seed_papers is None:
            self.seed_papers = list(SEED_DIR.glob("*.pdf"))
            logger.debug(f"Auto-discovered {len(self.seed_papers)} PDFs in SEED_DIR")
        elif isinstance(self.seed_papers, Path) and self.seed_papers.suffix == ".txt":
            self._load_from_txt(
                self.seed_papers, lambda paths: setattr(self, "seed_papers", paths)
            )

        if isinstance(self.questions, Path) and self.questions.suffix == ".txt":
            self._load_from_txt(self.questions, lambda q: setattr(self, "questions", q))

    def _load_from_txt(self, path: Path, setter) -> None:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(lines)} items from {path.name}")
        setter(lines)

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
    def resolved_seed_papers(self) -> list[Path]:
        papers = self.seed_papers
        if isinstance(papers, Path):
            return [papers] if papers.suffix.lower() == ".pdf" else []
        return [p for p in papers if p.suffix.lower() == ".pdf"]

    @property
    def resolved_questions(self) -> list[str]:
        if self.questions is None:
            return []
        if isinstance(self.questions, list):
            return self.questions
        return []


def _extract_refs_sequential(papers: list[Path]) -> list[dict]:
    all_references = []
    for pdf_file in papers:
        refs = Grobid.extract_references_from_pdf(pdf_file)
        logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
        all_references.extend(refs)
    return all_references


def _extract_refs_parallel(papers: list[Path], batch_size: int) -> list[dict]:
    all_references = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = {
            executor.submit(Grobid.extract_references_from_pdf, p): p for p in papers
        }
        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                refs = future.result()
                logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
                all_references.extend(refs)
            except Exception as e:
                logger.error(f"Failed to extract refs from {pdf_file.name}: {e}")
    return all_references


def _download_sequential(
    dois: list[str], output_dir: Path, openalex_opts: OpenAlexOptions
) -> None:
    for doi in dois:
        OpenAlex.download_paper_from_doi(doi, output_dir, openalex_opts)


def _download_parallel(
    dois: list[str],
    output_dir: Path,
    openalex_opts: OpenAlexOptions,
    batch_size: int,
) -> None:
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [
            executor.submit(
                OpenAlex.download_paper_from_doi, doi, output_dir, openalex_opts
            )
            for doi in dois
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Download failed: {e}")


def _save_questions(questions: list[str], questions_dir: Path) -> None:
    questions_dir.mkdir(parents=True, exist_ok=True)
    for q_idx, question in enumerate(questions, start=1):
        question_file = questions_dir / f"q{q_idx}.md"
        question_file.write_text(question, encoding="utf-8")
    logger.info(f"Saved {len(questions)} question(s) to {questions_dir}")


def _analyze_with_ollama(config: Config, questions: list[str]) -> None:
    if not questions:
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


def main(config: Config) -> None:
    logger.info("Checking Grobid connection...")
    Grobid.check_connection()
    logger.info("Grobid connection OK.")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.papers_dir.mkdir(parents=True, exist_ok=True)
    config.openalex_opts.setup_pyalex_key()

    seed_papers = config.resolved_seed_papers
    logger.info(f"Processing {len(seed_papers)} seed paper(s)")

    all_references = []
    seed_dois = []

    if config.extract_refs_from_seed and seed_papers:
        if config.batch_size > 1:
            all_references = _extract_refs_parallel(seed_papers, config.batch_size)
        else:
            all_references = _extract_refs_sequential(seed_papers)

        if config.extracted_references_path:
            import json

            with open(config.extracted_references_path, "w", encoding="utf-8") as f:
                json.dump(all_references, f, indent=4)
            logger.info(
                f"Saved {len(all_references)} references to {config.extracted_references_path}"
            )

        seed_dois = [ref.get("doi") for ref in all_references if ref.get("doi")]
        logger.info(f"Found {len(seed_dois)} DOIs from seed papers")

    has_filter = bool(config.download_filter.topics)

    if has_filter:
        dois = OpenAlex.get_dois_from_filter(config.download_filter)
        logger.info(f"Found {len(dois)} DOIs from filter")
        if config.batch_size > 1:
            _download_parallel(
                dois, config.papers_dir, config.openalex_opts, config.batch_size
            )
        else:
            _download_sequential(dois, config.papers_dir, config.openalex_opts)

    if seed_dois:
        OpenAlex.get_reference_dois.from_dois(
            seed_dois,
            config.papers_dir,
            config.download_reference_opts,
            config.openalex_opts,
        )

    if config.extract_refs_from_output:
        downloaded_papers = list(config.papers_dir.glob("*.pdf"))
        if downloaded_papers:
            logger.info(f"Found {len(downloaded_papers)} papers in papers_dir")
            reference_dois = OpenAlex.get_reference_dois.from_papers(
                downloaded_papers,
                config.download_reference_opts,
            )
            logger.info(
                f"Found {len(reference_dois)} reference DOIs from downloaded papers"
            )
            if config.batch_size > 1:
                _download_parallel(
                    reference_dois,
                    config.papers_dir,
                    config.openalex_opts,
                    config.batch_size,
                )
            else:
                _download_sequential(
                    reference_dois, config.papers_dir, config.openalex_opts
                )

    questions = config.resolved_questions
    if questions:
        _analyze_with_ollama(config, questions)

    logger.info("Pipeline complete.")


@pytest.mark.above10s
def test_usage():
    from paper_scraper.__global__ import POLYPHOX_PAPER

    main(
        Config(
            seed_papers=[POLYPHOX_PAPER],
            extract_refs_from_seed=True,
            extract_refs_from_output=True,
            download_reference_opts=DownloadReferenceOptions(depth=1),
        )
    )


@pytest.mark.above10s
def test_usage_ollama():
    from paper_scraper.__global__ import POLYPHOX_PAPER

    main(
        Config(
            seed_papers=[POLYPHOX_PAPER],
            extract_refs_from_seed=True,
            questions=[
                "What are the main adsorption mechanisms described in this paper?",
                "What are the key findings about pharmaceutical adsorption?",
            ],
            ollama_opts=OllamaOptions(),
            max_chunks=1,
        )
    )


def test_config_defaults():
    config = Config()
    assert len(config.seed_papers) == 2
    assert config.output_dir == OUTPUT_DIR
    assert config.batch_size == 1
    assert config.extract_refs_from_seed is True
    assert config.extract_refs_from_output is False


def test_config_seed_papers_loading():
    from paper_scraper.__global__ import POLYPHOX_PAPER

    config = Config(seed_papers=POLYPHOX_PAPER)
    assert config.resolved_seed_papers == [POLYPHOX_PAPER]

    config = Config(seed_papers=[POLYPHOX_PAPER])
    assert config.resolved_seed_papers == [POLYPHOX_PAPER]


def test_config_questions_loading():
    config = Config(questions=["Q1", "Q2"])
    assert config.resolved_questions == ["Q1", "Q2"]


def test_config_output_dirs():
    config = Config(output_dir=Path("/test/output"))
    assert config.papers_dir == Path("/test/output/DOWNLOADED_PAPERS")
    assert config.questions_dir == Path("/test/output/QUESTIONS")
    assert config.responses_dir == Path("/test/output/RESPONSES")
    assert config.extracted_references_path == Path(
        "/test/output/extracted_references.json"
    )
