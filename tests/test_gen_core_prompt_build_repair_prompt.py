import pytest
from core.prompt import build_repair_prompt
import core.prompt as prompt








def test_characterize_build_repair_prompt_invalid_mode(monkeypatch):
    class MockTarget:
        def __init__(self):
            self.src = "print('Hello')"
            self.lineno = 1
            self.import_lines = ["from core.prompt import build_repair_prompt"]

    test_src = "print('Hello')"
    failures = []
    mode = "invalid_mode"
    card = None

    with pytest.raises(AttributeError):
        build_repair_prompt(MockTarget(), test_src, failures, mode, card)
