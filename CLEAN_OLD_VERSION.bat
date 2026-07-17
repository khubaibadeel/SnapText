@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Cleaning files left by older SnapText packages...
for /d /r %%D in (__pycache__) do @if exist "%%D" rd /s /q "%%D" >nul 2>nul
if exist "src" rd /s /q "src"
if exist "runtime\tesseract" rd /s /q "runtime\tesseract"
if exist "build" rd /s /q "build"
if exist "SnapText.spec.bak" del /q "SnapText.spec.bak"

echo Old files removed. Run setup_development.bat next.
pause
