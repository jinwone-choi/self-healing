import pytest
from core.loop import Pipeline
import core.loop as loop

class MockTarget:
    def __init__(self, blacklisted=False, attempts=0, last_level="", retry_partial=False):
        self.blacklisted = blacklisted
        self.attempts = attempts
        self._last_level = last_level
        self._retry_partial = retry_partial
        self.key = "mock_target"

class MockSettings:
    def __init__(self, max_attempts_per_target, candidates=0):
        self.max_attempts_per_target = max_attempts_per_target
        self.candidates = candidates

@pytest.fixture
def pipeline():
    settings = MockSettings(max_attempts_per_target=3, candidates=5)
    targets = [MockTarget(attempts=i) for i in range(5)]
    p = Pipeline(ws=None, settings=settings, log=None, events=None, llm=None, run_id=None)
    p.targets = targets
    return p

def test_characterize_next_target_valid_input(pipeline):
    target = pipeline._next_target()
    assert target.key == "mock_target"

def test_characterize_next_target_blacklisted(pipeline):
    pipeline.targets[0].blacklisted = True
    target = pipeline._next_target()
    assert target.key == "mock_target"

def test_characterize_next_target_max_attempts(pipeline):
    pipeline.targets[1].attempts = 3
    target = pipeline._next_target()
    assert target.key == "mock_target"

def test_characterize_next_target_no_valid_targets(pipeline):
    for target in pipeline.targets:
        target.attempts = 3
    result = pipeline._next_target()
    assert result is None