import pytest
import json
from pathlib import Path
from snaptext_app.core.history import History

@pytest.fixture
def temp_history_path(tmp_path):
    return tmp_path / "history.json"

def test_history_add_delete(temp_history_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.history.get_history_path", lambda: temp_history_path)
    hist = History()
    
    hist.add_entry("path/to/img.png", "some text")
    assert len(hist.get_all()) == 1
    assert hist.get_all()[0]["text"] == "some text"
    entry_id = hist.get_all()[0]["id"]
    assert hist.update_entry(entry_id, text="updated text") is True
    assert hist.get_all()[0]["text"] == "updated text"
    
    hist.delete_entry(entry_id)
    assert len(hist.get_all()) == 0

def test_history_clear(temp_history_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.history.get_history_path", lambda: temp_history_path)
    hist = History()
    hist.add_entry("p1", "t1")
    hist.add_entry("p2", "t2")
    assert len(hist.get_all()) == 2
    
    hist.clear()
    assert len(hist.get_all()) == 0


def test_history_sanitizes_partially_corrupt_entries(temp_history_path, monkeypatch):
    monkeypatch.setattr("snaptext_app.core.history.get_history_path", lambda: temp_history_path)
    temp_history_path.write_text(json.dumps([
        {"text": 123, "timestamp": "not-a-date", "source": ""},
        "bad-entry",
        {"id": "ok", "timestamp": "2026-07-17T12:00:00", "text": "valid", "source": "file"},
    ]), encoding="utf-8")

    hist = History()
    entries = hist.get_all()

    assert len(entries) == 2
    assert entries[0]["id"]
    assert entries[0]["text"] == "123"
    assert entries[0]["source"] == "screen"
    assert entries[1]["id"] == "ok"
