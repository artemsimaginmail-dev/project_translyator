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

def _pick_names(text: str) -> list[str]:
    """Извлечение имен переменных из списка объявлений."""
    names = []
    text = text.strip()
    for raw in re.split(r"[,\s]+", text):
        name = raw.strip(" ;:(){}[]")
        if re.fullmatch(r"[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*", name):
            names.append(name)
    return names

def _after_declarations(lines: Iterable[str]) -> list[str]:
    result: list[str] = []
    in_var_block = False
    block_nesting = 0
    program_ended = False   

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        
        low = line.lower()
        # Проверяем конец программы
        if low in {"end.", "end", "конец.", "конец"}:
            program_ended = True
            continue
        
        if program_ended:
            continue  # Пропускаем все после END

        if low.startswith(("begin", "начало")):
            block_nesting += 1
            in_var_block = False
            continue
        
        if low.startswith(("end", "конец")):
            block_nesting -= 1
            continue
        
        if low.startswith(("var", "vаг", "переменные")):
            in_var_block = True
            continue
        
        if in_var_block and block_nesting == 0:
            # Обрабатываем объявления только на верхнем уровне
            continue
        
        result.append(line)
    
    return result

def operators_from_source(source: str, symbols: dict[str, str]) -> tuple[list[str], list[str]]:    
    messages: list[str] = []
    normalized = source_to_clean_text(source)
    lines = _after_declarations(normalized.splitlines())
    intermediate: list[str] = []
    declared = set(symbols)
    keywords = TERMS | set(KIND_WORDS.keys())
    predefined = PREDEFINED

    for src_line, line in enumerate(lines, start=1):
        clean = line.strip().rstrip(";")
        if not clean:
            continue
        
        intermediate.append(clean)

        # Проверка типов в присваиваниях
        if ":=" in line or "=" in line:
            var_name = line.split(":=")[0].strip().split("=")[0].strip()
            if var_name in symbols:
                var_type = symbols[var_name]
                expr = line.split(":=")[1].strip() if ":=" in line else line.split("=")[1].strip()
                # Простая проверка: если в выражении есть число с точкой, а переменная integer - ошибка
                if var_type == "integer" and "." in expr:
                    messages.append(
                        f"Ошибка типа: присваивание вещественного значения целой переменной {var_name!r} в строке {src_line}"
                    )

        # Проверяем все идентификаторы в операторе
        for name in re.findall(r"[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*", clean):
                if name not in declared and name.lower() not in keywords:
                    messages.append(
                         f"Ошибка таблицы имён: повторное объявление имени {name!r} в строке {src_line}. "
                         f"Предыдущее объявление в строке {symbols.get(name + '_line', 'неизвестно')}"
                     )
                     
                     # Сохраняем строку объявления
                    symbols[name + '_line'] = src_line
    
    return intermediate, messages 

_BRACKET_PAIRS = {"(": ")", "{": "}", "[": "]"}

def syntax_messages(source: str) -> list[str]:
    messages: list[str] = []
    raw_lines = source.splitlines()
    nonempty = [(idx + 1, ln.strip()) for idx, ln in enumerate(raw_lines) if ln.strip()]
    if not nonempty:
        return ["Ошибка структуры: исходная программа пуста"]

    first_no, first = nonempty[0]
    low_first = first.lower()
    starts_program = low_first.startswith(("программа", "program", "procedure", "процедура", "main"))
    if not starts_program:
        messages.append(
            f"Ошибка структуры: отсутствует заголовок программы в строке {first_no} (ожидалось 'программа' или 'program')"
        )
    elif low_first.startswith(("программа", "program")) and not re.search(r"[;]\s*$", first):
        messages.append(
            f"Ошибка структуры: отсутствует ';' после заголовка программы (строка {first_no})"
        )

    last_no, last = nonempty[-1]
    if not last.lower().rstrip(".").rstrip(";").endswith(("конец", "end", "}")):
        messages.append(
            f"Ошибка структуры: программа не завершена ключевым словом 'конец'/'end' (последняя строка {last_no})"
        )

    stack: list[tuple[str, int, int]] = []
    in_str: str | None = None
    for src_line, line in enumerate(raw_lines, start=1):
        for col, ch in enumerate(line, start=1):
            if in_str:
                if ch == in_str:
                    in_str = None
                continue
            if ch in ("'", '"'):
                in_str = ch
                continue
            if ch in _BRACKET_PAIRS:
                stack.append((ch, src_line, col))
            elif ch in _BRACKET_PAIRS.values():
                if not stack:
                    messages.append(
                        f"Ошибка структуры: лишняя закрывающая скобка {ch!r} в строке {src_line}, позиция {col}"
                    )
                    continue
                opening, ol, oc = stack.pop()
                if _BRACKET_PAIRS[opening] != ch:
                    messages.append(
                        f"Ошибка структуры: непарная скобка — открыта {opening!r} в строке {ol}, "
                        f"закрыта {ch!r} в строке {src_line}"
                    )
    for opening, ol, oc in stack:
        messages.append(
            f"Ошибка структуры: незакрытая скобка {opening!r} в строке {ol}, позиция {oc}"
        )

    begin_count = 0
    end_count = 0
    for src_line, line in enumerate(raw_lines, start=1):
        low = line.lower()
        for tok in re.findall(r"\b(begin|начало|end|конец)\b", low):
            if tok in ("begin", "начало"):
                begin_count += 1
            else:
                end_count += 1
    if begin_count > end_count:
        messages.append(
            f"Ошибка структуры: число открывающих 'begin/начало' ({begin_count}) "
            f"превышает число закрывающих 'end/конец' ({end_count})"
        )
    elif end_count > begin_count + 1:
        messages.append(
            f"Ошибка структуры: лишнее ключевое слово 'end/конец' "
            f"(open={begin_count}, close={end_count})"
        )

    in_var_block = False
    for src_line, raw in enumerate(raw_lines, start=1):
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith(("begin", "начало")):
            in_var_block = False
            continue
        if low.startswith(("var", "vаг", "переменные", "real", "integer", "int ", "double", "float", "label")):
            in_var_block = True
            if ":" in line and ";" not in line and "(" not in line:
                next_lines = [raw_lines[i].strip() for i in range(src_line, min(src_line + 1, len(raw_lines)))]
                if not any(nl.endswith(";") for nl in next_lines):
                    messages.append(
                        f"Ошибка структуры: отсутствует ';' в описании переменных (строка {src_line})"
                    )
            continue
        if in_var_block and ":" in line and ";" not in line and "(" not in line:
            messages.append(
                f"Ошибка структуры: отсутствует ';' в описании переменных (строка {src_line})"
            )
            continue
        if low in {"end", "end.", "конец", "конец.", "}", "begin", "начало", "{", "else", "иначе"}:
            continue
        if low.endswith((",", ";", "{", "}", ":", "(", ")")):
            continue
        if low.startswith(("if ", "если ", "for ", "цикл ", "while ", "пока ", "do ")):
            continue
        if re.match(r"^[A-Za-zА-Яа-я_]\w*\s*(:=|=)", line) and not line.endswith(";"):
            messages.append(
                f"Ошибка структуры: отсутствует ';' после оператора присваивания (строка {src_line})"
            )

    return messages

def symbols_from_source(source: str) -> tuple[dict[str, str], list[str]]:
    """Построение таблицы символов на основе объявлений переменных"""
    symbols: dict[str, str] = {}
    messages: list[str] = []
    normalized = source_to_clean_text(source)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]

    def add_name(name: str, kind: str, src_line: int) -> None:        
        low = name.lower()
        if low in TERMS or low in PREDEFINED:
            return
        if name in symbols:
            messages.append(
                f"Ошибка таблицы имён: повторное объявление имени {name!r} в строке {src_line}"
            )
        else:
            symbols[name] = kind

    in_var_block = False
  
    for src_line, line in enumerate(lines, start=1):
     low = line.lower()
      
     if low.startswith(("var", "vаг", "переменные")):
        in_var_block = True
        continue

     # Обработка массивов
     if "array" in line.lower() or "[" in line:
         # Парсим объявление массива
        array_match = re.match(r"(\w+)\s*:\s*array\s*\[(.+)\]\s+of\s+(\w+)", line, re.I)
        if array_match:
            name = array_match.group(1)
            bounds = array_match.group(2)
            elem_type = array_match.group(3)
            symbols[name] = f"array[{bounds}] of {elem_type}"

     if in_var_block and ":" in line:
         # Парсим объявления
         parts = line.split(";")
         for part in parts:
          if ":" in part:
                 names_part, type_part = part.split(":", 1)
                 # Сохраняем информацию
                 pass 

          if "=" in line:
                # Разделяем объявление и инициализацию
                decl_part, init_part = line.split("=", 1)
                # Обрабатываем decl_part как обычное объявление
                line = decl_part

    for src_line, line in enumerate(lines, start=1):
        low = line.lower()
        
        if low.startswith(("begin", "начало")):
            in_var_block = False
            continue
        
        if low.startswith(("var", "vаг", "переменные")):
            in_var_block = True
            line = re.sub(r"^(var|vаг|переменные)\b", "", line, flags=re.I).strip()
            low = line.lower()
            if not line:
                continue
        
        if in_var_block:
            if ":" not in line:
                continue
            
            for part in [p for p in line.split(";") if p.strip()]:
                if ":" not in part:
                    continue
                
                names_part, type_part = part.split(":", 1)
                type_name = "real" if any(w in type_part.lower() for w in ["real", "double", "float", "веще"]) else "integer"
                
                for name in _pick_names(names_part):
                    add_name(name, type_name, src_line)
            continue
        
        m = re.match(r"^(real|integer|int|double|float)\s+(.+?);?$", line, flags=re.I)
        if m:
            kind = KIND_WORDS.get(m.group(1).lower(), "real")
            for name in _pick_names(m.group(2)):
                add_name(name, kind, src_line)
            continue

    return symbols, messages
