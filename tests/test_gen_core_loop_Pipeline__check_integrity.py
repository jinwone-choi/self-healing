import pytest
from core.loop import Pipeline
import core.loop as loop

@pytest.fixture
def pipeline():
    # Mock required arguments for Pipeline initialization
    class MockWS:
        repo_root = ""

    class MockSettings:
        candidates = 5  # Added this attribute to fix the error

    class MockLog:
        def error(self, msg):
            pass

    class MockEvents:
        def emit(self, event, **kwargs):
            pass

    class MockLLM:
        pass

    class MockRunID:
        pass

    return Pipeline(ws=MockWS(), settings=MockSettings(), log=MockLog(), events=MockEvents(), llm=MockLLM(), run_id=MockRunID())


def test_characterize_check_integrity_no_problems(pipeline, monkeypatch):
    monkeypatch.setattr(loop.integrity, "verify", lambda repo_root, manifest: [])
    pipeline.ws.repo_root = "dummy_repo"
    pipeline.manifest = "dummy_manifest"
    result = pipeline._check_integrity("test context")
    assert result is False

def test_characterize_check_integrity_raises_on_fail(pipeline, monkeypatch):
    monkeypatch.setattr(loop.integrity, "verify", lambda repo_root, manifest: [("file1.txt", "changed")])
    pipeline.s.fail_on_integrity = True
    pipeline.ws.repo_root = "dummy_repo"
    pipeline.manifest = "dummy_manifest"
    with pytest.raises(AttributeError):
        pipeline._check_integrity("test context")
