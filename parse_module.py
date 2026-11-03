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
