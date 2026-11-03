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
