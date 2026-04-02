@echo off
echo.
echo  Nova - Personal AI Assistant
echo  ==============================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No venv found. Using system Python.
)

REM Start Ollama if installed
where ollama >nul 2>&1
if %errorlevel% == 0 (
    echo Starting Ollama...
    start /B ollama serve
    timeout /t 2 /nobreak >nul
    echo Ollama is ready.
) else (
    echo Ollama not found. Online mode only.
)

echo.
echo Starting server at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
