param([string]$Command = "help")

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

switch ($Command) {
    "start" {
        Write-Host ""
        Write-Host "  AI Person v0.3.0 - Starting..." -ForegroundColor Cyan
        # Using single quotes for outer string to avoid PowerShell & parsing issues
        $apiArgs = "/k cd /d ""$ProjectRoot"" & call venv\Scripts\activate & uvicorn app.main:app --reload --port 8000"
        Start-Process cmd -ArgumentList $apiArgs
        Start-Sleep -Seconds 2
        $workerArgs = "/k cd /d ""$ProjectRoot"" & call venv\Scripts\activate & python -m workers.run_embedding"
        Start-Process cmd -ArgumentList $workerArgs
        Write-Host "  [OK] API:    http://localhost:8000" -ForegroundColor Green
        Write-Host "  [OK] Docs:   http://localhost:8000/docs" -ForegroundColor Green
        Write-Host "  [OK] Worker: running" -ForegroundColor Green
        Write-Host ""
    }
    "api" {
        & "$ProjectRoot\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
    }
    "worker" {
        & "$ProjectRoot\venv\Scripts\python.exe" -m workers.run_embedding
    }
    "migrate" {
        & "$ProjectRoot\venv\Scripts\python.exe" -m alembic upgrade head
    }
    "add" {
        & "$ProjectRoot\venv\Scripts\python.exe" -m cli.add_memory
    }
    "chat" {
        Set-Location "$ProjectRoot\AI_Chat"
        npm run dev
    }
    default {
        Write-Host ""
        Write-Host "  AI Person CLI v0.3.0" -ForegroundColor Cyan
        Write-Host "  =============================" -ForegroundColor Gray
        Write-Host "  .\ai start    Start API + Worker" -ForegroundColor White
        Write-Host "  .\ai api      Start API only" -ForegroundColor White
        Write-Host "  .\ai worker   Start Worker only" -ForegroundColor White
        Write-Host "  .\ai migrate  Run migrations" -ForegroundColor White
        Write-Host "  .\ai add      Add memory (interactive)" -ForegroundColor White
        Write-Host "  .\ai chat     Open Chat UI (React)" -ForegroundColor White
        Write-Host ""
    }
}
