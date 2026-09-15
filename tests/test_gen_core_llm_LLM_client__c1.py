import pytest
from core.llm import LLM
import core.llm as llm

@pytest.fixture
def llm_instance(monkeypatch):
    class MockSettings:
        llm_base_url = "http://mock.url"
        llm_api_key = "mock_api_key"
        timeout_s = 30
        
    monkeypatch.setattr(llm.LLM, 's', MockSettings())
    return LLM()

def test_characterize_llm_client_initialization(llm_instance):
    client = llm_instance.client
    assert client is not None

def test_characterize_llm_client_double_initialization(llm_instance):
    client_1 = llm_instance.client
    client_2 = llm_instance.client
    assert client_1 == client_2

def test_characterize_llm_client_external_endpoint_warning(llm_instance, monkeypatch):
    def mock_is_external_endpoint(url):
        return True

    monkeypatch.setattr(llm, 'is_external_endpoint', mock_is_external_endpoint)
    with pytest.raises(Exception):  # Replace with the specific exception expected
        _ = llm_instance.client