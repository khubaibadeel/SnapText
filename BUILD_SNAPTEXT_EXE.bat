@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SnapText - Build Windows EXE

echo =====================================================
echo  SnapText - clean Windows EXE build (Python 3.12 x64)
echo =====================================================
echo.

if not exist "run.py" (
    echo ERROR: Run this file from the SnapText source directory.
    goto :error
)
if not exist "SnapText.spec" (
    echo ERROR: SnapText.spec is missing.
    goto :error
)

rem Prefer the Windows Python launcher, pinned to 3.12.
py -3.12 -c "import sys; sys.exit(0 if sys.maxsize > 2**32 else 1)" >nul 2>&1
if not errorlevel 1 (
    echo Using Python 3.12 x64 via the py launcher.
    py -3.12 -m venv ".venv"
    if errorlevel 1 goto :error
) else (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)" >nul 2>&1
    if errorlevel 1 goto :no_python
    echo Using Python 3.12 x64 from PATH.
    python -m venv ".venv"
    if errorlevel 1 goto :error
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo ERROR: Could not create the Python virtual environment.
    goto :error
)

echo.
echo [1/5] Installing dependencies in an isolated environment...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%PYTHON%" -m pip install -r "requirements.txt"
if errorlevel 1 goto :error

echo.
echo [2/5] Checking Windows OCR libraries and CustomTkinter...
"%PYTHON%" -c "from winrt.windows.media.ocr import OcrEngine; import customtkinter; print('Python bindings found')"
if errorlevel 1 goto :error

echo.
echo [3/5] Validating source and running tests...
"%PYTHON%" -m compileall -q "run.py" "snaptext_app"
if errorlevel 1 goto :error
"%PYTHON%" -m pytest -q
if errorlevel 1 goto :error

echo.
echo [4/5] Building fast-start folder EXE...
"%PYTHON%" -m PyInstaller --clean --noconfirm "SnapText.spec"
if errorlevel 1 goto :error

echo.
echo [5/5] Checking output artifacts...
if not exist "dist\SnapText\SnapText.exe" (
    echo ERROR: Executable missing after build.
    goto :error
)
if not exist "dist\SnapText\_internal\customtkinter\assets\themes\blue.json" (
    echo ERROR: CustomTkinter default theme was not included.
    goto :error
)
set "WINRT_OK="
for /r "dist\SnapText" %%F in (_winrt_windows_media_ocr*.pyd) do set "WINRT_OK=1"
if not defined WINRT_OK (
    echo ERROR: The Windows OCR native binding is missing from dist.
    goto :error
)

echo.
echo BUILD COMPLETED: %CD%\dist\SnapText\SnapText.exe
echo Keep the _internal directory with SnapText.exe.
echo Double-click CREATE_DESKTOP_SHORTCUT.bat to add a shortcut.
echo.
explorer "%CD%\dist\SnapText"
pause
exit /b 0

:no_python
echo.
echo ERROR: Install 64-bit Python 3.12, then run this script again.
echo Download from https://www.python.org/downloads/release/python-3120/
echo Alternatively, install any later 3.12.x version.
pause
exit /b 1

:error
echo.
echo BUILD FAILED. Fix the error above; then run this script again.
echo Build logs are written to this console and the build folder.
pause
exit /b 1
