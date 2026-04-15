from loguru import logger


class OllamaConnectionRefused(Exception):
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Cannot connect to Ollama at {url}")

    def __str__(self) -> str:
        return (
            f"Error: OllamaConnectionRefused\n"
            f"  x Cannot connect to Ollama at {self.url}\n"
            f"  help: Ensure Ollama is running:\n"
            f"          ollama serve\n"
            f"          ollama run <model>"
        )


def test_usage():
    logger.info("Testing OllamaConnectionRefused:")
    err = OllamaConnectionRefused(url="http://localhost:11434")
    logger.info(str(err))
