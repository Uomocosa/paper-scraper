from dataclasses import dataclass
import requests

import paper_scraper
from paper_scraper.__global__ import GROBID_URL
from paper_scraper import Error


@dataclass
class Options:
    timeout: float = 5.0


def check_connection(options: Options = Options()) -> None:
    base_url = GROBID_URL.rsplit("/api/", 1)[0] + "/api"
    try:
        response = requests.get(
            f"{base_url}/isalive",
            timeout=options.timeout,
        )
        if response.status_code != 200:
            raise Error.GrobidUnexpectedStatus(
                url=base_url, status_code=response.status_code
            )
    except requests.exceptions.ConnectionError as e:
        raise Error.GrobidConnectionRefused(url=base_url) from e
    except requests.exceptions.Timeout:
        raise Error.GrobidConnectionTimeout(url=base_url, timeout_s=options.timeout)


def test_usage():
    check_connection()
