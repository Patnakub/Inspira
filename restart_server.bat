@echo off
REM === Setup log path ===
set "LOGFILE=C:\Users\Lenovo\Desktop\exhibition-backend\server_restart_log.txt"
echo [%date% %time%] Attempting to restart server... >> "%LOGFILE%"

REM === Stop existing Node server (if running) ===
taskkill /F /IM node.exe >nul 2>&1

REM === Wait for process to fully close ===
timeout /t 2 /nobreak >nul

REM === Navigate to server folder ===
cd /d "C:\Users\Lenovo\Desktop\exhibition-backend"

REM === Start server and keep it open ===
echo [%date% %time%] Starting server... >> "%LOGFILE%"
start "NodeServer" cmd /k "node server.js"
