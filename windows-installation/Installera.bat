@echo off
setlocal
title Installera Loan Inventory System
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installera.ps1"
if errorlevel 1 (
  echo.
  echo Installationen misslyckades. Las felmeddelandet ovan.
  pause
  exit /b 1
)
echo.
echo Installationen ar klar.
pause
