from dataclasses import dataclass, field


@dataclass
class BatchResult:
    responses: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
