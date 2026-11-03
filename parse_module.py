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

_ASM_RUNTIME = """
 ;-------------------------------------------------------------------
 ; Подпрограмма WRITE_INT: вывод знакового 16-битного целого из AX
 ;-------------------------------------------------------------------
 WRITE_INT PROC
     PUSH AX
     PUSH BX
     PUSH CX
     PUSH DX
     MOV BX, 10
     XOR CX, CX
     CMP AX, 0
     JGE WI_DIGITS
     PUSH AX
     MOV AH, 02h
     MOV DL, '-'
     INT 21h
     POP AX
     NEG AX
 WI_DIGITS:
     XOR DX, DX
     DIV BX
     PUSH DX
     INC CX
     OR AX, AX
     JNZ WI_DIGITS
 WI_PRINT:
     POP DX
     ADD DL, '0'
     MOV AH, 02h
     INT 21h
     LOOP WI_PRINT
     MOV AH, 02h
     MOV DL, 13
     INT 21h
     MOV DL, 10
     INT 21h
     POP DX
     POP CX
     POP BX
     POP AX
     RET
 WRITE_INT ENDP
 
 ;-------------------------------------------------------------------
 ; Подпрограмма READ_INT: ввод знакового 16-битного целого, результат в AX
 ;-------------------------------------------------------------------
 READ_INT PROC
     PUSH BX
     PUSH CX
     PUSH DX
     XOR BX, BX
     XOR CX, CX
 RI_LOOP:
     MOV AH, 01h
     INT 21h
     CMP AL, 13
     JE RI_DONE
     CMP AL, '-'
     JNE RI_NOT_MINUS
     MOV CX, 1
     JMP RI_LOOP
 RI_NOT_MINUS:
     CMP AL, '0'
     JB RI_LOOP
     CMP AL, '9'
     JA RI_LOOP
     SUB AL, '0'
     XOR AH, AH
     PUSH AX
     MOV AX, BX
     MOV DX, 10
     MUL DX
     POP DX
     ADD AX, DX
     MOV BX, AX
     JMP RI_LOOP
 RI_DONE:
     MOV AX, BX
     OR CX, CX
     JZ RI_END
     NEG AX
 RI_END:
     POP DX
     POP CX
     POP BX
     RET
 READ_INT ENDP
 """

def _asm_split_args(text: str) -> list[str]:
    text = text.strip().strip("()").strip(";").strip()
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]

def _asm_tokenize_expr(expr: str) -> list[str]:
    return re.findall(r"\d+|[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*|[+\-*/()]", expr)

def _asm_compile_expr(expr: str) -> list[str]:
    """Компиляция целочисленных выражений в инструкцию x86. Результат помещается в AX"""
    scanned = _asm_tokenize_expr(expr)
    if not scanned:
        return [" XOR AX, AX"]

    # Оптимизация: константные выражения
    if len(scanned) == 1 and scanned[0].lstrip('-').isdigit():
        return [f" MOV AX, {scanned[0]}"]
    
    # Оптимизация: простое присваивание переменной
    if len(scanned) == 1 and re.match(r"[A-Za-zА-Яа-я_]\w*", scanned[0]):
        return [f" MOV AX, {scanned[0]}"]

    pos = [0]
    
    def factor() -> list[str]:
        if pos[0] >= len(scanned):
            return [" XOR AX, AX"]
        t = scanned[pos[0]]
        if t == "(":
            pos[0] += 1
            code = expression()
            if pos[0] < len(scanned) and scanned[pos[0]] == ")":
                pos[0] += 1
            return code
        pos[0] += 1
        return [f" MOV AX, {t}"]
    
    def term() -> list[str]:
        code = factor()
        while pos[0] < len(scanned) and scanned[pos[0]] in ("*", "/"):
            op = scanned[pos[0]]
            pos[0] += 1
            code.append(" PUSH AX")
            code += factor()
            code.append(" MOV BX, AX")
            code.append(" POP AX")
            if op == "*":
                code.append(" IMUL BX")
            else:
                code.append(" CWD")
                code.append(" IDIV BX")
        return code
    
    def expression() -> list[str]:
        code = term()
        while pos[0] < len(scanned) and scanned[pos[0]] in ("+", "-"):
            op = scanned[pos[0]]
            pos[0] += 1
            code.append(" PUSH AX")
            code += term()
            code.append(" MOV BX, AX")
            code.append(" POP AX")
            if op == "+":
                code.append(" ADD AX, BX")
            else:
                code.append(" SUB AX, BX")
        return code
    
    return expression()

_ASM_JUMP_FALSE = {
    ">": "JLE", ">=": "JL", "<": "JGE", "<=": "JG",
    "==": "JNE", "=": "JNE", "<>": "JE", "!=": "JE",
}

def _asm_compile_condition(cond: str, false_label: str) -> list[str]:
    """Компиляция условия для x86 с переходом когда false"""
    cond = cond.strip().strip("()").strip()
    m = re.search(r"(>=|<=|<>|!=|==|>|<|=)", cond)
    if not m:
        return [f" JMP {false_label} ; условие нераспознано"]
    
    op = m.group(1)
    left = cond[:m.start()].strip()
    right = cond[m.end():].strip()
    
    code: list[str] = []
    code += _asm_compile_expr(left)
    code.append(" PUSH AX")
    code += _asm_compile_expr(right)
    code.append(" MOV BX, AX")
    code.append(" POP AX")
    code.append(" CMP AX, BX")
    jump = _ASM_JUMP_FALSE.get(op, "JMP")
    code.append(f" {jump} {false_label}")
    return code

def _asm_split_block(text: str) -> list[str]:
    text = text.strip().strip("()").strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r";", text) if p.strip()] 

def _asm_compile_statement(line: str, ctx: dict) -> list[str]:
  clean = line.strip().rstrip(";").strip()
  if not clean:
    return []    
    code: list[str] = []

  # BEGIN/END block
  if re.match(r"^(?:begin|начало)$", clean, re.I):
      return []
  if re.match(r"^(?:end|конец)$", clean, re.I):
     return []

  # Labels
  label_match = re.match(r"^(\d+)\s*:\s*(.*)$", clean)
  if label_match:
      label_no, rest = label_match.group(1), label_match.group(2).strip()
      code.append(f"UL{label_no}:")
      if rest:
          code += _asm_compile_statement(rest, ctx)
      return code
    
  # GOTO
  goto_match = re.match(r"^goto\s+(\w+)\s*$", clean, re.I)
  if goto_match:
      target_label = goto_match.group(1)
      code.append(f" JMP UL{target_label}")
      return code

  # READ
  for prefix in ("readln", "read", "scanf", "accept", "ввод", "читать"):
      if re.match(rf"^{re.escape(prefix)}\b", clean, re.I):
          rest = clean[len(prefix):]
          for name in _asm_split_args(rest):
              code.append(f" CALL READ_INT ; ввод значения {name}")
              code.append(f" MOV {name}, AX")
          return code

  # WRITE
  for prefix in ("writeln", "write", "printf", "type", "вывод", "вывести", "печатать", "передача"):
      if re.match(rf"^{re.escape(prefix)}\b", clean, re.I):
          rest = clean[len(prefix):]
          for name in _asm_split_args(rest):
              code += _asm_compile_expr(name)
              code.append(" CALL WRITE_INT ; вывод значения")
          return code    

   # Assignment
  assign_match = re.match(r"^([A-Za-zА-Яа-я_]\w*)\s*(?:=|=)\s+(.+)$", clean)
  if assign_match:
     var = assign_match.group(1)
     expr = assign_match.group(2).strip()
     code.append(f" ; {clean}")
     code += _asm_compile_expr(expr)
     code.append(f" MOV {var}, AX")
     return code

  # WHILE loop
  while_match = re.match(r"^(?:while|пока)\s+(.+?)\s+(?:do|выполнять)\s+(.+)$", clean, re.I)
  if while_match:
      cond = while_match.group(1).strip()
      body = while_match.group(2).strip()
        
      ctx["while_no"] = ctx.get("while_no", 0) + 1
      idx = ctx["while_no"]
      start_label = f"WHILE_START_{idx:03d}"
      end_label = f"WHILE_END_{idx:03d}"
        
      code.append(f"{start_label}:")
      code += _asm_compile_condition(cond, end_label)
      for stmt in _asm_split_block(body):
          code += _asm_compile_statement(stmt, ctx)
      code.append(f" JMP {start_label}")
      code.append(f"{end_label}:")
      return code

  # IF-THEN-ELSE
  if_match = re.match(r"^(?:if|если)\s+(.+?)\s+(?:then|то)\s+(.+)$", clean, re.I)
  if if_match:
    cond = if_match.group(1).strip()
    tail = if_match.group(2).strip()
    else_match = re.search(r"\b(иначе|else)\b", tail, re.I)
    
    ctx["if_no"] = ctx.get("if_no", 0) + 1
    idx = ctx["if_no"]
    else_label = f"ELSE_{idx:03d}"
    end_label = f"ENDIF_{idx:03d}"
    
    if else_match:
        then_part = tail[:else_match.start()].strip().rstrip(";").rstrip(",")
        else_part = tail[else_match.end():].strip().rstrip(";").rstrip(",").strip("()")
        
        code.append(f" ; if {cond} then ... else ...")
        code += _asm_compile_condition(cond, else_label)
        
        # Then part
        for stmt in _asm_split_block(then_part):
            code += _asm_compile_statement(stmt, ctx)
        code.append(f" JMP {end_label}")
        
        # Else part
        code.append(f"{else_label}:")
        for stmt in _asm_split_block(else_part):
            code += _asm_compile_statement(stmt, ctx)
        code.append(f"{end_label}:")
    else:
        then_part = tail.strip().rstrip(";").rstrip(",")
        code.append(f" ; if {cond} then ...")
        code += _asm_compile_condition(cond, end_label)
        for stmt in _asm_split_block(then_part):
            code += _asm_compile_statement(stmt, ctx)
        code.append(f"{end_label}:")
    return code

  code.append(f" ; {clean} -- не распознано")
  return code

def operators_to_program(intermediate: list[str], symbols: dict[str, str]) -> str:
    """Генерация полной программы на языке ассемблер"""
    var_lines: list[str] = []
    for name in symbols.keys():
        var_lines.append(f" {name:<8} DW ?")
    
    ctx = {"if_no": 0}
    body: list[str] = []
    
    for line in intermediate:
        body += _asm_compile_statement(line, ctx)
    
    lines: list[str] = []
    lines.append(";-------------------------------------------------------------------")
    lines.append("; Сгенерированная программа на ассемблере x86 (MASM, 16-bit)")
    lines.append(";-------------------------------------------------------------------")
    lines.append("")
    lines.append(".MODEL SMALL")
    lines.append(".STACK 100h")
    lines.append("")
    lines.append(".DATA")
    if var_lines:
        lines += var_lines
    else:
        lines.append(" ; (нет переменных)")
    lines.append("")
    lines.append(".CODE")
    lines.append("MAIN PROC")
    lines.append(" MOV AX, @DATA")
    lines.append(" MOV DS, AX")
    lines.append("")
    lines += body
    lines.append("")
    lines.append(" MOV AX, 4C00h ; завершение программы")
    lines.append(" INT 21h")
    lines.append("MAIN ENDP")
    lines.append("")
    lines.append(_ASM_RUNTIME.rstrip())
    lines.append("")
    lines.append("END MAIN")
    
    return "\n".join(lines)

def _pipe(value, *steps):
    for step in steps:
        value = step(value)
    return value

def translate(source: str, variant: Variant) -> Outcome:
    normalized, scanned, messages = _pipe(source, _front)
    messages.extend(syntax_messages(normalized))
    symbols, sem_diag = symbols_from_source(normalized)
    messages.extend(sem_diag)
    intermediate, ir_diag = operators_from_source(normalized, symbols)
    messages.extend(ir_diag)
    output = operators_to_program(intermediate, symbols)
    return Outcome(scanned, symbols, messages, intermediate, output) 

def _print_report(result: Outcome, variant: Variant, show_tokens: bool) -> None:
    print(f"Вариант {variant.number}: {variant.title}")
    print(f"Схема: {variant.method}; целевой язык: {variant.target_language}")
    print("\n=== Имена и типы ===")
    if result.symbols:
        for name, kind in result.symbols.items():
            print(f"  {name:<10} {kind}")
    else:
        print("  (пусто)")
    if show_tokens:
        print("\n=== Поток токенов ===")
        for token in result.scanned:
            print(f"  {token.line}:{token.src_col}  {token.kind:<8} {token.value}")
    print("\n=== Рабочий список операторов ===")
    for row in result.intermediate:
        print(f"  {row}")
    print("\n=== Сообщения анализатора ===")
    if result.messages:
        for item in result.messages:
            print(f"  ! {item}")
        print("\n=== Результат трансляции ===")
        print("  Трансляция не выполнена: устраните ошибки в исходном тексте и повторите запуск.")
    else:
        print("  Замечаний нет")
        print("\n=== Результат трансляции ===")
        print(result.output) 

def run_cli(variant: Variant) -> None:
    parser = argparse.ArgumentParser(description=variant.title)
    parser.add_argument("--source", default="source.txt", help="Файл исходной программы")
    parser.add_argument("-o", "--output", default="result.txt", help="Файл результата трансляции")
    parser.add_argument("--scanned", action="store_true", help="Показать поток лексем")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Не найден исходный файл: {source_path}", file=sys.stderr)
        sys.exit(2)
    result = translate(source_path.read_text(encoding="utf-8"), variant)
    if not result.messages:
        # при наличии ошибок целевой код не формируется и файл результата не создаётся
        Path(args.output).write_text(result.output + "\n", encoding="utf-8")
    _print_report(result, variant, args.scanned)
    if result.messages:
        sys.exit(1)
