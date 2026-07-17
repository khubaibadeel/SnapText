# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH)
runtime_dir = project_root / "runtime" / "tesseract"

datas = [
    ("icon.ico", "."),
    ("assets/icon.png", "assets"),
]

# Tesseract is an optional language/accuracy enhancement. A release may include
# it, but SnapText no longer refuses to build or start without it because
# English OCR uses Windows.Media.Ocr.
if (runtime_dir / "tesseract.exe").is_file():
    datas.append((str(runtime_dir), "runtime/tesseract"))

hiddenimports = [
    "customtkinter",
    "PIL",
    "pytesseract",
    "pyperclip",
    "keyboard",
    "pystray",
    "pystray._win32",
    "plyer.platforms.win.notification",
    "winrt",
    "winrt.runtime",
    "winrt.system",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.media.ocr",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
    "winrt.windows.system",
]


a = Analysis(
    ["run.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "numpy", "scipy", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SnapText",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=["icon.ico"],
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SnapText",
)
