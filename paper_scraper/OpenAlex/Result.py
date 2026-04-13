from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

class Status(Enum):
    SUCCESS = 1
    NOT_OPEN_ACCESS = 2
    ERROR = 3

@dataclass
class Result:
    status: Status
    path: Optional[Path] = None
