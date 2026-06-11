import re
import requests
from pathlib import Path

import pyalex
from pyalex import Works
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import paper_scraper
from paper_scraper import OpenAlex
from loguru import logger

Result = OpenAlex.Result
Status = OpenAlex.Result.Status
OpenAlexOptions = OpenAlex.Options.Options


def _make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _collect_pdf_urls(work: dict, doi: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str | None):
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    oa = work.get("open_access", {})
    add(oa.get("oa_url"))

    primary = work.get("primary_location") or {}
    add(primary.get("pdf_url"))
    add(primary.get("landing_page_url"))

    best_oa = work.get("best_oa_location") or {}
    add(best_oa.get("pdf_url"))
    add(best_oa.get("landing_page_url"))

    for loc in work.get("locations") or []:
        add(loc.get("pdf_url"))
        add(loc.get("landing_page_url"))

    add(f"https://doi.org/{doi}")

    return urls


def _try_download(url: str, session: requests.Session, doi: str) -> bytes | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.8",
    }
    try:
        resp = session.get(url, timeout=30, headers=headers)
        if resp.status_code != 200:
            logger.debug(f"HTTP {resp.status_code} for {doi} from {url}")
            return None
        if not resp.content.startswith(b"%PDF"):
            logger.debug(f"Not a PDF for {doi} from {url}")
            return None
        return resp.content
    except Exception as e:
        logger.debug(f"Failed to fetch {url} for {doi}: {e}")
        return None


def download_paper_from_doi(
    doi: str,
    output_dir: Path,
    openalex_options: OpenAlexOptions = OpenAlexOptions(),
) -> OpenAlex.Result:
    openalex_options.setup_pyalex_key()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not doi or not isinstance(doi, str):
        logger.warning(f"Skipping invalid DOI: {doi}")
        return Result(Status.ERROR)

    doi = doi.strip()
    if not doi.startswith("10."):
        logger.warning(f"Skipping invalid DOI format: {doi}")
        return Result(Status.ERROR)

    lookup_doi = f"doi:{doi}"
    try:
        work = Works()[lookup_doi]
    except Exception as e:
        logger.error(f"Failed to fetch DOI {doi}: {e}")
        return Result(Status.ERROR)

    if not work:
        logger.warning(f"Work not found for DOI: {doi}")
        return Result(Status.ERROR)

    pdf_urls = _collect_pdf_urls(work, doi)
    if not pdf_urls:
        logger.warning(f"No URL found for DOI: {doi}")
        return Result(Status.NOT_OPEN_ACCESS)

    title = work.get("title", "unknown")
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.pdf"
    filepath = output_dir / filename

    session = _make_session()
    for url in pdf_urls:
        content = _try_download(url, session, doi)
        if content:
            filepath.write_bytes(content)
            logger.info(f"Downloaded: {filename}")
            return Result(Status.SUCCESS, filepath)

    logger.warning(
        f"All {len(pdf_urls)} URLs failed for DOI: {doi}"
    )
    return Result(Status.NOT_OPEN_ACCESS)


def sanitize_filename(text: str) -> str:
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:200]


def test_usage():
    from paper_scraper.__global__ import TEMP_DOWLOADED_PAPERS_DIR

    download_paper_from_doi("10.3390/w12061530", TEMP_DOWLOADED_PAPERS_DIR)
