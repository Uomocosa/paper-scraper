import requests
import urllib3
from paper_scraper.Ollama.Options import Options
from paper_scraper.Error import OllamaConnectionRefused, OllamaConnectionTimeout
from loguru import logger

def _estimate_tokens(text: str) -> int:
    return len(text) // 4

def call_ollama(
    question: str,
    paper_text: str,
    options: Options,
) -> str:
    url = f"{options.base_url}/api/chat"
    
    payload = {
        "model": options.model,
        "messages": [
            {"role": "system", "content": options.system_prompt},
            {
                "role": "user",
                "content": f"Paper:\n\n{paper_text}\n\n---\n\nQuestion: {question}\n\nPlease answer based only on the paper above.",
            },
        ],
        "stream": False,
        "options": {
            "temperature": options.temperature,
            "num_ctx": options.max_context_tokens, # This actually restricts the memory now!
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
    except (requests.ConnectionError, urllib3.exceptions.NewConnectionError) as e:
        raise OllamaConnectionRefused(url=url) from e
    except urllib3.exceptions.MaxRetryError as e:
        if isinstance(e.reason, urllib3.exceptions.ConnectTimeoutError):
            raise OllamaConnectionTimeout(url=url, timeout_s=120.0) from e
        raise OllamaConnectionRefused(url=url) from e

    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]



def test_usage():
    from paper_scraper import Ollama
    sample_paper_text = (
        "Polyphox adsorption mechanisms are primarily driven by electrostatic "
        "interactions and van der Waals forces. The study demonstrates that "
        "at a pH of 7.4, the binding affinity reaches its peak due to the "
        "deprotonation of surface hydroxyl groups."
    )
    ollama_options = Ollama.Options()
    question = "What are the primary drivers of the adsorption mechanisms?"
    logger.info(f"Connecting to Ollama at {ollama_options.base_url} (Model: {ollama_options.model})...")
    answer = call_ollama(
        question=question,
        paper_text=sample_paper_text,
        options=ollama_options
    )
    logger.info(f"Answer:\n{answer}")
