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
     r"(?P<ident>[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*)|"
     r"(?P<number>\d+(?:[.,]\d+)?)|"
     r"(?P<string>\'[^\']*\'|\"[^\"]*\")|"
     r"(?P<op>:=|<=|>=|<>|!=|==|\+\+|--|\*\*|[+\-*/=<>\|])|"
     r"(?P<punc>[;:,.(){}[\]])|"
     r"(?P<space>\s+)",
     re.UNICODE,
 )

def _strip_comments(source: str) -> str:
    """Удаление комментариев из исходного кода"""
    lines = []
    for line in source.splitlines():
        if "//" in line:
            line = line[:line.index("//")]
        lines.append(line)
    return "\n".join(lines)

def source_to_clean_text(source: str) -> str:

    source = _strip_comments(source)

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

    if not source or not source.strip():
        return [], ["Предупреждение: исходная программа пуста"]

    scanned: list[Atom] = []
    messages: list[str] = []

    for src_line, line in enumerate(source.splitlines(), start=1):
        for match in WORD_RE.finditer(line):
            kind = match.lastgroup or "ident"
            value = match.group()
            
            if kind == "space":
                continue

            # Обработка недопустимых символов
            if kind == "bad":
              messages.append(
                  f"Ошибка лексического анализа: запрещённый символ {value!r} в строке {src_line}, позиция {match.start() + 1}"
              )
              continue

            src_col = match.start() + 1
            
            if kind == "ident" and value.lower() in TERMS:
                kind = "keyword"
             
            scanned.append(Atom(kind, value, src_line, src_col))
     
    return scanned, messages

def _front(source: str):
   normalized = source_to_clean_text(source)
   scanned, lex_diag = lex(normalized)
   return normalized, scanned, list(lex_diag)

