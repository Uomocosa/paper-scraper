import re
import requests
from pathlib import Path
from dataclasses import dataclass

import pyalex
from pyalex import Works

import paper_scraper
from paper_scraper import OpenAlex
from paper_scraper import Grobid
from paper_scraper import Error
from paper_scraper import Secrets
from paper_scraper.Error.GrobidError import GrobidError
from paper_scraper.__global__ import DOWNLOADED_DIR, EXTRACTED_REFERENCES
from loguru import logger


@dataclass
class Options:
    depth: int = 0
