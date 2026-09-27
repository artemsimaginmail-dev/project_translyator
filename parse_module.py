from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

PassKind = Literal["one-pass", "two-pass", "three-pass"]

@dataclass(frozen=True)
class Variant:
    number: int
    method: PassKind
    target_language: str
    title: str 

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
 
TERMS = {
     "program", "var", "begin", "end", "if", "then", "else",
     "integer", "real", "read", "write", "writeln"
 }

PREDEFINED = {"sin", "cos", "exp", "ln", "log", "sqrt", "abs", "fabs"}
KIND_WORDS = {
    "integer": "integer",
    "int": "integer",
    "целые": "integer",
    "real": "real",
    "double": "real",
    "float": "real",
    "вещественные": "real",
}

WORD_RE = re.compile(
     r"(?P<ident>[A-Za-z_][A-Za-z_0-9]*)|"
     r"(?P<number>\d+)|"
     r"(?P<op>[+\-*/=])|"
     r"(?P<punc>[;:,()])|"
     r"(?P<space>\s+)",
     re.UNICODE,
 )

