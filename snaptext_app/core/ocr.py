from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .config import config
from .logger import logger
from .paths import resource_path

LANGUAGE_OPTIONS = {
    "English": "eng",
    "Urdu": "urd",
    "English + Urdu": "eng+urd",
}
LANGUAGE_LABELS = {value: key for key, value in LANGUAGE_OPTIONS.items()}

BUNDLED_TESSERACT = Path("runtime") / "tesseract" / "tesseract.exe"
WINDOWS_LANGUAGE_TAGS = {
    "eng": ("en-US", "en-GB", "en"),
    "urd": ("ur-PK", "ur-IN", "ur"),
}


class OCREngineUnavailable(RuntimeError):
    """Raised when no suitable local OCR engine can process the request."""


@dataclass(frozen=True)
class OCRStatus:
    ready: bool
    engine: str = "none"
    path: str = ""
    version: str = ""
    languages: tuple[str, ...] = ()
    message: str = ""
    bundled: bool = False
    tessdata_dir: str = ""

    @property
    def engine_label(self) -> str:
        if self.engine == "windows":
            return "Windows OCR"
        if self.engine == "tesseract":
            return "Built-in Tesseract OCR" if self.bundled else "Tesseract OCR"
        return "OCR unavailable"

    def supports(self, language_profile: str) -> bool:
        requested = {code for code in language_profile.split("+") if code}
        return bool(requested) and requested.issubset(set(self.languages))


# Backward-compatible name retained for older imports and third-party extensions.
TesseractStatus = OCRStatus


def get_bundled_tesseract_path() -> Path:
    """Return the optional Tesseract executable shipped with a release build."""
    return resource_path(str(BUNDLED_TESSERACT))


def _candidate_paths(configured_path: str | None = None) -> Iterable[Path]:
    """Yield optional Tesseract executables in priority order."""
    seen: set[str] = set()
    candidates: list[str | Path | None] = [
        get_bundled_tesseract_path(),
        configured_path,
        shutil.which("tesseract"),
    ]

    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates.extend(
            [
                Path(program_files) / "Tesseract-OCR" / "tesseract.exe",
                Path(program_files_x86) / "Tesseract-OCR" / "tesseract.exe",
                Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
                Path.home() / "AppData" / "Local" / "Tesseract-OCR" / "tesseract.exe",
            ]
        )
    else:
        candidates.extend(["/usr/bin/tesseract", "/usr/local/bin/tesseract"])

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        yield path


def find_tesseract(configured_path: str | None = None) -> str:
    configured_path = configured_path if configured_path is not None else config.get("tesseract_path", "")
    for path in _candidate_paths(configured_path):
        if path.is_file():
            return str(path)
    return ""


def _subprocess_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _tessdata_dir(executable: str | Path) -> Path | None:
    directory = Path(executable).resolve().parent / "tessdata"
    return directory if directory.is_dir() else None


def _tesseract_environment(executable: str | Path) -> dict[str, str]:
    env = os.environ.copy()
    tessdata = _tessdata_dir(executable)
    if tessdata:
        env["TESSDATA_PREFIX"] = str(tessdata)
    return env


def _list_languages(executable: str, tessdata: Path | None) -> tuple[str, ...]:
    command = [executable]
    if tessdata:
        command.extend(["--tessdata-dir", str(tessdata)])
    command.append("--list-langs")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=_subprocess_flags(),
        env=_tesseract_environment(executable),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return tuple(sorted(line for line in lines if not line.lower().startswith("list of available")))


def check_tesseract(path: str | None = None) -> OCRStatus:
    """Inspect optional Tesseract support without making it mandatory."""
    resolved = find_tesseract(path)
    if not resolved:
        return OCRStatus(
            ready=False,
            engine="tesseract",
            message="Optional Tesseract OCR was not found.",
        )

    try:
        result = subprocess.run(
            [resolved, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_subprocess_flags(),
            env=_tesseract_environment(resolved),
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip())

        version_line = (result.stdout or result.stderr).splitlines()[0].strip()
        tessdata = _tessdata_dir(resolved)
        languages = _list_languages(resolved, tessdata)
        pytesseract.pytesseract.tesseract_cmd = resolved
        bundled = Path(resolved).resolve() == get_bundled_tesseract_path().resolve()
        return OCRStatus(
            True,
            engine="tesseract",
            path=resolved,
            version=version_line,
            languages=languages,
            message="Tesseract OCR ready",
            bundled=bundled,
            tessdata_dir=str(tessdata) if tessdata else "",
        )
    except Exception as exc:
        logger.warning("Tesseract validation failed for %s: %s", resolved, exc)
        bundled = False
        try:
            bundled = Path(resolved).resolve() == get_bundled_tesseract_path().resolve()
        except Exception:
            pass
        return OCRStatus(
            False,
            engine="tesseract",
            path=resolved,
            message="The optional Tesseract installation could not be started.",
            bundled=bundled,
        )


def _is_rpc_changed_mode(exc: BaseException) -> bool:
    """Return True when COM is already initialized with another apartment model."""
    values = (
        getattr(exc, "hresult", None),
        getattr(exc, "winerror", None),
        exc.args[0] if getattr(exc, "args", ()) else None,
    )
    for value in values:
        if isinstance(value, int) and (value & 0xFFFFFFFF) == 0x80010106:
            return True
    return False


def _initialize_windows_runtime():
    """Initialize WinRT for the current thread and return a cleanup callback.

    SnapText runs OCR in worker threads. WinRT requires each calling thread to
    have a COM apartment, so initialization must happen on the thread that
    performs recognition rather than only once at application startup.
    """
    if sys.platform != "win32":
        return lambda: None

    try:
        from winrt.runtime import ApartmentType, init_apartment, uninit_apartment

        try:
            init_apartment(ApartmentType.MULTI_THREADED)
            return uninit_apartment
        except Exception as exc:
            if _is_rpc_changed_mode(exc):
                # Another library already initialized this thread as STA. WinRT
                # calls are still valid; we simply must not uninitialize it.
                logger.debug("WinRT thread already uses a different apartment model")
                return lambda: None
            raise
    except ImportError:
        # Compatibility with the older monolithic ``winsdk`` package.
        try:
            from winsdk import _winrt

            try:
                _winrt.init_apartment(_winrt.MTA)
                return _winrt.uninit_apartment
            except Exception as exc:
                if _is_rpc_changed_mode(exc):
                    logger.debug("Legacy WinRT thread already has a COM apartment")
                    return lambda: None
                raise
        except ImportError:
            # _load_windows_ocr_api() will provide the user-facing dependency
            # message. Keeping this a no-op preserves that clearer error path.
            return lambda: None


def _load_windows_ocr_api() -> dict[str, Any]:
    """Load the current PyWinRT packages, with legacy winsdk compatibility."""
    try:
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter

        return {
            "Language": Language,
            "BitmapAlphaMode": BitmapAlphaMode,
            "BitmapPixelFormat": BitmapPixelFormat,
            "SoftwareBitmap": SoftwareBitmap,
            "OcrEngine": OcrEngine,
            "DataWriter": DataWriter,
        }
    except ImportError as modern_error:
        try:
            from winsdk.windows.globalization import Language
            from winsdk.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.storage.streams import DataWriter

            return {
                "Language": Language,
                "BitmapAlphaMode": BitmapAlphaMode,
                "BitmapPixelFormat": BitmapPixelFormat,
                "SoftwareBitmap": SoftwareBitmap,
                "OcrEngine": OcrEngine,
                "DataWriter": DataWriter,
            }
        except ImportError as legacy_error:
            raise ImportError(
                "Windows OCR Python bindings are not installed. Run setup_development.bat once."
            ) from legacy_error
        except Exception:
            raise
    except Exception:
        raise


def _language_code_from_tag(tag: str) -> str | None:
    normalized = tag.lower().replace("_", "-")
    if normalized == "en" or normalized.startswith("en-"):
        return "eng"
    if normalized == "ur" or normalized.startswith("ur-"):
        return "urd"
    return None


def _windows_available_languages(api: dict[str, Any]) -> tuple[str, ...]:
    codes: set[str] = set()
    OcrEngine = api["OcrEngine"]
    try:
        recognizers = OcrEngine.available_recognizer_languages or ()
        for language in recognizers:
            code = _language_code_from_tag(str(language.language_tag))
            if code:
                codes.add(code)
    except Exception as exc:
        logger.debug("Could not enumerate Windows OCR languages: %s", exc)
    return tuple(sorted(codes))


def check_windows_ocr() -> OCRStatus:
    """Check Windows' local OCR API. It requires no separate OCR executable."""
    if sys.platform != "win32":
        return OCRStatus(False, engine="windows", message="Windows OCR is available only on Windows.")

    cleanup_runtime = _initialize_windows_runtime()
    try:
        api = _load_windows_ocr_api()
        OcrEngine = api["OcrEngine"]
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            # Some systems have recognizers installed but no matching user-profile
            # language. Try English explicitly before reporting failure.
            Language = api["Language"]
            engine = OcrEngine.try_create_from_language(Language("en-US"))
        if engine is None:
            return OCRStatus(
                False,
                engine="windows",
                message="Windows OCR is present, but no compatible recognition language is installed.",
            )

        languages = set(_windows_available_languages(api))
        try:
            recognizer_code = _language_code_from_tag(str(engine.recognizer_language.language_tag))
            if recognizer_code:
                languages.add(recognizer_code)
        except Exception:
            pass
        # The common Windows setup has an English recognizer. If enumeration is
        # unavailable but an engine was created, preserve a useful default.
        if not languages:
            languages.add("eng")

        return OCRStatus(
            True,
            engine="windows",
            version="Windows built-in OCR",
            languages=tuple(sorted(languages)),
            message="Windows OCR ready",
        )
    except ImportError as exc:
        logger.warning("Windows OCR bindings are missing: %s", exc)
        return OCRStatus(
            False,
            engine="windows",
            message="SnapText's Windows OCR support is not installed. Run setup_development.bat once.",
        )
    except Exception as exc:
        logger.warning("Windows OCR validation failed: %s", exc)
        return OCRStatus(
            False,
            engine="windows",
            message="Windows OCR could not be started on this PC.",
        )
    finally:
        # Release WinRT objects before balancing the COM apartment.
        engine = None
        api = None
        try:
            cleanup_runtime()
        except Exception as exc:
            logger.debug("Could not uninitialize WinRT cleanly: %s", exc)


def _persist_detected_tesseract(status: OCRStatus) -> None:
    # Do not persist PyInstaller's temporary bundled path. A system path is safe.
    if status.ready and status.engine == "tesseract" and not status.bundled:
        if config.get("tesseract_path") != status.path:
            config.set("tesseract_path", status.path)


def check_ocr_engine(language_profile: str | None = None) -> OCRStatus:
    """Select the best available engine for the requested language profile."""
    requested = language_profile or config.get("ocr_language", "eng")

    windows_status = check_windows_ocr()

    # Windows OCR is the zero-configuration default for English. Return before
    # probing optional executables so the normal capture path stays fast and
    # cannot be disrupted by a stale third-party Tesseract installation.
    if requested == "eng" and windows_status.ready and windows_status.supports(requested):
        return windows_status

    tesseract_status = check_tesseract()
    _persist_detected_tesseract(tesseract_status)

    # Tesseract is preferred for Urdu and mixed recognition when available.
    if tesseract_status.ready and tesseract_status.supports(requested):
        return tesseract_status

    # A Windows language pack may provide Urdu on some systems.
    if windows_status.ready and windows_status.supports(requested):
        return windows_status

    if requested in {"urd", "eng+urd"}:
        return OCRStatus(
            False,
            message=(
                "Urdu OCR is not available on this PC. Choose English in Settings, "
                "or install Tesseract with Urdu language data for optional Urdu support."
            ),
            languages=tuple(sorted(set(windows_status.languages) | set(tesseract_status.languages))),
        )

    details = windows_status.message or tesseract_status.message
    return OCRStatus(
        False,
        message=details or "No local OCR engine is available.",
        languages=tuple(sorted(set(windows_status.languages) | set(tesseract_status.languages))),
    )


def configure_detected_ocr(language_profile: str | None = None) -> OCRStatus:
    requested = language_profile or config.get("ocr_language", "eng")
    status = check_ocr_engine(requested)
    if not status.ready and requested != "eng":
        fallback = check_ocr_engine("eng")
        if fallback.ready:
            logger.warning(
                "OCR profile %s is unavailable; falling back to English.",
                requested,
            )
            config.set("ocr_language", "eng")
            return fallback
    return status


def configure_detected_tesseract() -> OCRStatus:
    """Backward-compatible alias for the old startup helper."""
    return configure_detected_ocr()


def available_language_options() -> dict[str, str]:
    """Return only language profiles that can currently be recognized."""
    supported: set[str] = set()
    windows_status = check_windows_ocr()
    tesseract_status = check_tesseract()
    if windows_status.ready:
        supported.update(windows_status.languages)
    if tesseract_status.ready:
        supported.update(tesseract_status.languages)

    options: dict[str, str] = {}
    if "eng" in supported:
        options["English"] = "eng"
    if "urd" in supported:
        options["Urdu"] = "urd"
    if {"eng", "urd"}.issubset(supported) and tesseract_status.ready and tesseract_status.supports("eng+urd"):
        options["English + Urdu"] = "eng+urd"

    # Keep Settings usable even during a transient engine check failure. English
    # remains the safe default and the status area explains any missing binding.
    if not options:
        options["English"] = "eng"
    return options


def _preprocess(image: Image.Image, mode: str) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    gray = ImageOps.grayscale(image)
    if mode == "fast":
        return ImageOps.autocontrast(gray)

    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.SHARPEN)
    contrast = 1.8 if mode == "balanced" else 2.2
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    scale = 2 if mode == "balanced" else 3
    width, height = gray.size
    return gray.resize(
        (max(1, width * scale), max(1, height * scale)), Image.Resampling.LANCZOS
    )


def _choose_windows_language(api: dict[str, Any], code: str):
    Language = api["Language"]
    OcrEngine = api["OcrEngine"]

    try:
        recognizers = OcrEngine.available_recognizer_languages or ()
        for language in recognizers:
            if _language_code_from_tag(str(language.language_tag)) == code:
                return language
    except Exception:
        pass

    for tag in WINDOWS_LANGUAGE_TAGS.get(code, ()):
        try:
            language = Language(tag)
            if OcrEngine.is_language_supported(language):
                return language
        except Exception:
            continue
    return None


async def _perform_windows_ocr_once(image: Image.Image, code: str, mode: str) -> str:
    api = _load_windows_ocr_api()
    OcrEngine = api["OcrEngine"]
    language = _choose_windows_language(api, code)
    engine = OcrEngine.try_create_from_language(language) if language is not None else None
    if engine is None and code == "eng":
        engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        label = LANGUAGE_LABELS.get(code, code)
        raise OCREngineUnavailable(f"Windows does not have the {label} OCR language installed.")

    processed = _preprocess(image, mode)
    max_dimension = int(OcrEngine.max_image_dimension)
    if max_dimension > 0 and max(processed.size) > max_dimension:
        processed.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    rgba = processed.convert("RGBA")
    pixels = rgba.tobytes("raw", "BGRA")
    DataWriter = api["DataWriter"]
    SoftwareBitmap = api["SoftwareBitmap"]
    BitmapPixelFormat = api["BitmapPixelFormat"]
    BitmapAlphaMode = api["BitmapAlphaMode"]

    writer = DataWriter()
    bitmap = None
    try:
        writer.write_bytes(pixels)
        buffer = writer.detach_buffer()
        bitmap = SoftwareBitmap(
            BitmapPixelFormat.BGRA8,
            rgba.width,
            rgba.height,
            BitmapAlphaMode.IGNORE,
        )
        bitmap.copy_from_buffer(buffer)
        result = await engine.recognize_async(bitmap)
        return (result.text or "").strip()
    finally:
        try:
            writer.close()
        except Exception:
            pass
        if bitmap is not None:
            try:
                bitmap.close()
            except Exception:
                pass


def _run_windows_ocr(image: Image.Image, language_profile: str, mode: str) -> str:
    async def recognize() -> str:
        results: list[str] = []
        for code in language_profile.split("+"):
            text = await _perform_windows_ocr_once(image, code, mode)
            if text and text not in results:
                results.append(text)
        return "\n".join(results).strip()

    cleanup_runtime = _initialize_windows_runtime()
    try:
        return asyncio.run(recognize())
    except OCREngineUnavailable:
        raise
    except Exception as exc:
        logger.exception("Windows OCR failed")
        raise RuntimeError(f"Windows OCR failed: {exc}") from exc
    finally:
        try:
            cleanup_runtime()
        except Exception as exc:
            logger.debug("Could not uninitialize WinRT cleanly: %s", exc)


def _run_tesseract_ocr(
    img: Image.Image,
    status: OCRStatus,
    language_profile: str,
    mode: str,
) -> str:
    pytesseract.pytesseract.tesseract_cmd = status.path
    options = {
        "fast": "--oem 3 --psm 6",
        "balanced": "--oem 3 --psm 6 -c preserve_interword_spaces=1",
        "accurate": "--oem 3 --psm 3 -c preserve_interword_spaces=1",
    }
    if mode not in options:
        mode = "balanced"

    tessdata_option = ""
    if status.tessdata_dir:
        safe_path = status.tessdata_dir.replace('"', '\\"')
        tessdata_option = f' --tessdata-dir "{safe_path}"'

    previous_prefix = os.environ.get("TESSDATA_PREFIX")
    try:
        if status.tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = status.tessdata_dir
        processed = _preprocess(img, mode)
        return pytesseract.image_to_string(
            processed,
            lang=language_profile,
            config=options[mode] + tessdata_option,
        ).strip()
    finally:
        if previous_prefix is None:
            os.environ.pop("TESSDATA_PREFIX", None)
        else:
            os.environ["TESSDATA_PREFIX"] = previous_prefix


def perform_ocr(img: Image.Image, lang: str | None = None, mode: str | None = None) -> str:
    """Extract text using Windows OCR first, with optional Tesseract fallback."""
    explicit_language = lang is not None
    language_profile = lang or config.get("ocr_language", "eng")
    mode = mode or config.get("ocr_mode", "balanced")
    status = check_ocr_engine(language_profile)
    if not status.ready and not explicit_language and language_profile != "eng":
        fallback = check_ocr_engine("eng")
        if fallback.ready:
            logger.warning(
                "Configured OCR profile %s is unavailable; using English.",
                language_profile,
            )
            language_profile = "eng"
            status = fallback
            config.set("ocr_language", "eng")
    if not status.ready:
        raise OCREngineUnavailable(status.message)

    logger.debug(
        "Starting OCR with engine=%s lang=%s mode=%s",
        status.engine_label,
        language_profile,
        mode,
    )
    try:
        if status.engine == "windows":
            text = _run_windows_ocr(img, language_profile, mode)
        else:
            text = _run_tesseract_ocr(img, status, language_profile, mode)
        logger.debug("OCR completed with %d characters", len(text))
        return text
    except OCREngineUnavailable:
        raise
    except Exception as exc:
        logger.exception("OCR failed")
        raise RuntimeError(f"OCR failed: {exc}") from exc
