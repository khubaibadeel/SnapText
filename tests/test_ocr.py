from pathlib import Path

from PIL import Image

from snaptext_app.core import ocr


def test_language_profiles_are_human_readable():
    assert ocr.LANGUAGE_OPTIONS["English"] == "eng"
    assert ocr.LANGUAGE_OPTIONS["Urdu"] == "urd"
    assert ocr.LANGUAGE_OPTIONS["English + Urdu"] == "eng+urd"


def test_find_tesseract_uses_configured_path_when_bundle_is_missing(tmp_path, monkeypatch):
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"")
    monkeypatch.setattr(
        ocr, "get_bundled_tesseract_path", lambda: tmp_path / "missing" / "tesseract.exe"
    )
    assert ocr.find_tesseract(str(executable)) == str(executable)


def test_find_tesseract_prefers_bundled_runtime(tmp_path, monkeypatch):
    bundled = tmp_path / "runtime" / "tesseract" / "tesseract.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"")
    configured = tmp_path / "configured" / "tesseract.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"")
    monkeypatch.setattr(ocr, "get_bundled_tesseract_path", lambda: bundled)
    assert ocr.find_tesseract(str(configured)) == str(bundled)


def test_find_tesseract_returns_empty_when_no_candidates(monkeypatch):
    monkeypatch.setattr(ocr, "_candidate_paths", lambda configured_path=None: [])
    assert ocr.find_tesseract("missing") == ""


def test_preprocessing_modes_return_valid_images():
    image = Image.new("RGB", (30, 20), "white")
    fast = ocr._preprocess(image, "fast")
    balanced = ocr._preprocess(image, "balanced")
    accurate = ocr._preprocess(image, "accurate")
    assert fast.size == (30, 20)
    assert balanced.size == (60, 40)
    assert accurate.size == (90, 60)


def test_windows_ocr_is_default_for_english(monkeypatch):
    windows = ocr.OCRStatus(True, engine="windows", languages=("eng",), message="ready")
    optional = ocr.OCRStatus(False, engine="tesseract", message="not installed")
    monkeypatch.setattr(ocr, "check_windows_ocr", lambda: windows)
    monkeypatch.setattr(ocr, "check_tesseract", lambda path=None: optional)

    selected = ocr.check_ocr_engine("eng")

    assert selected.ready
    assert selected.engine == "windows"


def test_tesseract_is_used_for_urdu_when_available(monkeypatch):
    windows = ocr.OCRStatus(True, engine="windows", languages=("eng",), message="ready")
    optional = ocr.OCRStatus(
        True,
        engine="tesseract",
        path="tesseract.exe",
        languages=("eng", "urd"),
        bundled=True,
    )
    monkeypatch.setattr(ocr, "check_windows_ocr", lambda: windows)
    monkeypatch.setattr(ocr, "check_tesseract", lambda path=None: optional)

    selected = ocr.check_ocr_engine("urd")

    assert selected.ready
    assert selected.engine == "tesseract"


def test_missing_optional_urdu_does_not_break_english_options(monkeypatch):
    windows = ocr.OCRStatus(True, engine="windows", languages=("eng",), message="ready")
    optional = ocr.OCRStatus(False, engine="tesseract", message="not installed")
    monkeypatch.setattr(ocr, "check_windows_ocr", lambda: windows)
    monkeypatch.setattr(ocr, "check_tesseract", lambda path=None: optional)

    assert ocr.available_language_options() == {"English": "eng"}
    unavailable = ocr.check_ocr_engine("urd")
    assert not unavailable.ready
    assert "Choose English" in unavailable.message


def test_perform_ocr_dispatches_to_windows_backend(monkeypatch):
    status = ocr.OCRStatus(True, engine="windows", languages=("eng",))
    monkeypatch.setattr(ocr, "check_ocr_engine", lambda language_profile=None: status)
    monkeypatch.setattr(ocr, "_run_windows_ocr", lambda image, language, mode: "recognized")

    result = ocr.perform_ocr(Image.new("RGB", (10, 10), "white"), lang="eng", mode="fast")

    assert result == "recognized"


def test_windows_language_tag_mapping():
    assert ocr._language_code_from_tag("en-US") == "eng"
    assert ocr._language_code_from_tag("ur-PK") == "urd"
    assert ocr._language_code_from_tag("fr-FR") is None
