# RAAQIB NVR - Installation

Simple setup guide for running this project locally.

## What You Need

- Python 3.10+
- FFmpeg (available in PATH)
- Git
- Node.js 20+
- pnpm

## 0) Install System Dependencies

Use one set of commands based on your OS.

### Windows (PowerShell, using winget)

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
winget install Git.Git
winget install OpenJS.NodeJS.LTS
```

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git nodejs npm
```

### macOS (Homebrew)

```bash
brew install python ffmpeg git node
```

## 1) Clone the Project

```bash
git clone https://github.com/Raaaqib/MiniQvision.git
cd MiniQvision
```

If you already have the project folder, just open it in your terminal.

## 2) Create and Activate Python Environment

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3) Install Backend Dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 4) Install Node.js and pnpm

Install Node.js 20 LTS, then install pnpm:

```bash
npm install -g pnpm
```

Check versions:

```bash
node -v
pnpm -v
```

## 5) Install Frontend Dependencies

```bash
cd src/web
pnpm install
cd ../..
```

## 6) Download YOLO ONNX Model

Create the models folder and download `yolo11n.onnx`:

### Windows (PowerShell)

```powershell
if (!(Test-Path models)) { New-Item -ItemType Directory -Path models }
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx" -OutFile "models\yolo11n.onnx"
```

### macOS / Linux

```bash
mkdir -p models
curl -L -o models/yolo11n.onnx "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
```

## 7) Run the Backend

```bash
python app.py config_local.yaml
```

Backend API docs:

- http://localhost:8000/docs

## 8) Run the Frontend (Second Terminal)

```bash
cd src/web
pnpm run dev
```

Frontend URL:

- http://localhost:5173

## Quick Verification

Run these checks:

```bash
python --version
ffmpeg -version
node -v
pnpm -v
```

If all commands work and both servers start, setup is complete.