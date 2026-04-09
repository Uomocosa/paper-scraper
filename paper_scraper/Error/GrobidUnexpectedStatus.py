from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger


@dataclass
class GrobidUnexpectedStatus(ABC, Exception):
    url: str
    status_code: int

    def __str__(self) -> str:
        return (
            f"Error: GrobidUnexpectedStatus\n"
            f"  x Server returned status {self.status_code} for {self.url}\n"
            f"  help: Is Grobid running correctly?"
        )


def test_usage():
    logger.info("Testing GrobidUnexpectedStatus:")
    err = GrobidUnexpectedStatus(url="http://localhost:8070/api", status_code=500)
    logger.info(str(err))
