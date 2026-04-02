@echo off
REM ─────────────────────────────────────────────────────────────
REM  switch_model.bat  (Windows version)
REM  Run this to pick the best model for your machine.
REM ─────────────────────────────────────────────────────────────

echo.
echo  Model Switcher – Nova Personal Assistant
echo  ==========================================
echo.
echo  Your options:
echo.
echo  1) phi3:mini    - 1.8 GB RAM - Very fast - Good for chat
echo  2) gemma2:2b    - 2.0 GB RAM - Fast - Better reasoning
echo  3) mistral      - 4.1 GB RAM - Medium - Great all-rounder
echo  4) llama3.2:3b  - 2.0 GB RAM - Fast - Excellent quality
echo  5) llama3.1:8b  - 5.5 GB RAM - Slow - Best quality (needs 8GB+)
echo.
set /p choice="  Enter number (1-5): "

if "%choice%"=="1" set MODEL=phi3:mini & set CTX=1024 & set THR=4
if "%choice%"=="2" set MODEL=gemma2:2b & set CTX=1024 & set THR=4
if "%choice%"=="3" set MODEL=mistral & set CTX=2048 & set THR=4
if "%choice%"=="4" set MODEL=llama3.2:3b & set CTX=2048 & set THR=4
if "%choice%"=="5" set MODEL=llama3.1:8b & set CTX=2048 & set THR=2

if not defined MODEL echo Invalid choice & exit /b 1

echo.
echo  Pulling %MODEL% ...
ollama pull %MODEL%

REM Update .env using PowerShell
powershell -Command "(Get-Content .env) -replace '^OFFLINE_MODEL=.*', 'OFFLINE_MODEL=%MODEL%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^OLLAMA_NUM_CTX=.*', 'OLLAMA_NUM_CTX=%CTX%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^OLLAMA_NUM_THREAD=.*', 'OLLAMA_NUM_THREAD=%THR%' | Set-Content .env"

echo.
echo  Switched to %MODEL%
echo  Restart server: run start.bat
echo.
