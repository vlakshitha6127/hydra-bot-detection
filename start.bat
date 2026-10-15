@echo off
title BreachX 2026 / HYDRA Detection Engine
echo ==========================================================
echo    BREACHX 2026 / HYDRA: COORDINATED BOT NETWORK DETECTION
echo    Autonomous Full-Stack Cybersecurity Platform v1.7
echo ==========================================================
echo.
echo [1/2] Launching BreachX FastAPI Detection Engine on port 8000...
start "BreachX Backend" py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak >nul
echo [2/2] Opening Interactive Cybersecurity Dashboard...
start http://127.0.0.1:8000/
echo.
echo BreachX / HYDRA is running at http://127.0.0.1:8000/
echo API documentation available at http://127.0.0.1:8000/docs
pause
