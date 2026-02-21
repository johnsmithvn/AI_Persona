@echo off
:: AI Person CLI — Quick launcher
:: Usage: ai <command>
::   ai start    — Start API + Worker
::   ai api      — Start API only
::   ai worker   — Start Worker only
::   ai migrate  — Run alembic upgrade head
::   ai help     — Show this help

cd /d %~dp0\..

if "%1"=="" goto help
if "%1"=="start" goto start
if "%1"=="api" goto api
if "%1"=="worker" goto worker
if "%1"=="migrate" goto migrate
if "%1"=="help" goto help
echo Unknown command: %1
goto help

:start
call start.bat
goto end

:api
call venv\Scripts\activate && uvicorn app.main:app --reload --port 8000
goto end

:worker
call venv\Scripts\activate && python -m workers.run_embedding
goto end

:migrate
call venv\Scripts\activate && alembic upgrade head
goto end

:help
echo.
echo   AI Person CLI v0.2.0
echo   ====================
echo   ai start    Start API server + Embedding worker
echo   ai api      Start API server only
echo   ai worker   Start Embedding worker only
echo   ai migrate  Run database migrations
echo   ai help     Show this help
echo.
goto end

:end
