from loguru import logger


class UnexpectedStatus(Exception):
    def __init__(self, url: str, status_code: int):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Server returned status {status_code} for {url}")

    def __str__(self) -> str:
        return (
            f"Error: UnexpectedStatus\n"
            f"  x Server returned status {self.status_code} for {self.url}\n"
            f"  help: Is Grobid running correctly?"
        )


def test_usage():
    logger.info("Testing UnexpectedStatus:")
    err = UnexpectedStatus(url="http://localhost:8070/api", status_code=500)
    logger.info(str(err))
