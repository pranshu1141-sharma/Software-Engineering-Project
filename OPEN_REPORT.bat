@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0open_report.ps1"
if errorlevel 1 pause
