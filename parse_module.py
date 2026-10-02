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
    "accept", "and", "begin", "do", "double", "else", "end", "float", "if",
    "int", "integer", "or", "printf", "program", "read", "readln", "real",
    "scanf", "then", "type", "var", "write", "writeln", "ввод", "вещественные",
    "вывести", "вывод", "выполнить", "выполнять", "если", "и", "или", "иначе",
    "конец", "начало", "передача", "переменные", "печатать", "программа", "то",
    "целые", "читать",
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
     r"(?P<number>\d+(?:[.,]\d+)?)|"
     r"(?P<string>\'[^\']*\'|\"[^\"]*\")|"
     r"(?P<op>[+\-*/=])|"
     r"(?P<punc>[;:,()])|"
     r"(?P<space>\s+)",
     re.UNICODE,
 )

def source_to_clean_text(source: str) -> str:
    
    # Замена нестандартных кавычек
    replacements = {
        '"': '"', '"': '"', "„": '"',
        "'": "'", "'": "'",
    }
    
    for old, new in replacements.items():
        source = source.replace(old, new)
    
    # Склеивание строк, разбитых переносом
    raw_lines = source.splitlines()
    glued: list[str] = []
     
    for line in raw_lines:
        stripped = line.strip()
        if glued and glued[-1].rstrip().endswith(("(", ",")):
            glued[-1] = glued[-1].rstrip() + " "+ stripped
            continue
        glued.append(line)
     
    return "\n".join(glued)

def lex(source:  str) -> tuple[list[Atom], list[str]]:    

    scanned: list[Atom] = []
    messages: list[str] = []

    for src_line, line in enumerate(source.splitlines(), start=1):
        for match in WORD_RE.finditer(line):
            kind = match.lastgroup or "ident"
            value = match.group()
            
            if kind == "space":
                continue
    
            src_col = match.start() + 1
            
            if kind == "ident" and value.lower() in TERMS:
                kind = "keyword"
             
            scanned.append(Atom(kind, value, src_line, src_col))
     
    return scanned, messages

