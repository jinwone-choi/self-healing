import pytest
from core.loop import Pipeline
import core.loop as loop
import time

def test_characterize_budget_ok_normal(monkeypatch):
    class MockSettings:
        max_runtime_minutes = 10
        max_llm_calls = 5
        candidates = 1  # Added missing attribute

    class MockLLM:
        calls = 3

    pipeline = Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=MockLLM(), run_id=None)
    pipeline.t0 = time.time() - 300  # Simulate 5 minutes elapsed

    result = pipeline._budget_ok()
    assert result is True

def test_characterize_budget_ok_runtime_exceeded(monkeypatch):
    class MockSettings:
        max_runtime_minutes = 1
        max_llm_calls = 5
        candidates = 1  # Added missing attribute

    class MockLLM:
        calls = 3

    pipeline = Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=MockLLM(), run_id=None)
    pipeline.t0 = time.time() - 120  # Simulate 2 minutes elapsed

    result = pipeline._budget_ok()
    assert result is False

def test_characterize_budget_ok_llm_calls_exceeded(monkeypatch):
    class MockSettings:
        max_runtime_minutes = 10
        max_llm_calls = 2
        candidates = 1  # Added missing attribute

    class MockLLM:
        calls = 3

    pipeline = Pipeline(ws=None, settings=MockSettings(), log=None, events=None, llm=MockLLM(), run_id=None)
    pipeline.t0 = time.time() - 300  # Simulate 5 minutes elapsed

    result = pipeline._budget_ok()
    assert result is False
