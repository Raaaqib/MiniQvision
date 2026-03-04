@echo off
:: ─────────────────────────────────────────────────────────────────────────────
::  Raaqib NVR — Stop
::  Kills all camera streams and shuts down Docker containers.
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo [Raaqib NVR] Stopping...

:: Kill any ffmpeg processes streaming to RTSP
echo   Stopping camera streams...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-Job -Name 'cam*' -ErrorAction SilentlyContinue | Stop-Job; Get-Job -Name 'cam*' -ErrorAction SilentlyContinue | Remove-Job -Force; taskkill /IM ffmpeg.exe /F 2>$null; Write-Host '  Camera streams stopped.' -ForegroundColor Green"

:: Stop Docker containers
echo   Stopping Docker containers...
cd /d "%~dp0"
docker compose down

echo.
echo [Raaqib NVR] Stopped. Goodbye.
pause
