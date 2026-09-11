@echo off
set PYTHONIOENCODING=utf-8
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_streamlit_https_cert.ps1"
if errorlevel 1 pause && exit /b 1
python launch.py
pause
