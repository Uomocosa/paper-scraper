import os
from pathlib import Path
from dataclasses import dataclass
from typing import Literal


@dataclass
class Options:
    model: str = "tinyllama"
    base_url: str = "http://localhost:11434"
    completion_path: str = "/api/chat"
    api_key_env: str = ""
    system_prompt_file: str = ""
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
        if self.system_prompt_file:
            self.system_prompt = Path(self.system_prompt_file).read_text(encoding="utf-8")
