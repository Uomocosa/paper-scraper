from enum import Enum


class GrobidError(Enum):
    UNEXPECTED_STATUS = "unexpected_status"
    CONNECTION_REFUSED = "connection_refused"
    CONNECTION_TIMEOUT = "connection_timeout"


def test_usage():
    from loguru import logger

    logger.info(f"GrobidError enum: {list(GrobidError)}")
