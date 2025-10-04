import pytest
import json
import tempfile
import os
from pathlib import Path
from lmarena_bridge.settings import load_settings, Settings, update_config_partial

@pytest.fixture
def temp_config_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.jsonc"
        config_path.write_text(json.dumps({
            "version": "3.0.0",
            "session_id": "test-session",
            "message_id": "test-message",
            "server_port": 5102
        }))
        monkeypatch.setenv("LMABRIDGE_CONFIG_DIR", tmpdir)
        yield tmpdir

def test_load_settings_default():
    s = load_settings()
    assert isinstance(s, Settings)
    assert s.version
    assert s.server_port == 5102

def test_load_settings_from_file(temp_config_dir):
    s = load_settings()
    assert s.session_id == "test-session"
    assert s.message_id == "test-message"

def test_update_config_partial(temp_config_dir):
    ok = update_config_partial({"server_port": 9999})
    assert ok
    s = load_settings()
    assert s.server_port == 9999