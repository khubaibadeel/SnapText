<div align="center">

<img src="assets/icon.png" alt="SnapText icon" width="96" />

# SnapText

**Capture any screen region, extract its text, and copy it instantly.**

[![Tests](https://github.com/Khubaib295/SnapText/actions/workflows/tests.yml/badge.svg)](https://github.com/Khubaib295/SnapText/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D4?logo=windows&logoColor=white)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

SnapText is a focused Windows OCR utility built with Python and CustomTkinter. Press one shortcut, drag over visible text, and SnapText captures the selected area, recognizes it locally, and places the result on your clipboard.

SnapText 1.0 uses **Windows' built-in OCR for English**, so users are not asked to download, install, or locate `tesseract.exe`. If Tesseract is already available, SnapText detects it automatically and can expose optional Urdu profiles when the required language data is installed.

![SnapText main window](docs/screenshots/main-window.png)

## Highlights

- Modern light, dark, and system-aware interface
- DPI-aware, multi-monitor screen selection overlay
- OCR from a screen region, clipboard image, or image file
- Zero-configuration English OCR through Windows
- Optional Urdu and English + Urdu profiles when supported locally
- Fast, Balanced, and Accurate recognition modes
- Editable result preview with word and character counts
- Searchable history with thumbnails and date filters
- Automatic clipboard copy and optional screenshot saving
- Configurable global keyboard shortcuts
- Windows notifications, system tray, and launch-at-startup support
- Single-instance protection and remembered window position
- Automated Windows/Linux tests and tag-based GitHub Releases

## Interface

| Dark mode | Capture preview |
|---|---|
| ![SnapText dark mode](docs/screenshots/main-window-dark.png) | ![Capture preview](docs/screenshots/preview-window.png) |

| Capture history | Settings |
|---|---|
| ![Capture history](docs/screenshots/history-window.png) | ![SnapText settings](docs/screenshots/settings-window.png) |

## Keyboard Shortcuts

The defaults can be changed in **Settings → Capture**.

| Shortcut | Action |
|---|---|
| `Ctrl + Shift + S` | Start a new screen capture |
| `Ctrl + Shift + C` | Copy text from the latest capture |
| `Ctrl + O` | Open the screenshot folder while the main window is focused |
| `Ctrl + ,` | Open settings while the main window is focused |
| `Esc` or right-click | Cancel an active screen selection |

## Requirements

### Downloaded Windows release

- Windows 10 or Windows 11
- No separate OCR executable
- No manual OCR path configuration
- No internet connection while recognizing text

Download `SnapText-Windows.zip` from GitHub Releases, extract the complete folder, and run `SnapText.exe`. Keep the `_internal` folder beside the executable.

### Running from source

- Windows 10 or Windows 11
- Python 3.10 or newer
- Internet access once, while Python packages are installed

## Installation from Source

```bash
git clone https://github.com/Khubaib295/SnapText.git
cd SnapText
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install and verify the required packages:

```powershell
setup_development.bat
```

Run SnapText:

```powershell
python run.py
```

The setup no longer downloads Tesseract or any third-party OCR installer. It installs the Python bindings required to call Windows' local OCR API and verifies that the API can start.

## Optional Urdu OCR

SnapText displays only recognition profiles available on the current PC.

- English works through Windows OCR on a normal Windows 10/11 installation.
- Urdu appears when Windows provides an Urdu recognizer or when a detected Tesseract installation contains `urd.traineddata`.
- English + Urdu appears when Tesseract can recognize both languages.

A missing optional Urdu engine never blocks English capture.

## Build the Windows Executable

```powershell
setup_development.bat
pyinstaller --noconfirm SnapText.spec
```

The complete application folder is created at:

```text
dist\SnapText\
```

Distribute the whole folder or the GitHub-generated ZIP—not `SnapText.exe` by itself.

## Publish a GitHub Release

The release workflow builds and publishes `SnapText-Windows.zip` whenever a version tag is pushed:

```bash
git add .
git commit -m "Release SnapText 1.0"
git tag v1.0
git push origin main
git push origin v1.0
```

GitHub Actions installs the Windows OCR bindings, runs the tests, builds the complete Windows application folder, checks that the OCR extension is included, packages it, and creates the release automatically.

## Testing

```bash
python -m pytest -q
```

Regenerate product screenshots from the real UI:

```bash
python scripts/capture_screenshots.py
```

The Windows manual validation checklist is available in [docs/TESTING.md](docs/TESTING.md).

## Project Structure

```text
SnapText/
├── .github/workflows/      # Tests and Windows release automation
├── assets/                 # Product artwork
├── docs/screenshots/       # README screenshots generated from the real UI
├── scripts/                # Screenshot utility
├── snaptext_app/core/               # OCR, capture, configuration, tray, shortcuts, and OS integration
├── snaptext_app/ui/                 # Main, preview, history, and settings windows
├── tests/                  # Automated tests
├── icon.ico                # Multi-resolution Windows icon
├── SnapText.spec           # PyInstaller build definition
├── version_info.txt        # Windows executable metadata
└── run.py                  # Application entry point
```

## Local Data

SnapText stores settings, history, and rotating logs under the current user's application-data directory. Screenshots are stored under `Pictures\SnapText` by default. Clearing history does not delete screenshot files.

## Current Limitations

- OCR quality depends on font size, contrast, image quality, and correct language selection.
- Optional Urdu recognition depends on a compatible language recognizer being installed locally.
- Global shortcuts can fail when another application owns the same combination or security software blocks keyboard hooks.
- The complete release folder must remain intact.
- Windows is the supported production platform; other systems are used only for basic development testing.

## Author

**Khubaib Adeel**

- GitHub: [@Khubaib295](https://github.com/Khubaib295)
- Instagram: [@khubaib_adeel](https://www.instagram.com/khubaib_adeel/)
- Email: [khubaibadeelkamboh@gmail.com](mailto:khubaibadeelkamboh@gmail.com)

## License

This project is released under the [MIT License](LICENSE).
