from snaptext_app.core.clipboard import copy_to_clipboard


def test_copy_to_clipboard_returns_false_when_backend_fails(monkeypatch):
    monkeypatch.setattr("pyperclip.copy", lambda _text: (_ for _ in ()).throw(RuntimeError("missing clipboard")))

    assert copy_to_clipboard("hello") is False


def test_copy_to_clipboard_returns_true_when_backend_succeeds(monkeypatch):
    copied = {}

    def fake_copy(text):
        copied["text"] = text

    monkeypatch.setattr("pyperclip.copy", fake_copy)

    assert copy_to_clipboard("hello") is True
    assert copied["text"] == "hello"
