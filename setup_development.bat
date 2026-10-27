@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Preparing SnapText 1.0 development environment...
echo Project folder: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Install 64-bit Python 3.10 or newer, then run this file again.
    goto :error
)

rem Remove Python bytecode caches only. Do not delete source folders during setup.
for /d /r %%D in (__pycache__) do @if exist "%%D" rd /s /q "%%D" >nul 2>nul

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Verifying the exact SnapText code that will run...
python scripts\verify_installation.py
if errorlevel 1 goto :error

echo.
echo Setup complete.
echo Start SnapText with: python run.py
pause
exit /b 0

:error
echo.
echo Setup failed. Review the message above.
pause
exit /b 1
