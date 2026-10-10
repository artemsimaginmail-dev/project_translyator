def _pick_names(text: str) -> list[str]:
    """Извлечение имен переменных из списка объявлений."""
    names = []
    for raw in re.split(r"[,\s]+", text):
        name = raw.strip(" ;:(){}[]")
        if re.fullmatch(r"[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*", name):
            names.append(name)
    return names

def symbols_from_source(source: str) -> tuple[dict[str, str], list[str]]:
    """Построение таблицы символов на основе объявлений переменных"""
    symbols: dict[str, str] = {}
    messages: list[str] = []
    normalized = source_to_clean_text(source)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    
    in_var_block = False
  
    for src_line, line in enumerate(lines, start=1):
     low = line.lower()
      
     if low.startswith(("var", "vаг", "переменные")):
        in_var_block = True
        continue
      
     if in_var_block and ":" in line:
         # Парсим объявления
         parts = line.split(";")
         for part in parts:
          if ":" in part:
                 names_part, type_part = part.split(":", 1)
                 # Сохраняем информацию
                 pass 
          
    return symbols, messages