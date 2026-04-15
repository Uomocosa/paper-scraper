from dataclasses import dataclass, field


@dataclass
class QuestionResponse:
    question: str
    papers: list["PaperResponse"] = field(default_factory=list)
    skipped_papers: list[str] = field(default_factory=list)
