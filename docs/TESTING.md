# SnapText Windows validation checklist

Run this checklist before publishing a release.

## Clean setup

- Use Windows 10 or Windows 11 with Python 3.12.
- Do not install Tesseract.
- Run `setup_development.bat`.
- Confirm the script installs requirements without downloading an OCR executable.
- Run `python run.py` and confirm the footer reports **Windows OCR ready**.

## Core capture flow

- Press `Ctrl + Shift + S`.
- Select text across one monitor, then repeat on a second monitor.
- Test Windows display scaling at 100%, 125%, and 150%.
- Confirm `Esc` and right-click cancel cleanly.
- Confirm English text is extracted and copied.
- Confirm the application never shows an “installation incomplete” popup.

## Other input methods

- Copy an image and use **From Clipboard**.
- Use **Open Image** with PNG, JPEG, BMP, TIFF, and WebP files.
- Test an empty or low-contrast image and confirm a normal empty state appears.

## Settings and history

- Confirm the OCR tab reports the active engine and only lists supported language profiles.
- Change the global shortcuts and restart SnapText.
- Search and filter history.
- Delete one entry and clear all entries, confirming destructive actions.
- Toggle notifications, system tray, startup, and appearance settings.

## Optional Tesseract fallback

- Install Tesseract separately only for this test.
- Add English and Urdu trained data.
- Restart SnapText and confirm Urdu and English + Urdu profiles appear automatically.
- Remove or rename Tesseract and confirm English continues through Windows OCR.

## Release build

- Run `pyinstaller --noconfirm SnapText.spec`.
- Confirm `dist\SnapText\SnapText.exe` exists.
- Confirm the release contains the WinRT OCR extension in `_internal`.
- Test the complete folder on a Windows account without Python or Tesseract.
- Confirm copying `SnapText.exe` alone is documented as unsupported.
