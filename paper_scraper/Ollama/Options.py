from dataclasses import dataclass


@dataclass
class Options:
    model: str = "tinyllama"
    base_url: str = "http://localhost:11434"
    temperature: float = 1.0
    system_prompt: str = "You are a helpful scientific research assistant."
    max_context_tokens: int = 256
    batch: int = 1
    handle_pdfs: str = "pdf2text"
