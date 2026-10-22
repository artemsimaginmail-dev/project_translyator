import pytest
from translator import symbols_from_source, operators_from_source

def test_variable_declaration():
    source = """
    program Test
    var
        x: integer;
        y: real;
    begin
        x := 5
    end
    """
    symbols, _ = symbols_from_source(source)
    assert symbols["x"] == "integer"
    assert symbols["y"] == "real"

def test_duplicate_declaration():
    source = """
    program Test
    var
        x: integer;
        x: real;
    begin
        x := 5
    end
    """
    _, messages = symbols_from_source(source)
    assert len(messages) == 1
    assert "повторное объявление" in messages[0]