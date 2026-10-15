# BreachX 2026 / HYDRA: Windows PowerShell Startup Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   BREACHX 2026 / HYDRA: COORDINATED BOT NETWORK DETECTION" -ForegroundColor Cyan
Write-Host "   Autonomous Full-Stack Cybersecurity Platform v1.7" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Python
Write-Host "[1/3] Checking Python 3.11+ environment..." -ForegroundColor Yellow
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $pyCmd) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
}

if ($null -eq $pyCmd) {
    Write-Host "ERROR: Python was not found on PATH. Please install Python 3.11+." -ForegroundColor Red
    exit 1
}

Write-Host "Found Python: $($pyCmd.Source)" -ForegroundColor Green

# Start Backend Server
Write-Host "[2/3] Starting FastAPI Detection Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "py" -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" -PassThru

Start-Sleep -Seconds 2

# Launch Browser
Write-Host "[3/3] Opening Interactive Cybersecurity Dashboard in browser..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000/"

Write-Host ""
Write-Host "HYDRA ENGINE IS RUNNING!" -ForegroundColor Green
Write-Host "Dashboard: http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate backend server." -ForegroundColor Gray

try {
    Wait-Process -Id $backendProcess.Id
} finally {
    if (-not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
}
