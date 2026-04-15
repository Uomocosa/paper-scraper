from dataclasses import dataclass
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from paper_scraper.__global__ import GROBID_URL, SEED_DIR
from paper_scraper.Grobid.Error import ConnectionRefused, UnexpectedStatus
from loguru import logger


@dataclass
class Options:
    pass


def extract_references_from_pdf(pdf_path, options: Options = Options()) -> list[dict]:
    pdf_path = Path(pdf_path)

    logger.info(f"Sending {pdf_path.name} to Grobid...")

    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf_path.name, f, "application/pdf")}
            response = requests.post(GROBID_URL, files=files)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionRefused(url=GROBID_URL) from e

    if response.status_code != 200:
        raise UnexpectedStatus(url=GROBID_URL, status_code=response.status_code)

    soup = BeautifulSoup(response.text, "xml")
    extracted_refs = []

    for bibl in soup.find_all("biblStruct"):
        ref_data = {}

        title_tag = bibl.find("title")
        if title_tag:
            ref_data["title"] = title_tag.text.strip()

        doi_tag = bibl.find("idno", type="DOI")
        if doi_tag:
            ref_data["doi"] = doi_tag.text.strip()

        if ref_data:
            extracted_refs.append(ref_data)

    return extracted_refs


def test_usage():
    pdf_path = (
        SEED_DIR
        / "2‐Oxazoline‐Based Polymer for Pharmaceutical Products Adsorption in Aqueous (1).pdf"
    )
    extracted_refs = extract_references_from_pdf(pdf_path)
    logger.info("extracted_refs:\n" + "\n".join(str(ref) for ref in extracted_refs))
