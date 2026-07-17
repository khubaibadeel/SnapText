from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_text = str(ROOT)
if root_text in sys.path:
    sys.path.remove(root_text)
sys.path.insert(0, root_text)

from snaptext_app.core.ocr import check_windows_ocr
from snaptext_app.version import __version__


def main() -> int:
    package_file = Path(__import__("snaptext_app").__file__).resolve()
    print(f"SnapText version: {__version__}")
    print(f"Loaded package: {package_file}")

    expected_root = ROOT.resolve()
    if expected_root not in package_file.parents:
        print("ERROR: Python loaded SnapText from a different folder.")
        return 1

    if sys.platform != "win32":
        print("Windows OCR verification skipped on this operating system.")
        return 0

    status = check_windows_ocr()
    print(f"OCR engine: {status.engine_label}")
    print(f"OCR status: {status.message}")
    print(f"OCR languages: {', '.join(status.languages) if status.languages else 'none detected'}")

    if not status.ready:
        print("ERROR: Windows OCR could not be started.")
        print("Open Windows Settings > Time & language > Language & region and ensure English is installed.")
        return 1

    if "eng" not in status.languages:
        print("ERROR: The English OCR language is not installed in Windows.")
        return 1

    print("Windows OCR is ready. No Tesseract runtime is required for English OCR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
