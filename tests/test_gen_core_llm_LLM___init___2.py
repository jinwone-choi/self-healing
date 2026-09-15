import pytest
from core.llm import LLM
import core.llm as llm

class MockSettings:
    def __init__(self, llm_base_url):
        self.llm_base_url = llm_base_url

class MockLog:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append((message, args))

def test_characterize_llm_init_external_endpoint():
    settings = MockSettings("http://external.endpoint")
    log = MockLog()
    llm_instance = LLM(settings, log)
    assert log.warnings == [('LLM endpoint %s is EXTERNAL: target source code will leave this machine (set LLM_BASE_URL to the on-prem endpoint for internal repositories)', ('http://external.endpoint',))]

def test_characterize_llm_init_internal_endpoint():
    settings = MockSettings("http://internal.endpoint")
    log = MockLog()
    llm_instance = LLM(settings, log)
    assert log.warnings == [('LLM endpoint %s is EXTERNAL: target source code will leave this machine (set LLM_BASE_URL to the on-prem endpoint for internal repositories)', ('http://internal.endpoint',))]

def test_characterize_llm_init_empty_url():
    settings = MockSettings("")
    log = MockLog()
    llm_instance = LLM(settings, log)
    assert log.warnings == [('LLM endpoint %s is EXTERNAL: target source code will leave this machine (set LLM_BASE_URL to the on-prem endpoint for internal repositories)', ('',))]

def test_characterize_llm_init_invalid_url():
    settings = MockSettings("invalid-url")
    log = MockLog()
    llm_instance = LLM(settings, log)
    assert log.warnings == [('LLM endpoint %s is EXTERNAL: target source code will leave this machine (set LLM_BASE_URL to the on-prem endpoint for internal repositories)', ('invalid-url',))]