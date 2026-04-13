from dataclasses import dataclass
from paper_scraper import Secrets
import pyalex


@dataclass
class Options:
    api_key: str | None = None

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = Secrets.get_pyalex_api_key()

    def setup_pyalex_key(self):
        if self.api_key:
            pyalex.api_key = self.api_key
        else:
            pyalex.api_key = None
