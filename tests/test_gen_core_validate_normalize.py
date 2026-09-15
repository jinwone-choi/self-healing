import pytest
from core.validate import normalize
import core.validate as validate

class MockTarget:
    def __init__(self, import_lines):
        self.import_lines = import_lines



def test_characterize_normalize_no_fence(monkeypatch):
    raw_input = "code without fence"
    target = MockTarget(import_lines=["import os"])
    mode = "characterize"
    
    def fake_extract_code(raw):
        return "code without fence"

    monkeypatch.setattr(validate, "extract_code", fake_extract_code)
    
    result = normalize(raw_input, target, mode)
    assert "no_fence_sliced" in result.fixes  # Adjusted to check for the expected fix
