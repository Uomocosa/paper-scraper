import pytest
from paper_scraper import Grobid

@pytest.fixture(autouse=True)
def skip_by_grobid_status(request):
    if request.node.get_closest_marker("requires_grobid"):
        try:
            Grobid.check_connection()
        except Exception as e:
            pytest.skip(f"Grobid service unavailable: {e}")
