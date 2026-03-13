# RAAQIB NVR — Getting Started (End-to-end)

This guide shows a complete, copy-paste workflow to get Raaqib running from cloning the repo through starting the app, including creating and activating a `.venv`, installing dependencies, downloading the ONNX model into `models/`, and verifying the API.

Prerequisites
- Python 3.10+ installed and on PATH
- FFmpeg installed and on PATH
- Git (or download zip)

1) Clone the repository

```bash
# from any OS
git clone https://github.com/yourname/raaqib-nvr.git
cd "raaqib-nvr/MiniQvision"
pwd  # confirm project root contains app.py
```

2) Create and activate the virtual environment `.venv`

Windows (PowerShell):

```powershell
# create venv
python -m venv .venv
# if PowerShell blocks scripts, run once:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# activate
.\.venv\Scripts\Activate.ps1
# confirm
python -V
```

Windows (cmd.exe):

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
python -V
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -V
```

You should see `(.venv)` in your prompt and `python -V` should show 3.10+.

3) Upgrade pip and install Python dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If installation fails on Windows because of build tools, install Microsoft C++ Build Tools.

4) Download the ONNX model into `models/` (required)

Windows (PowerShell):

```powershell
if (!(Test-Path -Path models)) { New-Item -ItemType Directory -Path models }
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx" -OutFile "models\yolo11n.onnx"
```

macOS / Linux:

```bash
mkdir -p models
curl -L -o models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
# or
#wget -O models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
```

Alternate: if you have `yolo11n.pt`, export to ONNX locally with `ultralytics` (see INSTALLATION.md).

Verify model exists:

```bash
ls -l models/yolo11n.onnx
# Windows PowerShell
Get-ChildItem models\yolo11n.onnx
```

5) Run the application

Windows (PowerShell):

```powershell
# stop previous runs (optional)
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
# activate venv
.\.venv\Scripts\Activate.ps1
# start with local config
python app.py config_local.yaml
```

macOS / Linux:

```bash
pkill -f "python app.py" || true
source .venv/bin/activate
python app.py config_local.yaml
```

Expected top-level log summary:

```
RAAQIB NVR — Starting
Cameras: <n>
Model: models/yolo11n.onnx
Device: cpu
API: http://0.0.0.0:8000
All processes started. Press Ctrl+C to stop.
```

6) Verify API and view logs

PowerShell API check:

```powershell
Start-Sleep -Seconds 2 ; (Invoke-WebRequest http://localhost:8000/api/status).Content | ConvertFrom-Json | Select-Object status, uptime_seconds
```

curl (macOS/Linux):

```bash
sleep 2; curl -s http://localhost:8000/api/status | jq
```

Tail logs:

```powershell
Get-Content logs\raaqib.log -Tail 50 -Wait
```

```bash
tail -f logs/raaqib.log
```

7) Stop the system

- In the terminal where `python app.py` runs: press Ctrl+C
- Or force-kill on Windows: `Stop-Process -Name python -Force`

Troubleshooting
- "ONNX model not found": ensure `models/yolo11n.onnx` exists and restart the app.
- PowerShell activation blocked: run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` then activate.
- Dependency build errors on Windows: install Visual C++ Build Tools.

That's it — open http://localhost:8000/docs to explore the API and dashboard.
