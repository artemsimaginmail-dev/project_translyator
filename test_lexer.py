import pytest
from translator import lex, source_to_clean_text

def test_simple_tokens():
    source = "program Test var x: integer;"
    tokens, _ = lex(source_to_clean_text(source))
    assert len(tokens) == 7
    assert tokens[0].kind == "keyword"
    assert tokens[0].value == "program"

def test_number_tokens():
    source = "x := 123.45"
    tokens, _ = lex(source_to_clean_text(source))
    assert tokens[2].kind == "number"
    assert tokens[2].value == "123.45"