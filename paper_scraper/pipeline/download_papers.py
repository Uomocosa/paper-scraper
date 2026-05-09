from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from paper_scraper import OpenAlex
from paper_scraper.__global__ import OUTPUT_DIR


OpenAlexOptions = OpenAlex.Options.Options
DownloadReferenceOptions = OpenAlex.get_reference_dois.Options


@dataclass
class Config:
    dois: list[str] = field(default_factory=list)
    output_dir: Path = OUTPUT_DIR / "DOWNLOADED_PAPERS"
    papers_dir: Path = OUTPUT_DIR / "DOWNLOADED_PAPERS"
    openalex_opts: OpenAlexOptions = field(default_factory=OpenAlexOptions)
    batch_size: int = 1
    extract_refs: bool = False
    reference_opts: DownloadReferenceOptions = field(
        default_factory=DownloadReferenceOptions
    )


def download_papers(config: Config) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.papers_dir.mkdir(parents=True, exist_ok=True)
    config.openalex_opts.setup_pyalex_key()

    if config.batch_size > 1:
        with ThreadPoolExecutor(max_workers=config.batch_size) as executor:
            futures = [
                executor.submit(
                    OpenAlex.download_paper_from_doi,
                    doi,
                    config.papers_dir,
                    config.openalex_opts,
                )
                for doi in config.dois
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Download failed: {e}")
    else:
        for doi in config.dois:
            try:
                OpenAlex.download_paper_from_doi(
                    doi, config.papers_dir, config.openalex_opts
                )
            except Exception as e:
                logger.error(f"Download failed for {doi}: {e}")

    if config.extract_refs:
        downloaded_papers = list(config.papers_dir.glob("*.pdf"))
        if downloaded_papers:
            logger.info(f"Found {len(downloaded_papers)} papers in papers_dir")
            reference_dois = OpenAlex.get_reference_dois.from_papers(
                downloaded_papers,
                config.reference_opts,
            )
            logger.info(
                f"Found {len(reference_dois)} reference DOIs from downloaded papers"
            )

            if config.batch_size > 1:
                with ThreadPoolExecutor(max_workers=config.batch_size) as executor:
                    futures = [
                        executor.submit(
                            OpenAlex.download_paper_from_doi,
                            doi,
                            config.papers_dir,
                            config.openalex_opts,
                        )
                        for doi in reference_dois
                    ]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Download failed: {e}")
            else:
                for doi in reference_dois:
                    try:
                        OpenAlex.download_paper_from_doi(
                            doi, config.papers_dir, config.openalex_opts
                        )
                    except Exception as e:
                        logger.error(f"Download failed for {doi}: {e}")



import pytest
@pytest.mark.above10s
def test_usage():
    from paper_scraper.__global__ import TEMP_OUTPUT_DIR
    config = Config(
        dois=["10.3390/w12061530"],
        papers_dir=TEMP_OUTPUT_DIR / "DOWNLOADED_PAPERS",
        output_dir=TEMP_OUTPUT_DIR / "DOWNLOADED_PAPERS",
        batch_size=1,
    )
    download_papers(config)
