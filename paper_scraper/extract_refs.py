import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from paper_scraper.__global__ import SEED_DIR, GROBID_URL, REPO_DIR
from paper_scraper.Error.GrobidConnection import (
    ConnectionRefused,
    ConnectionTimeout,
    UnexpectedStatus,
)


def check_grobid_connection(timeout: float = 5.0) -> None:
    base_url = GROBID_URL.rsplit("/api/", 1)[0] + "/api"
    try:
        response = requests.get(
            f"{base_url}/status",
            timeout=timeout,
        )
        if response.status_code != 200:
            raise UnexpectedStatus(url=base_url, status_code=response.status_code)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionRefused(url=base_url) from e
    except requests.exceptions.Timeout:
        raise ConnectionTimeout(url=base_url, timeout_s=timeout)


def extract_references_from_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    print(f"🤖 Sending {pdf_path.name} to Grobid...")

    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf_path.name, f, "application/pdf")}
            response = requests.post(GROBID_URL, files=files)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionRefused(url=GROBID_URL) from e

    if response.status_code != 200:
        raise UnexpectedStatus(url=GROBID_URL, status_code=response.status_code)

    # Grobid returns TEI XML. We use BeautifulSoup to parse it.
    soup = BeautifulSoup(response.text, "xml")
    extracted_refs = []

    # In TEI XML, citations are stored in <biblStruct> tags
    for bibl in soup.find_all("biblStruct"):
        ref_data = {}

        # 1. Try to get the Title
        title_tag = bibl.find("title")
        if title_tag:
            ref_data["title"] = title_tag.text.strip()

        # 2. Try to get the DOI (This is the golden ticket for downloading)
        doi_tag = bibl.find("idno", type="DOI")
        if doi_tag:
            ref_data["doi"] = doi_tag.text.strip()

        if ref_data:
            extracted_refs.append(ref_data)

    return extracted_refs


def test_():
    print("Checking Grobid connection...")
    check_grobid_connection()
    print("Grobid connection OK.\n")

    all_references = []

    for pdf_file in SEED_DIR.iterdir():
        if pdf_file.suffix.lower() == ".pdf":
            refs = extract_references_from_pdf(pdf_file)

            print(f"✅ Extracted {len(refs)} references from {pdf_file.name}.")
            all_references.extend(refs)

    with open(REPO_DIR / "extracted_references.json", "w", encoding="utf-8") as f:
        json.dump(all_references, f, indent=4)

    print(
        f"\n🎉 Done! Saved a total of {len(all_references)} references to extracted_references.json"
    )
