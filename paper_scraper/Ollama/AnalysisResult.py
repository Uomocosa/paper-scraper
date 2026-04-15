from dataclasses import dataclass


@dataclass
class AnalysisResult:
    response: str
    skipped: bool = False
