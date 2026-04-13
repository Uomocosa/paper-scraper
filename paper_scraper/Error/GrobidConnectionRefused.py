from loguru import logger

class GrobidConnectionRefused(Exception):
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Cannot connect to Grobid at {url}")

    def __str__(self) -> str:
        return (
            f"Error: GrobidConnectionRefused\n"
            f"  x Cannot connect to Grobid at {self.url}\n"
            f"  help: Ensure Grobid is running:\n"
            f"          podman machine init\n"
            f"          podman machine start\n"
            f"          podman run --rm --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.2-crf"
        )


def test_usage():
    logger.info("Testing GrobidConnectionRefused:")
    err = GrobidConnectionRefused(url="http://localhost:8070/api")
    logger.info(str(err))
