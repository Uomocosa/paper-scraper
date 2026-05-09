import requests
import urllib3
from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.Error import ConnectionRefused, ConnectionTimeout
from loguru import logger


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def complete(
    messages: list[dict[str, str | list[str]]],
    options: Options,
) -> str:
    url = f"{options.base_url}/api/chat"  # Modern endpoint with vision support
    
    payload = {
        "model": options.model,
        "messages": messages,
        "stream": False,
    }
    
    # Only add options if they're set (some models don't support all options)
    if options.temperature != 1.0 or options.max_context_tokens != 256:
        payload["options"] = {
            "temperature": options.temperature,
            "num_ctx": options.max_context_tokens,
        }

    try:
        logger.debug(f"Sending request to {url} with model {options.model}")
        response = requests.post(url, json=payload, timeout=120)
    except (requests.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
        raise ConnectionRefused(url=url) from e
    except urllib3.exceptions.MaxRetryError as e:
        if isinstance(e.reason, urllib3.exceptions.ConnectTimeoutError):
            raise ConnectionTimeout(url=url, timeout_s=120.0) from e
        raise ConnectionRefused(url=url) from e

    response.raise_for_status()
    data = response.json()
    
    # Validate response structure
    if "message" not in data or "content" not in data["message"]:
        logger.error(f"Unexpected response structure: {data}")
        raise ValueError(f"Unexpected Ollama response format: {data}")
    
    return data["message"]["content"]


import pytest


@pytest.mark.above10s
def test_usage():
    from paper_scraper import Ollama

    ollama_options = Ollama.Options()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    logger.info(
        f"Connecting to Ollama at {ollama_options.base_url} (Model: {ollama_options.model})..."
    )
    answer = complete(messages=messages, options=ollama_options)
    logger.info(f"Answer: {answer}")
