import pytest
from core.loop import Pipeline
import core.loop as loop

class MockSettings:
    def __init__(self):
        self.pytest_timeout_s = 30
        self.target_coverage = 80
        self.candidates = 1  # Added candidates attribute



def test_characterize_pipeline_finalize_with_failures(tmp_path, monkeypatch):
    mock_ws = type('MockWorkspace', (), {})()
    mock_ws.cov_dir = tmp_path
    final_json_path = mock_ws.cov_dir / "final.json"
    final_json_path.write_text("{}", encoding="utf-8")

    mock_pipeline = Pipeline(ws=mock_ws, settings=MockSettings(), log=None, events=None, llm=None, run_id=None)

    monkeypatch.setattr(loop.cio, "run_pytest", lambda *args, **kwargs: type('MockResult', (), {'returncode': 1, 'stdout': 'FAILURES'})())
    
    with pytest.raises(AttributeError):
        mock_pipeline.finalize()
