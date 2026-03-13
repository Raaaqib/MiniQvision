# ─────────────────────────────────────────────────────────────────────────────
#  Raaqib NVR — Smart Launcher
#  Detects your webcams, streams them to Docker, opens the UI.
# ─────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "  ██████╗  █████╗  █████╗  ██████╗ ██╗██████╗ " -ForegroundColor Cyan
Write-Host "  ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗" -ForegroundColor Cyan
Write-Host "  ██████╔╝███████║███████║██║   ██║██║██████╔╝" -ForegroundColor Cyan
Write-Host "  ██╔══██╗██╔══██║██╔══██║██║▄▄ ██║██║██╔══██╗" -ForegroundColor Cyan
Write-Host "  ██║  ██║██║  ██║██║  ██║╚██████╔╝██║██████╔╝" -ForegroundColor Cyan
Write-Host "  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══▀▀═╝ ╚═╝╚═════╝ " -ForegroundColor Cyan
Write-Host "  NVR SYSTEM — Starting..." -ForegroundColor DarkCyan
Write-Host ""

# ── 1. Check Docker ───────────────────────────────────────────────────────────
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
try {
    $null = docker info 2>&1
} catch {
    Write-Host "  ERROR: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    Read-Host "  Press Enter to exit"
    exit 1
}
Write-Host "  Docker is running." -ForegroundColor Green

# ── 2. Check ffmpeg ───────────────────────────────────────────────────────────
Write-Host "[2/4] Checking ffmpeg..." -ForegroundColor Yellow
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: ffmpeg not found in PATH." -ForegroundColor Red
    Write-Host "  Download from https://www.gyan.dev/ffmpeg/builds/ and add to PATH." -ForegroundColor Red
    Read-Host "  Press Enter to exit"
    exit 1
}
Write-Host "  ffmpeg found." -ForegroundColor Green

# ── 3. Detect webcams via dshow ───────────────────────────────────────────────
Write-Host "[3/4] Detecting cameras..." -ForegroundColor Yellow
$rawOutput = & ffmpeg -list_devices true -f dshow -i dummy 2>&1 | Out-String
$cameraNames = @()
foreach ($line in ($rawOutput -split "`n")) {
    # Match lines like: [dshow ...] "Camera Name" (video)
    if ($line -match '"(.+?)"\s+\(video\)') {
        $name = $matches[1].Trim()
        # Skip audio-only virtual devices, keep real video devices
        if ($name -notmatch 'audio|Audio|screen|Screen') {
            $cameraNames += $name
        }
    }
}

if ($cameraNames.Count -eq 0) {
    Write-Host "  WARNING: No webcams detected. Only IP/RTSP cameras (if configured) will be active." -ForegroundColor Yellow
} else {
    Write-Host "  Found $($cameraNames.Count) camera(s):" -ForegroundColor Green
    for ($i = 0; $i -lt $cameraNames.Count; $i++) {
        Write-Host "    cam$($i+1): $($cameraNames[$i])" -ForegroundColor White
    }
}

# ── 4. Start Docker containers ────────────────────────────────────────────────
Write-Host "[4/4] Starting Docker containers..." -ForegroundColor Yellow
$buildFlag = if (Test-Path ".\Dockerfile") { "--build" } else { "" }
$composeOut = docker compose up -d $buildFlag 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR starting containers:" -ForegroundColor Red
    $composeOut | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Read-Host "  Press Enter to exit"
    exit 1
}
Write-Host "  Containers started." -ForegroundColor Green

# ── 5. Stream webcams to mediamtx RTSP relay ─────────────────────────────────
$streamJobs = @()
if ($cameraNames.Count -gt 0) {
    Write-Host ""
    Write-Host "[+] Streaming cameras to RTSP relay..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2   # give mediamtx a moment to be ready

    $maxCams = [Math]::Min($cameraNames.Count, 4)
    for ($i = 0; $i -lt $maxCams; $i++) {
        $camName  = $cameraNames[$i]
        $slot     = "cam$($i + 1)"
        $rtspUrl  = "rtsp://localhost:8554/$slot"
        Write-Host "  Streaming '$camName' → $rtspUrl" -ForegroundColor Cyan

        $job = Start-Job -Name $slot -ScriptBlock {
            param($camName, $rtspUrl)
            while ($true) {
                & ffmpeg -f dshow -rtbufsize 100M `
                    -i "video=$camName" `
                    -c:v libx264 -preset ultrafast -tune zerolatency `
                    -b:v 1500k -maxrate 1500k -bufsize 3000k `
                    -pix_fmt yuv420p -g 30 `
                    -f rtsp $rtspUrl 2>&1
                Start-Sleep -Seconds 2   # auto-restart on disconnect
            }
        } -ArgumentList $camName, $rtspUrl

        $streamJobs += $job
    }
    Write-Host "  All camera streams started." -ForegroundColor Green
}

# ── 6. Open browser ────────────────────────────────────────────────────────────
Start-Sleep -Seconds 3
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host "  Raaqib NVR is RUNNING" -ForegroundColor Green
Write-Host "  Web UI  : http://localhost:8000/ui" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Dashboard: http://localhost:8501" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host ""
Start-Process "http://localhost:8000/ui"

# ── 7. Keep alive + cleanup on Ctrl+C ─────────────────────────────────────────
Write-Host "  Press Ctrl+C to stop all streams (Docker keeps running)." -ForegroundColor DarkGray
Write-Host "  Run stop.bat to shut everything down." -ForegroundColor DarkGray
Write-Host ""

try {
    while ($true) { Start-Sleep -Seconds 30 }
} finally {
    Write-Host ""
    Write-Host "  Stopping camera streams..." -ForegroundColor Yellow
    $streamJobs | ForEach-Object { Stop-Job $_; Remove-Job $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "  Streams stopped. Docker containers are still running." -ForegroundColor Green
    Write-Host "  Run stop.bat to shut down Docker too." -ForegroundColor DarkGray
}
