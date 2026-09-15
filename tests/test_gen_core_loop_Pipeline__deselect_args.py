import pytest
from core.loop import Pipeline
import core.loop as loop

class MockSettings:
    def __init__(self):
        self.candidates = []


def test_characterize_deselect_args_with_empty_known_failures(monkeypatch):
    monkeypatch.setattr(Pipeline, '__init__', lambda self, ws, settings, log, events, llm, run_id: setattr(self, 'known_failures', []))
    pipeline = Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=None, run_id=None)
    pipeline.known_failures = []
    result = pipeline._deselect_args()
    assert result == []
