@echo off
title Kids Video Automation
echo ========================================
echo   Kids Video Automation Pipeline
echo ========================================
echo.

echo [1/3] Starting API server (port 8787)...
start /B pythonw C:\Users\khali\kids-video-agent\api_server.py
timeout /t 3 /nobreak >nul

echo [2/3] Starting n8n (port 5678)...
start /B n8n start
timeout /t 10 /nobreak >nul

echo [3/3] Opening n8n workflow...
start http://localhost:5678/workflow/d8f485e4-8166-4150-ad5d-a2c8dd3c740f

echo.
echo ========================================
echo   Both servers running!
echo   API:  http://localhost:8787
echo   n8n:  http://localhost:5678
echo ========================================
echo.
echo Click "Execute Workflow" in n8n
echo.
echo To stop: close this window
echo.
pause
