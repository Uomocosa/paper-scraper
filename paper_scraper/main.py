from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

from paper_scraper import Grobid
from paper_scraper import OpenAlex
from paper_scraper.__global__ import DOWNLOADED_DIR
from paper_scraper.download_papers import Config as DownloadConfig


@dataclass
class Config(DownloadConfig):
    seed_papers: list[Path] | Path = field(default_factory=list)
    batch_size: int = 1
    extracted_references_path: Path | None = None
    extract_refs_from_output: bool = False


def _resolve_seed_papers(seed_papers: list[Path] | Path) -> list[Path]:
    if isinstance(seed_papers, Path):
        if seed_papers.suffix == ".txt":
            with open(seed_papers, "r") as f:
                paths = [Path(line.strip()) for line in f if line.strip()]
            logger.info(f"Loaded {len(paths)} paper paths from {seed_papers.name}")
            return paths
        return [seed_papers]
    return list(seed_papers)


def _extract_refs_sequential(papers: list[Path]) -> list[dict]:
    all_references = []
    for pdf_file in papers:
        if pdf_file.suffix.lower() == ".pdf":
            refs = Grobid.extract_references_from_pdf(pdf_file)
            logger.info(f"Extracted {len(refs)} references from {pdf_file.name}.")
            all_references.extend(refs)
    return all_references


def _extract_refs_parallel(papers: list[Path], batch_size: int) -> list[dict]:
    all_references = []
    pdf_files = [p for p in papers if p.suffix.lower() == ".pdf"]

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = {
            executor.submit(Grobid.extract_references_from_pdf, p): p for p in pdf_files
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
    dois: list[str], output_dir: Path, openalex_opts: OpenAlex.Options
) -> None:
    for doi in dois:
        OpenAlex.download_paper_from_doi(doi, output_dir, openalex_opts)


def _download_parallel(
    dois: list[str],
    output_dir: Path,
    openalex_opts: OpenAlex.Options,
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


def main(config: Config) -> None:
    logger.info("Checking Grobid connection...")
    Grobid.check_connection()
    logger.info("Grobid connection OK.")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.openalex_opts.setup_pyalex_key()

    seed_papers = _resolve_seed_papers(config.seed_papers)
    logger.info(f"Processing {len(seed_papers)} seed paper(s)")

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

    if config.download_filter.topics:
        dois = OpenAlex.get_dois_from_filter(config.download_filter)
        logger.info(f"Found {len(dois)} DOIs from filter")
        if config.batch_size > 1:
            _download_parallel(
                dois, config.output_dir, config.openalex_opts, config.batch_size
            )
        else:
            _download_sequential(dois, config.output_dir, config.openalex_opts)

    if seed_dois:
        OpenAlex.get_reference_dois.from_dois(
            seed_dois,
            config.download_reference_opts,
            config.openalex_opts,
        )

    if config.extract_refs_from_output:
        downloaded_papers = list(config.output_dir.glob("*.pdf"))
        if downloaded_papers:
            logger.info(f"Found {len(downloaded_papers)} papers in output_dir")
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
                    config.output_dir,
                    config.openalex_opts,
                    config.batch_size,
                )
            else:
                _download_sequential(
                    reference_dois, config.output_dir, config.openalex_opts
                )

    logger.info("Pipeline complete.")


def test_usage():
    from paper_scraper.__global__ import POLYPHOX_PAPER, REPO_DIR
    from paper_scraper import OpenAlex

    main(
        Config(
            seed_papers=[POLYPHOX_PAPER],
            output_dir=DOWNLOADED_DIR,
            openalex_opts=OpenAlex.Options(),
            download_filter=OpenAlex.get_dois_from_filter.Filter(
                topics=["T11948"],
                year_min=2022,
                max_papers=2,
            ),
            download_reference_opts=OpenAlex.get_reference_dois.Options(depth=1),
            batch_size=1,
            extracted_references_path=REPO_DIR / "test_output" / "refs.json",
            extract_refs_from_output=True,
        )
    )
