"""Check a Windows onedir distribution for key files (not a runtime smoke test)."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / 'dist' / 'SnapText'
checks = {
    'SnapText.exe': dist / 'SnapText.exe',
    'bundled icon': dist / '_internal' / 'icon.ico',
    'CustomTkinter theme': dist / '_internal' / 'customtkinter' / 'assets' / 'themes' / 'blue.json',
}
for title, path in checks.items():
    print(('OK' if path.is_file() else 'MISSING'), title, ':', path)
winrt = list(dist.rglob('_winrt_windows_media_ocr*.pyd')) if dist.is_dir() else []
print('OK' if winrt else 'MISSING', 'WinRT OCR native extension', winrt[:1])
raise SystemExit(0 if all(path.is_file() for path in checks.values()) and winrt else 1)
