# Changelog

## Unreleased

### Fixed

- Prevented OCR/clipboard error callbacks from losing exception details before the UI handles them.
- Kept successful OCR results visible even when clipboard copy or screenshot saving fails.
- Hardened configuration and history loading against corrupt local JSON values.
- Removed destructive setup behavior that deleted a local `src` folder.

## 1.0 — 2026-07-17

### Fixed

- Removed the blocking “SnapText installation incomplete” dialog.
- Removed the mandatory Tesseract runtime download from development setup.
- Replaced mandatory executable-based English OCR with Windows' local OCR API.
- Fixed the broken **Run OCR Again** path that called a missing setup-window method.
- Prevented unsupported OCR language profiles from being selected in Settings.
- Added automatic fallback to English when an older configuration references an unavailable Urdu profile.
- Updated PyInstaller and GitHub Actions so release builds include the Windows OCR Python extensions.

### Changed

- Tesseract is now optional and detected automatically.
- Urdu profiles appear only when the current PC can actually recognize Urdu.
- OCR failures are shown as non-blocking inline status messages rather than technical popups.
- Windows and Linux are both used in continuous-integration tests.

## 1.0.1

- Added the professional interface, capture overlay, history, settings, tray support, shortcuts, and release automation.
