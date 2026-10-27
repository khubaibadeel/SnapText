# SnapText 1.0 — Source audit and EXE packaging report

## Scope and results

Inspected the source archive supplied by the user, including the actual Windows PyInstaller specification, release workflow, Python entry point, OCR engine, application-data paths, UI modules, and tests. On this Linux analysis environment, source compilation succeeded and **21 tests passed** (`python -m pytest -q`). **The Windows EXE was not built or executed here:** PyInstaller requires building on Windows to target Windows, and Windows OCR/GUI cannot be functionally tested in this Linux environment.

## Architecture (code verified)

- `run.py` initializes the project import path and launches `snaptext_app.main.run()`.
- `snaptext_app/main.py` enables DPI awareness, obtains a Windows single-instance mutex, builds `MainWindow`, and enters Tk's event loop.
- `snaptext_app/ui/main_window.py` coordinates the screen snipper, clipboard image/file OCR, history, preview, global shortcuts, system tray, and OCR worker threads.
- `snaptext_app/core/ocr.py` selects Windows.Media.Ocr for English by default, loads PyWinRT bindings, initializes COM/WinRT per worker thread, and falls back to optional locally installed Tesseract when appropriate.
- `snaptext_app/core/paths.py` resolves frozen resources through `sys._MEIPASS`; user settings/history/logs are saved in writable `%APPDATA%\SnapText`, screenshots in `Pictures\SnapText`.
- `snaptext_app/core/system.py` uses `sys.executable` for Startup Registry entries when frozen, and a mutex prevents more than one instance.

## Packaging assessment

**Positive findings:** An onedir-oriented `SnapText.spec` already existed. Its asset paths, frozen-resource path handling, and Windows startup handling are appropriate. WinRT imported modules, tray backend, notifications, and optional `runtime/tesseract` directory were explicitly considered. There is a GitHub Actions release workflow on `windows-latest`, pinned to Python 3.12, which builds and archives `dist/SnapText`.

**Improvement made in this kit:** Updated the obsolete `PYZ(a.pure, a.zipped_data, cipher=...)` (PyInstaller 3/5 era) to the PyInstaller 6 form `PYZ(a.pure)`. Added `collect_data_files('customtkinter')` to the existing spec to explicitly collect CustomTkinter JSON themes and OTF font resources. CustomTkinter's own packaging documentation instructs users to bundle these non-Python assets. Disabled UPX (`upx=False`) to reduce executable-packaging complexity and potential scanning incompatibilities. Retained onedir layout and existing PyWinRT hidden imports. PyWinRT's official documentation describes its own PyInstaller hook for collecting dynamic namespace imports and `.pywinrt` tables; the kit's build uses this installed hook.

**Other risks to validate on a real Windows PC:**

1. The 21 unit tests do **not** exercise real Windows COM / WinRT OCR, foreground screen capture, hotkeys, Windows notifications, tray integration or frozen startup. Perform the Windows smoke tests below.
2. English recognition needs a functioning Windows OCR recognizer and installed language resources. Packaging Python bindings alone does not install Windows OCR language packs.
3. Urdu OCR is conditional: the source **does not bundle Tesseract**, unless `runtime/tesseract/tesseract.exe` is provided before building. For Urdu, install Tesseract with `urd.traineddata` (and `eng.traineddata` for mixed recognition), or provide a complete compatible runtime with language data. Do not ship a partial runtime.
4. A second launch may appear to do nothing while the first instance remains active in the tray; this is intentional single-instance behavior.
5. Windows global shortcuts may conflict with an existing app and can be affected by OS privileges and endpoint-security hooks.
6. `run.py` changes the working directory to its bundled script location. Most app paths correctly use `resource_path()` and `%APPDATA%`, so it is unlikely to break this application; nevertheless test when installed outside the source folder.
7. PyInstaller EXEs are unsigned by default. SmartScreen or endpoint protection can warn about unrecognized executables. Prefer no UPX, trusted local builds, and code signing for distribution. Do not disable security protections as a packaging workaround.
8. Some UI callbacks schedule `Tk.after` from background threads and Tk may be closing simultaneously; these are runtime robustness concerns, not packaging blockers. Validate rapidly closing during OCR and tray use.
9. `CLEAN_OLD_VERSION.bat` deletes `src` and `runtime/tesseract` folders without confirmation. It is not part of this build process and should not be run blindly if those folders contain data you need.

## Build on Windows (recommended)

1. Install **Python 3.12 x64** on the Windows 10/11 build PC (for reproducibility with the included CI workflow). Internet is needed for the initial dependency installation.
2. Extract the entire build-kit ZIP, then open its `SnapText` folder.
3. Double-click `BUILD_SNAPTEXT_EXE.bat`. It creates an isolated `.venv`, installs the dependencies, validates bindings, runs tests, and builds the onedir EXE.
4. Find the result at `SnapText\dist\SnapText\SnapText.exe`. Keep `SnapText\dist\SnapText\_internal` beside the EXE.
5. Double-click `CREATE_DESKTOP_SHORTCUT.bat` (optional) to create a desktop shortcut to that EXE.
6. Distribute the *whole* `dist\SnapText` folder, optionally compressed as ZIP. The target PC does **not** need Python; it **does** need a supported Windows build and the Windows OCR language support used by the application.

Manual commands instead of double-clicking:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm SnapText.spec
.venv\Scripts\python.exe scripts\verify_build.py
```

## Windows validation checklist

- [ ] Double-click `dist\SnapText\SnapText.exe`; UI opens, logo and icons/themes render.
- [ ] Start new capture using button and `Ctrl+Shift+S`; select a screen region; English OCR succeeds.
- [ ] Clipboard receives extracted text; preview opens; pasted result is correct.
- [ ] Capture from image file and clipboard image both work.
- [ ] Capture history survives restarting the EXE.
- [ ] Close to tray, restore, and exit; relaunch starts without stale mutex warnings.
- [ ] Test running with another cwd and with path containing spaces.
- [ ] Test a second Windows 10/11 PC **without Python** installed.
- [ ] If Urdu support is needed, verify Tesseract and `urd.traineddata` independently.

## Troubleshooting

- **`ModuleNotFoundError` for WinRT:** rebuild using Python 3.12 with the isolated `.venv`, and confirm `_winrt_windows_media_ocr*.pyd` and other WinRT resources exist in `dist\SnapText`.
- **CustomTkinter default theme not found:** verify `_internal\customtkinter\assets\themes\blue.json` is present, then rebuild using the patched spec.
- **OCR unavailable, application otherwise launches:** check Windows English OCR language under Windows language settings, then review `%APPDATA%\SnapText\app.log`. An installed Python binding is not the same as an available OCR recognizer.
- **No UI on second launch:** look for SnapText in the Windows system tray; exit the existing instance first.
- **Missing screen shortcut:** another process may own it; choose another shortcut in Settings.

## Why the onedir build is best for fast startup

Onefile PyInstaller builds need to unpack embedded dependencies at each launch and have higher startup overhead; onedir keeps dependencies extracted on disk. For this program's CustomTkinter resource files and PyWinRT runtime tables, onedir also avoids unnecessary packaging complexity. Use a desktop shortcut pinned to `dist\SnapText\SnapText.exe` for convenient double-click launch.
