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
