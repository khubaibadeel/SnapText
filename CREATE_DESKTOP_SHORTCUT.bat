@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\make_desktop_shortcut.ps1"
if errorlevel 1 (
    echo Failed to create shortcut. Make sure the EXE has already been built.
    pause
    exit /b 1
)
echo.
pause
