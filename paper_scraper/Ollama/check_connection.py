from dataclasses import dataclass

import requests
import urllib3

from paper_scraper.Ollama.Options import Options as OllamaOptions
from paper_scraper.Ollama.Error import (
    ConnectionRefused,
    ConnectionTimeout,
)


@dataclass
class Options(OllamaOptions):
    timeout_s: float = 5.0


def check_connection(options: Options = Options()) -> None:
    url = f"{options.base_url}/api/tags"
    
    try:
        response = requests.get(
            url,
            timeout=options.timeout_s,
        )
        response.raise_for_status()
    except (requests.exceptions.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
        raise ConnectionRefused(url=options.base_url) from e
    except (requests.exceptions.Timeout, urllib3.exceptions.ConnectTimeoutError) as e:
        raise ConnectionTimeout(url=options.base_url, timeout_s=options.timeout_s) from e


import pytest


@pytest.mark.requires_ollama
def test_usage():
    check_connection()
