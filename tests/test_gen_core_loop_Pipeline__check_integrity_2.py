import core.loop
import pytest
from core.loop import Pipeline
import core.loop as loop

class MockWS:
    def __init__(self):
        self.repo_root = "dummy_repo_root"

class MockSettings:
    def __init__(self):
        self.candidates = 5  # Adding the missing attribute

class MockLog:
    def error(self, msg):
        pass

class MockEvents:
    def emit(self, event, **kwargs):
        pass

class MockLLM:
    pass

def test_characterize_pipeline_check_integrity_with_problems():
    pipeline = Pipeline(ws=MockWS(), settings=MockSettings(), log=MockLog(), events=MockEvents(), llm=MockLLM(), run_id="dummy_run_id")
    
    def mock_verify(repo_root, manifest):
        return [("file1", "missing"), ("file2", "corrupted")]
    
    loop.integrity.verify = mock_verify
    pipeline._restore = lambda problems: None  # Mock _restore to do nothing

    with pytest.raises(core.loop.IntegrityViolation):
        pipeline._check_integrity("test_context")

def test_characterize_pipeline_check_integrity_no_problems():
    pipeline = Pipeline(ws=MockWS(), settings=MockSettings(), log=MockLog(), events=MockEvents(), llm=MockLLM(), run_id="dummy_run_id")

    def mock_verify(repo_root, manifest):
        return []
    
    loop.integrity.verify = mock_verify

    result = pipeline._check_integrity("test_context")
    assert result is False
