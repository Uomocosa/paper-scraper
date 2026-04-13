from pathlib import Path

SRC_DIR = Path(__file__).parent
REPO_DIR = SRC_DIR.parent
PAPERS_DIR = REPO_DIR / "PAPERS"
SEED_DIR = PAPERS_DIR / "SEED"
DOWNLOADED_DIR = PAPERS_DIR / "DOWNLOADED"
GROBID_URL = "http://localhost:8070/api/processReferences"
EXTRACTED_REFERENCES = REPO_DIR / "PAPERS" / "SEED" / "extracted_references.json"
ENV_FILE = REPO_DIR.parent / ".env"

assert SRC_DIR.exists(), f"SRC_DIR does not exist: {SRC_DIR}"
assert REPO_DIR.exists(), f"REPO_DIR does not exist: {REPO_DIR}"
assert SEED_DIR.exists(), f"SEED_DIR does not exist: {SEED_DIR}"
DOWNLOADED_DIR.mkdir(parents=True, exist_ok=True)


def test_usage():
    pass
