@echo off
title AI Person — Launcher
echo ============================================
echo   AI Person v0.2.0 — Starting Services...
echo ============================================
echo.

:: Activate venv and start API server in new window
start "AI Person — API Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

:: Small delay to let API server bind port first
timeout /t 2 /nobreak >nul

:: Activate venv and start embedding worker in new window
start "AI Person — Embedding Worker" cmd /k "cd /d %~dp0 && call venv\Scripts\activate && python -m workers.run_embedding"

echo.
echo   [OK] API Server:       http://localhost:8000
echo   [OK] Swagger UI:       http://localhost:8000/docs
echo   [OK] Embedding Worker: running
echo.
echo   Close the CMD windows to stop services.
echo ============================================
