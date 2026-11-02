def _pipe(value, *steps):
    for step in steps:
        value = step(value)
    return value

