from loguru import logger


class OllamaConnectionTimeout(Exception):
    def __init__(self, url: str, timeout_s: float):
        self.url = url
        self.timeout_s = timeout_s
        super().__init__(f"Connection to Ollama timed out after {timeout_s}s")

    def __str__(self) -> str:
        return (
            f"Error: OllamaConnectionTimeout\n"
            f"  x Connection to Ollama timed out after {self.timeout_s}s\n"
            f"  help: The server may be overloaded. Try again later."
        )


def test_usage():
    logger.info("Testing OllamaConnectionTimeout:")
    err = OllamaConnectionTimeout(url="http://localhost:11434", timeout_s=120.0)
    logger.info(str(err))
