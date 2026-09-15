import pytest
from core.loop import Pipeline
import core.loop as loop


def test_characterize_discover_targets_empty_input(monkeypatch):
    def mock_discover(ws, cov, log):
        return []

    monkeypatch.setattr(loop.tmod, "discover", mock_discover)
    
    class MockSettings:
        candidates = 10

    pipeline = Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=None, run_id=None)
    pipeline.discover_targets()
    
    assert pipeline.targets == []
