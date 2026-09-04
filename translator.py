from __future__ import annotations
import re
from dataclasses import dataclass
 
@dataclass(frozen=True)
class Atom:
     kind: str
     value: str
     line: int
     src_col: int
 
@dataclass
class Outcome:
     scanned: list[Atom]
     symbols: dict[str, str]
     messages: list[str]
     intermediate: list[str]
     output: str     