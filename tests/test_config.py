import pytest
import json
from pathlib import Path
from snaptext_app.core.config import Config, DEFAULT_CONFIG

@pytest.fixture
def temp_config_path(tmp_path):
    return tmp_path / "config.json"

def test_config_defaults(temp_config_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.config.get_config_path", lambda: temp_config_path)
    cfg = Config()
    assert cfg.get("appearance_mode") == "system"
    assert cfg.get("auto_copy_text") is True
    assert cfg.get("ocr_mode") == "balanced"
    assert cfg.get("capture_hotkey") == "ctrl+shift+s"

def test_config_save_load(temp_config_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.config.get_config_path", lambda: temp_config_path)
    cfg = Config()
    cfg.set("appearance_mode", "dark")
    
    # Reload
    cfg2 = Config()
    assert cfg2.get("appearance_mode") == "dark"

def test_config_malformed(temp_config_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.config.get_config_path", lambda: temp_config_path)
    temp_config_path.write_text("invalid json")
    
    cfg = Config()
    assert cfg.get("appearance_mode") == "system" # Should fall back to default


def test_config_sanitizes_invalid_values(temp_config_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.config.get_config_path", lambda: temp_config_path)
    temp_config_path.write_text(json.dumps({
        "appearance_mode": "neon",
        "ocr_mode": "slow",
        "ocr_language": "klingon",
        "auto_copy_text": "false",
        "max_history_entries": "not-a-number",
        "window_geometry": "bad geometry",
        "save_directory": "",
        "capture_hotkey": "",
    }))

    cfg = Config()

    assert cfg.get("appearance_mode") == "system"
    assert cfg.get("ocr_mode") == "balanced"
    assert cfg.get("ocr_language") == "eng"
    assert cfg.get("auto_copy_text") is False
    assert cfg.get("max_history_entries") == DEFAULT_CONFIG["max_history_entries"]
    assert cfg.get("window_geometry") == DEFAULT_CONFIG["window_geometry"]
    assert cfg.get("save_directory") == DEFAULT_CONFIG["save_directory"]
    assert cfg.get("capture_hotkey") == DEFAULT_CONFIG["capture_hotkey"]
