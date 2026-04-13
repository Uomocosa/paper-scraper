from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from paper_scraper.__global__ import ENV_FILE

load_dotenv(ENV_FILE)

def get_pyalex_api_key() -> str | None:
    import os
    return os.getenv("PYALEX_API_KEY") or None


def test_usage():
    key = get_pyalex_api_key()
    logger.info(f"Loaded API key: {'<set>' if key else '<not set>'}")
