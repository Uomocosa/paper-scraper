from dataclasses import dataclass

import pytest
import requests

from paper_scraper.__global__ import GROBID_URL
from paper_scraper.Grobid.Error import (
    ConnectionRefused,
    ConnectionTimeout,
    UnexpectedStatus,
)


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
            raise UnexpectedStatus(url=base_url, status_code=response.status_code)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionRefused(url=base_url) from e
    except requests.exceptions.Timeout:
        raise ConnectionTimeout(url=base_url, timeout_s=options.timeout)


@pytest.mark.requires_grobid
def test_usage():
    check_connection()
