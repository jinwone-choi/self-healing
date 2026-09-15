import pytest
from core.logger import EventLog
import core.logger as logger

@pytest.fixture
def event_log(tmp_path):
    log_file = tmp_path / "test_log.json"
    el = EventLog(log_file)
    yield el
    el.close()

def test_characterize_event_log_close_normal(event_log):
    event_log.close()
    assert event_log._fh.closed == True

def test_characterize_event_log_close_empty_file(event_log):
    event_log._fh.write("")  # Writing an empty string to the file
    event_log.close()
    assert event_log._fh.closed == True
