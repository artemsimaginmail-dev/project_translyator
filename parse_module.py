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