import pytest
from core.loop import Pipeline
import core.loop as loop

class MockSettings:
    def __init__(self):
        self.candidates = 1  # Mocking a candidates attribute

@pytest.fixture
def mock_static_gate(monkeypatch):
    def mock_gate(src):
        if src == "valid_input":
            return True, None, []
        elif src == "no_assert":
            return False, "no_assert", []
        return False, "invalid", []
    
    monkeypatch.setattr(loop.validate, "static_gate", mock_gate)

@pytest.fixture
def pipeline():
    return Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=None, run_id=None)

def test_characterize_pipeline_gate_valid_input(mock_static_gate, pipeline):
    norm = type("Normalized", (), {"src": "valid_input"})()
    result = pipeline._gate(norm, None, None, None, None)
    assert result == 'valid_input'
