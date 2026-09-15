import pytest
from core.prompt import build_repair_prompt
import core.prompt as prompt

def test_characterize_build_repair_prompt_with_card(monkeypatch):
    class MockTarget:
        def __init__(self):
            self.src = "sample source code"
            self.lineno = 1
            self.missing = []
            self.import_lines = ["import math"]

    def mock_load_card(card):
        return "Mock card content for " + card

    monkeypatch.setattr(prompt, "load_card", mock_load_card)
    
    result = build_repair_prompt(MockTarget(), "test_src", [], "characterize", "example_card")
    assert "## Rule: example_card" in result[1]

def test_characterize_build_repair_prompt_without_card(monkeypatch):
    class MockTarget:
        def __init__(self):
            self.src = "sample source code"
            self.lineno = 1
            self.missing = []
            self.import_lines = ["import math"]

    monkeypatch.setattr(prompt, "load_card", lambda card: "Mock card content for " + card)
    
    result = build_repair_prompt(MockTarget(), "test_src", [], "characterize")
    assert "## Rule:" not in result[1]

def test_characterize_build_repair_prompt_empty_failures(monkeypatch):
    class MockTarget:
        def __init__(self):
            self.src = "sample source code"
            self.lineno = 1
            self.missing = []
            self.import_lines = ["import math"]

    monkeypatch.setattr(prompt, "load_card", lambda card: "Mock card content for " + card)
    
    result = build_repair_prompt(MockTarget(), "test_src", [], "characterize")
    assert "## Target source" in result[1]