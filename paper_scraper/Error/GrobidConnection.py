from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger


class GrobidConnection(ABC, Exception):
    @abstractmethod
    def __str__(self) -> str:
        pass


@dataclass
class ConnectionRefused(GrobidConnection):
    url: str

    def __str__(self) -> str:
        return (
            f"Error: GrobidConnection::ConnectionRefused\n"
            f"  x Cannot connect to Grobid at {self.url}\n"
            f"  help: Ensure Grobid is running:\n"
            f"          podman machine init\n"
            f"          podman machine start\n"
            f"          podman run --rm --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.2-crf"
        )


@dataclass
class ConnectionTimeout(GrobidConnection):
    url: str
    timeout_s: float

    def __str__(self) -> str:
        return (
            f"Error: GrobidConnection::ConnectionTimeout\n"
            f"  x Connection to Grobid timed out after {self.timeout_s}s\n"
            f"  help: The server may be overloaded. Try again later."
        )


@dataclass
class UnexpectedStatus(GrobidConnection):
    url: str
    status_code: int

    def __str__(self) -> str:
        return (
            f"Error: GrobidConnection::UnexpectedStatus\n"
            f"  x Server returned status {self.status_code} for {self.url}\n"
            f"  help: Is Grobid running correctly?"
        )


def test_error_formatting():
    logger.info("Testing ConnectionRefused:")
    err = ConnectionRefused(url="http://localhost:8070/api")
    logger.info(str(err))

    logger.info("\nTesting ConnectionTimeout:")
    err = ConnectionTimeout(url="http://localhost:8070/api", timeout_s=5.0)
    logger.info(str(err))

    logger.info("\nTesting UnexpectedStatus:")
    err = UnexpectedStatus(url="http://localhost:8070/api", status_code=500)
    logger.info(str(err))
