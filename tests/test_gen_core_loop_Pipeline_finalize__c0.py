import pytest
from core.loop import Pipeline
import core.loop as loop

def test_characterize_pipeline_finalize_success(monkeypatch):
    class FakeWorkspace:
        def __init__(self):
            self.cov_dir = tmp_path
            self.repo_root = tmp_path

    class FakeSettings:
        target_coverage = 80
        pytest_timeout_s = 60

    pipeline = Pipeline()
    pipeline.ws = FakeWorkspace()
    pipeline.s = FakeSettings()
    pipeline._deselect_args = lambda: []
    
    final_json = tmp_path / "final.json"
    final_json.write_text('{"percent": 85}', encoding="utf-8")
    
    monkeypatch.setattr(loop.cio, "run_pytest", lambda *args, **kwargs: type('obj', (object,), {'returncode': 0, 'stdout': 'TOTAL 100 100 85.00%'}))
    monkeypatch.setattr(loop.CovState, "from_json", lambda data: type('CovState', (object,), {'percent': data['percent']}))
    
    pipeline.finalize()
    assert pipeline.final_percent == __CAPTURE__

def test_characterize_pipeline_finalize_no_final_json(monkeypatch):
    class FakeWorkspace:
        def __init__(self):
            self.cov_dir = tmp_path
            self.repo_root = tmp_path

    class FakeSettings:
        target_coverage = 80
        pytest_timeout_s = 60

    pipeline = Pipeline()
    pipeline.ws = FakeWorkspace()
    pipeline.s = FakeSettings()
    pipeline._deselect_args = lambda: []
    
    monkeypatch.setattr(loop.cio, "run_pytest", lambda *args, **kwargs: type('obj', (object,), {'returncode': 0, 'stdout': 'TOTAL 100 100 85.00%'}))
    monkeypatch.setattr(loop.CovState, "from_json", lambda data: type('CovState', (object,), {'percent': data['percent']}))
    
    pipeline.finalize()
    assert pipeline.final_percent == __CAPTURE__

def test_characterize_pipeline_finalize_with_failures(monkeypatch):
    class FakeWorkspace:
        def __init__(self):
            self.cov_dir = tmp_path
            self.repo_root = tmp_path

    class FakeSettings:
        target_coverage = 80
        pytest_timeout_s = 60

    pipeline = Pipeline()
    pipeline.ws = FakeWorkspace()
    pipeline.s = FakeSettings()
    pipeline._deselect_args = lambda: []
    
    final_json = tmp_path / "final.json"
    final_json.write_text('{"percent": 75}', encoding="utf-8")
    
    monkeypatch.setattr(loop.cio, "run_pytest", lambda *args, **kwargs: type('obj', (object,), {'returncode': 5, 'stdout': 'TOTAL 100 100 75.00%'}))
    monkeypatch.setattr(loop.CovState, "from_json", lambda data: type('CovState', (object,), {'percent': data['percent']}))
    
    pipeline.finalize()
    assert pipeline.final_percent == __CAPTURE__