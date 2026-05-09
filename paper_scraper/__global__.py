from pathlib import Path

SRC_DIR = Path(__file__).parent
REPO_DIR = SRC_DIR.parent
SEED_PAPERS_DIR = REPO_DIR / "SEED_PAPERS"
OUTPUT_DIR = REPO_DIR / "OUTPUT_DIR"
GROBID_URL = "http://localhost:8070/api/processReferences"
ENV_FILE = REPO_DIR.parent / ".env"

from joblib import Memory

CACHE_MEMORY = Memory(location=".cache_dir", verbose=0)

HELPER_DIR = SRC_DIR / "__HELPER_DIR__"
HELPER_DIR.mkdir(parents=True, exist_ok=True)
TEMP_OUTPUT_DIR = HELPER_DIR / "TEMP_OUTPUT_DIR"
TEMP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DOWLOADED_PAPERS_DIR = HELPER_DIR / "DOWNLOADED_PAPERS"
TEMP_DOWLOADED_PAPERS_DIR.mkdir(parents=True, exist_ok=True)

FIXTURES_DIR = HELPER_DIR / "fixtures"
TEST_SEED_PAPER_1 = FIXTURES_DIR / "attention_is_all_you_need.pdf"
TEST_SEED_PAPER_2 = FIXTURES_DIR / "bert_pre-training.pdf"
POLYPHOX_PAPER = TEST_SEED_PAPER_1  # Legacy alias

assert SRC_DIR.exists(), f"SRC_DIR does not exist: {SRC_DIR}"
assert REPO_DIR.exists(), f"REPO_DIR does not exist: {REPO_DIR}"
assert SEED_PAPERS_DIR.exists(), f"SEED_PAPERS_DIR does not exist: {SEED_PAPERS_DIR}"
TEMP_DOWLOADED_PAPERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def test_usage():
    pass
