@echo off
title TechXfluence AI
cd /d "%~dp0"
echo ==========================================
echo         TechXfluence AI - Starting
echo ==========================================
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create virtual environment. Install Python and tick "Add to PATH".
    pause & exit /b 1
  )
)
call .venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo Package install failed. Check your internet connection.
  pause & exit /b 1
)
where ollama >nul 2>nul
if errorlevel 1 echo [WARNING] Ollama not found. Install from https://ollama.com/download then run: ollama pull llama3.2
echo.
echo Opening chatbot at http://localhost:8501  (Ctrl+C to stop)
call .venv\Scripts\python.exe -m streamlit run app.py
pause
