@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Virtual environment not found. See README.md.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" "launch_ai.py"
if errorlevel 1 pause
