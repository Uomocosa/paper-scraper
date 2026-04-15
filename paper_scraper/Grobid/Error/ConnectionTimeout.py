from loguru import logger


class ConnectionTimeout(Exception):
    def __init__(self, url: str, timeout_s: float):
        self.url = url
        self.timeout_s = timeout_s
        super().__init__(f"Connection to Grobid timed out after {timeout_s}s")

    def __str__(self) -> str:
        return (
            f"Error: ConnectionTimeout\n"
            f"  x Connection to Grobid timed out after {self.timeout_s}s\n"
            f"  help: The server may be overloaded. Try again later."
        )


def test_usage():
    logger.info("Testing ConnectionTimeout:")
    err = ConnectionTimeout(url="http://localhost:8070/api", timeout_s=5.0)
    logger.info(str(err))
