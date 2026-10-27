@echo off
setlocal
cd /d "%~dp0"
python run.py
if errorlevel 1 (
    echo.
    echo SnapText stopped because of an error.
    pause
)
