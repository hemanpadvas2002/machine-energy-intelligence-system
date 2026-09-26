@echo off
echo ============================================================
echo   Machine Energy Intelligence System — Starting...
echo ============================================================

IF EXIST ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [START] Virtual environment activated
) ELSE (
    echo [START] WARNING: No .venv found. Run setup first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
)

python START.py
pause
