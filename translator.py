KIND_WORDS = {
    "integer": "integer",
    "int": "integer",
    "целые": "integer",
    "real": "real",
    "double": "real",
    "float": "real",
    "вещественные": "real",
}

def _pick_names(text: str) -> list[str]:
    """Extract variable names from declaration list."""
    names = []
    for raw in re.split(r"[,\s]+", text):
        name = raw.strip(" ;:(){}[]")
        if re.fullmatch(r"[A-Za-zА-Яа-я_][A-Za-zА-Яа-я_0-9]*", name):
            names.append(name)
    return names

def symbols_from_source(source: str) -> tuple[dict[str, str], list[str]]:
    """Build symbol table from variable declarations."""
    symbols: dict[str, str] = {}
    messages: list[str] = []
    return symbols, messages