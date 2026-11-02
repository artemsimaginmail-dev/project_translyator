def _print_report(result: Outcome, variant: Variant, show_tokens: bool) -> None:
    print(f"Вариант {variant.number}: {variant.title}")
    print(f"Схема: {variant.method}; целевой язык: {variant.target_language}")
