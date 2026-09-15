import pytest
from core.llm import LLM
import core.llm as llm

@pytest.fixture
def llm_instance(monkeypatch):
    class MockSettings:
        llm_base_url = "http://mock-url.com"
        llm_api_key = "mock-api-key"
        timeout_s = 5

    monkeypatch.setattr(llm, 's', MockSettings())  # Patch the settings in the correct module
    return LLM()

def test_characterize_llm_client_initialization(llm_instance):
    client = llm_instance.client
    assert client is not None  # Ensure client is initialized

def test_characterize_llm_client_called_twice(llm_instance):
    client_first_call = llm_instance.client
    client_second_call = llm_instance.client
    assert client_first_call == client_second_call  # Ensure same client instance is returned

def test_characterize_llm_client_external_endpoint_warning(llm_instance, caplog):
    with caplog.at_level("WARNING"):
        llm_instance.client  # Trigger the client to be initialized
    assert "LLM endpoint" in caplog.text  # Check for warning log

def test_characterize_llm_client_no_settings(llm_instance, monkeypatch):
    monkeypatch.setattr(llm, 's', None)
    with pytest.raises(AttributeError):  # Expecting an error due to missing settings
        llm_instance.client