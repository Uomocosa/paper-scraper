import pytest
from paper_scraper import Grobid
from paper_scraper import Ollama


@pytest.fixture(autouse=True)
def skip_by_grobid_status(request):
    if request.node.get_closest_marker("requires_grobid"):
        try:
            Grobid.check_connection()
        except Exception as e:
            pytest.skip(f"Grobid service unavailable: {e}")

@pytest.fixture(autouse=True)
def skip_by_ollama_status(request):
    if request.node.get_closest_marker("requires_ollama"):
        try:
            Ollama.check_connection()
        except Exception as e:
            pytest.skip(f"Ollama service unavailable: {e}")

@pytest.fixture(autouse=True)
def skip_by_opencode_go_key_status(request):
    if request.node.get_closest_marker("requires_opencode_go_key"):
        from dotenv import load_dotenv
        from paper_scraper.__global__ import ENV_FILE
        load_dotenv(ENV_FILE)
        import os
        if not os.environ.get("OPENCODE_GO_KEY"):
            pytest.skip("OPENCODE_GO_KEY not set in environment")
