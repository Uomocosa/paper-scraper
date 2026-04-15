from dataclasses import dataclass


@dataclass
class PaperResponse:
    paper_name: str
    response: str
    skipped: bool = False
