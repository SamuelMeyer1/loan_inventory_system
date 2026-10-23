@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -B launcher.py
) else (
  python -B launcher.py
)
if errorlevel 1 pause
