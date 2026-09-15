import pytest
from core.llm import LLM
import core.llm as llm

def test_characterize_llm_init_normal(monkeypatch):
    class MockSettings:
        llm_base_url = "http://localhost"

    mock_log = lambda msg: None
    instance = LLM(settings=MockSettings(), log=mock_log)
    assert instance.s.llm_base_url == 'http://localhost'



def test_characterize_llm_init_internal_endpoint(monkeypatch):
    class MockSettings:
        llm_base_url = "http://internal.com"

    mock_log = lambda msg: None
    monkeypatch.setattr(llm, "is_external_endpoint", lambda url: False)
    instance = LLM(settings=MockSettings(), log=mock_log)
    assert instance.s.llm_base_url == 'http://internal.com'
