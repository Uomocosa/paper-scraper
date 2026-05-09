import requests
import urllib3
import base64
from pathlib import Path
from paper_scraper.Ollama.Options import Options
from paper_scraper.Ollama.Error import ConnectionRefused, ConnectionTimeout
from loguru import logger


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _encode_image_to_base64(image_path: str | Path) -> str:
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def complete(
    messages: list[dict[str, str | list[str] | list[dict]]],
    options: Options,
) -> str:
    url = f"{options.base_url}/api/chat"  # Modern endpoint with vision support
    
    processed_messages = _process_messages(messages)
    
    payload = {
        "model": options.model,
        "messages": processed_messages,
        "stream": False,
    }
    
    if options.temperature != 1.0 or options.max_context_tokens != 256:
        payload["options"] = {
            "temperature": options.temperature,
            "num_ctx": options.max_context_tokens,
        }

    try:
        logger.debug(f"Sending request to {url} with model {options.model}")
        logger.debug(f"Message count: {len(processed_messages)}")
        response = requests.post(url, json=payload, timeout=120)
    except (requests.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
        raise ConnectionRefused(url=url) from e
    except urllib3.exceptions.MaxRetryError as e:
        if isinstance(e.reason, urllib3.exceptions.ConnectTimeoutError):
            raise ConnectionTimeout(url=url, timeout_s=120.0) from e
        raise ConnectionRefused(url=url) from e

    response.raise_for_status()
    data = response.json()
    
    if "message" not in data or "content" not in data["message"]:
        logger.error(f"Unexpected response structure: {data}")
        raise ValueError(f"Unexpected Ollama response format: {data}")
    
    return data["message"]["content"]


def _process_messages(
    messages: list[dict[str, str | list[str] | list[dict]]],
) -> list[dict]:
    processed = []
    
    for msg in messages:
        processed_msg = msg.copy()
        
        if "images" in processed_msg and processed_msg["images"]:
            images = processed_msg["images"]
            processed_images = []
            
            for img in images:
                if isinstance(img, (str, Path)):
                    img_str = str(img)
                    if Path(img_str).exists():
                        logger.debug(f"Encoding image from file: {img_str}")
                        processed_images.append(_encode_image_to_base64(img_str))
                    elif len(img_str) > 100 and not img_str.startswith(('http://', 'https://')):
                        processed_images.append(img_str)
                    else:
                        logger.debug(f"Assuming base64 or will process later: {img_str[:50]}...")
                        processed_images.append(img_str)
                else:
                    processed_images.append(img)
            
            processed_msg["images"] = processed_images
        
        processed.append(processed_msg)
    
    return processed


import pytest


@pytest.mark.above10s
def test_only_text():
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


@pytest.mark.above10s
def test_multimodal_usage():
    from paper_scraper import Ollama
    from pathlib import Path
    import tempfile
    
    ollama_options = Ollama.Options(
        model="moondream:v2",
    )
    
    # Create a simple test image (1x1 pixel PNG)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        test_image_path = Path(tmp.name)
        test_image_path.write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x8d\xf7\xed\xf7\x00\x00\x00\x00IEND\xaeB`\x82'
        )
    
    messages = [
        {
            "role": "user",
            "content": "What's in this image?",
            "images": [str(test_image_path)],  # File paths are auto-encoded
        }
    ]
    
    logger.info(
        f"Connecting to Ollama at {ollama_options.base_url} (Model: {ollama_options.model})..."
    )
    answer = complete(messages=messages, options=ollama_options)
    logger.info(f"Multimodal answer: {answer}")
    assert answer, "Expected a non-empty answer from the multimodal model"
    
    test_image_path.unlink()
