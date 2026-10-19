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
            if name not in declared and name.lower() not in TERMS:
                messages.append(
                    f"Ошибка таблицы имён: имя не найдено в описаниях {name!r} в операторе {src_line}"
                )
    
    return intermediate, messages 

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