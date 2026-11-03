def _print_report(result: Outcome, variant: Variant, show_tokens: bool) -> None:
    print(f"Вариант {variant.number}: {variant.title}")
    print(f"Схема: {variant.method}; целевой язык: {variant.target_language}")
    print("\n=== Имена и типы ===")
    if result.symbols:
        for name, kind in result.symbols.items():
            print(f"  {name:<10} {kind}")
    else:
        print("  (пусто)")
