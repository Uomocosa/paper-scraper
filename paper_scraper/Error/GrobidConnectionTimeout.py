from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger


@dataclass
class GrobidConnectionTimeout(ABC, Exception):
    url: str
    timeout_s: float

    def __str__(self) -> str:
        return (
            f"Error: GrobidConnectionTimeout\n"
            f"  x Connection to Grobid timed out after {self.timeout_s}s\n"
            f"  help: The server may be overloaded. Try again later."
        )


def test_usage():
    logger.info("Testing GrobidConnectionTimeout:")
    err = GrobidConnectionTimeout(url="http://localhost:8070/api", timeout_s=5.0)
    logger.info(str(err))
