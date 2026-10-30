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

