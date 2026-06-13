import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class Options:
    model: str = "tinyllama"
    base_url: str = "http://localhost:11434"
    completion_path: str = "/api/chat"
    api_key_env: str = ""
    temperature: float = 1.0
    system_prompt: str = "You are a helpful scientific research assistant."
    max_context_tokens: int = 256
    batch: int = 1
    handle_pdfs: Literal["pdf2text", "pdf2image"] = "pdf2text"

    def __post_init__(self):
        self.api_key = ""
        if self.api_key_env:
            from dotenv import load_dotenv
            from paper_scraper.__global__ import ENV_FILE
            load_dotenv(ENV_FILE)
            self.api_key = os.environ.get(self.api_key_env, "")
        env_prompt = os.environ.get("OPENCODE_SYSTEM_PROMPT")
        if env_prompt:
            self.system_prompt = env_prompt
