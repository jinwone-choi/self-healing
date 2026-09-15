import pytest
from core.config import load_settings
import core.config as config

def test_characterize_load_settings_default(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(config, "_s", lambda key, default=None: default)
    monkeypatch.setattr(config, "_f", lambda key, default=None: default)
    monkeypatch.setattr(config, "_i", lambda key, default=None: default)
    monkeypatch.setattr(config, "_b", lambda key, default=None: default)
    
    result = load_settings()
    assert result.llm_base_url == 'https://api.openai.com/v1'
    assert result.llm_model == 'gpt-4o-mini'

def test_characterize_load_settings_with_env(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(config, "_s", lambda key, default=None: "test_value" if key == "LLM_BASE_URL" else default)
    monkeypatch.setattr(config, "_f", lambda key, default=None: 0.5 if key == "LLM_TEMPERATURE" else default)
    monkeypatch.setattr(config, "_i", lambda key, default=None: 100 if key == "LLM_MAX_TOKENS" else default)
    monkeypatch.setattr(config, "_b", lambda key, default=None: False if key == "BLOCK_NETWORK" else default)
    
    result = load_settings()
    assert result.llm_base_url == 'test_value'
    assert result.temperature == 0.5

def test_characterize_load_settings_empty(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(config, "_s", lambda key, default=None: None)
    monkeypatch.setattr(config, "_f", lambda key, default=None: None)
    monkeypatch.setattr(config, "_i", lambda key, default=None: None)
    monkeypatch.setattr(config, "_b", lambda key, default=None: None)
    
    result = load_settings()
    assert result.llm_base_url is None
    assert result.temperature is None