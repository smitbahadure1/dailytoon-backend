@echo off
echo Starting Daily Toon Backend...
echo.

REM Start backend server
start "Backend Server" cmd /k "cd /d %~dp0 && python server_pollinations.py"

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Start ngrok
start "Ngrok Tunnel" cmd /k "ngrok http 8000 --host-header=rewrite"

echo.
echo ========================================
echo Daily Toon Backend is starting!
echo ========================================
echo.
echo Backend server and ngrok are running in separate windows.
echo.
echo IMPORTANT: 
echo 1. Wait for ngrok to show the URL
echo 2. Copy the https://....ngrok-free.dev URL
echo 3. If the URL changed, you need to rebuild the APK
echo.
echo To stop: Close both terminal windows
echo ========================================
pause
