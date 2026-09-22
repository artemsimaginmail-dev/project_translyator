from __future__ import annotations

from parse_module import Variant, run_cli

VARIANT = Variant(
    number=8,
    method='two-pass',
    target_language='asm',
    title='Двухпроходный транслятор с исходного языка на ассемблер (x86, MASM)',
)

def main() -> None:
    run_cli(VARIANT)

if __name__ == "__main__":
    main()