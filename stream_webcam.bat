@echo off
echo ═══════════════════════════════════════════════════════
echo   Raaqib NVR — Stream Laptop Camera to Docker
echo ═══════════════════════════════════════════════════════
echo.
echo This streams your laptop webcam to the RTSP relay server
echo so Docker can access it.
echo.
echo Press Ctrl+C to stop streaming.
echo.

REM ── List available cameras ──
echo Available video devices:
ffmpeg -list_devices true -f dshow -i dummy 2>&1 | findstr /C:"video"
echo.

REM ── Stream both cameras to RTSP relay in parallel ──
echo Starting HP TrueVision HD Camera stream on rtsp://localhost:8554/laptop
start "Cam1-Laptop" ffmpeg -f dshow -i video="HP TrueVision HD Camera" ^
  -c:v libx264 -preset ultrafast -tune zerolatency ^
  -b:v 1500k -maxrate 1500k -bufsize 3000k ^
  -pix_fmt yuv420p -g 30 ^
  -f rtsp rtsp://localhost:8554/laptop

echo Starting DroidCam Video stream on rtsp://localhost:8554/droidcam
start "Cam2-DroidCam" ffmpeg -f dshow -i video="DroidCam Video" ^
  -c:v libx264 -preset ultrafast -tune zerolatency ^
  -b:v 1500k -maxrate 1500k -bufsize 3000k ^
  -pix_fmt yuv420p -g 30 ^
  -f rtsp rtsp://localhost:8554/droidcam

echo.
echo Both streams started in separate windows. Close those windows to stop streaming.
echo Press any key to exit this window.
pause > nul
