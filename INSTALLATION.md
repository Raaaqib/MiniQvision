# RAAQIB NVR — Installation Guide

Complete step-by-step guide to install Raaqib from scratch, including Python, FFmpeg, dependencies, and initial setup.

## Table of Contents

- [System Requirements](#system-requirements)
- [Platform-Specific Installation](#platform-specific-installation)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
  - [macOS (Intel & Apple Silicon)](#macos-intel--apple-silicon)
  - [Windows 10/11](#windows-1011)
- [Verify Installation](#verify-installation)
- [Post-Installation Setup](#post-installation-setup)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Specifications

- **OS**: Linux, macOS, or Windows 10/11
- **CPU**: Intel Core i5 / AMD Ryzen 5 (or equivalent ARM)
- **RAM**: 2 GB (4 GB+ recommended)
- **Storage**: 20 GB minimum (SSD recommended for logs/database)
- **Python**: 3.10 or newer
- **FFmpeg**: 4.4 or newer

### GPU Support (Optional)

- **NVIDIA**: CUDA compute capability 3.5+ (GeForce GTX 750 or newer)
- **AMD**: ROCm 5.0+ (for development machines)
- **Apple Silicon**: Metal acceleration (automatic)
- **Google Coral**: Edge TPU for inference (~4W power usage)

### Network

- 100 Mbps+ for streaming multiple cameras
- RTSP capable network devices (cameras)

---

## Platform-Specific Installation

### Linux (Ubuntu/Debian)

#### Step 1: Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

#### Step 2: Install Python 3.10+

Check current Python version:

```bash
python3 --version
```

If you have Python 3.10 or newer, skip to FFmpeg. Otherwise:

**Ubuntu 22.04+ (has Python 3.10 by default)**:
```bash
sudo apt install python3-pip python3-venv python3-dev -y
```

**Ubuntu 20.04 (has Python 3.8 by default)**:
```bash
sudo apt install python3.10 python3.10-venv python3.10-dev python3-pip -y
# Set as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

#### Step 3: Install FFmpeg

```bash
sudo apt install ffmpeg libsm6 libxext6 libxrender-dev -y
```

Verify FFmpeg installed:
```bash
ffmpeg -version
```

#### Step 4: Install Build Tools

```bash
sudo apt install build-essential git -y
```

#### Step 5: Clone Repository & Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/yourname/raaqib-nvr.git
cd raaqib-nvr/Raaqib-Docker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

#### Step 6: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**For GPU support (NVIDIA CUDA)**:
```bash
# Install CUDA 12.1 (if not already installed)
# See https://developer.nvidia.com/cuda-downloads

# Install cuDNN
# Download from https://developer.nvidia.com/cudnn

# Then install GPU-accelerated packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

#### Step 7: Verify Installation

```bash
# Test Python
python --version

# Test FFmpeg
ffmpeg -version

# Test dependencies
python -c "import cv2, numpy, yaml, fastapi; print('✓ All dependencies installed')"
```

---

### macOS (Intel & Apple Silicon)

#### Step 1: Install Homebrew

If not installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Step 2: Install Python 3.10+

```bash
brew install python@3.10
```

Set as default:
```bash
export PATH="/usr/local/opt/python@3.10/bin:$PATH"
```

Verify:
```bash
python3 --version
```

#### Step 3: Install FFmpeg

```bash
brew install ffmpeg
```

Verify:
```bash
ffmpeg -version
```

#### Step 4: Install Git

```bash
brew install git
```

#### Step 5: Clone Repository & Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/yourname/raaqib-nvr.git
cd raaqib-nvr/Raaqib-Docker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

#### Step 6: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**For Apple Silicon (M1/M2/M3) GPU acceleration**:

Metal acceleration is automatic with PyTorch. Optional for better performance:

```bash
pip install torch torchvision torchaudio
```

#### Step 7: Verify Installation

```bash
# Test Python
python --version

# Test FFmpeg
ffmpeg -version

# Test dependencies
python -c "import cv2, numpy, yaml, fastapi; print('✓ All dependencies installed')"
```

---

### Windows 10/11

#### Step 1: Install Python 3.10+

1. Download from [python.org](https://www.python.org/downloads/)
2. Run installer
3. **✓ CHECK**: "Add Python to PATH"
4. Click "Disable path length limit" (Windows 11)

Verify installation:
```powershell
python --version
pip --version
```

#### Step 2: Install FFmpeg

**Option A: Using Chocolatey** (recommended)

```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg -y
```

**Option B: Manual Installation**

1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to `C:\Program Files\ffmpeg`
3. Add to PATH:
   - Win+X → System → Advanced system settings
   - Environment Variables → Path → New
   - Add `C:\Program Files\ffmpeg\bin`

Verify installation (restart terminal after):
```powershell
ffmpeg -version
```

#### Step 3: Install Git

Download from [git-scm.com](https://git-scm.com/) and install.

#### Step 4: Clone Repository

Open PowerShell and run:

```powershell
# Clone the repository
git clone https://github.com/yourname/raaqib-nvr.git
cd raaqib-nvr/Raaqib-Docker

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel
```

#### Step 5: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

**For NVIDIA GPU (CUDA 12.1)**:

```powershell
# Install CUDA + cuDNN from NVIDIA website

# Install GPU-accelerated PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install remaining dependencies
pip install -r requirements.txt
```

#### Step 6: Verify Installation

```powershell
# Test Python
python --version

# Test FFmpeg
ffmpeg -version

# Test dependencies
python -c "import cv2, numpy, yaml, fastapi; print('✓ All dependencies installed')"
```

---

## Verify Installation

Run this test to ensure everything is working:

```bash
python -c "
import sys
import cv2
import numpy as np
import yaml
import pydantic
import fastapi
import onnxruntime
import PIL

print(f'✓ Python {sys.version.split()[0]}')
print(f'✓ OpenCV {cv2.__version__}')
print(f'✓ NumPy {np.__version__}')
print(f'✓ PyYAML {yaml.__version__}')
print(f'✓ ONNX Runtime {onnxruntime.__version__}')
print(f'✓ FastAPI {fastapi.__version__}')
print('✓ All core dependencies installed!')
"
```

Check FFmpeg:
```bash
ffmpeg -version | head -n 1
```

---

## Post-Installation Setup

### 1. Download YOLO Model (Optional)

The first time you run Raaqib, it will auto-download the YOLO model (~100-700 MB depending on size).

To pre-download:

```bash
# Activate virtual environment first
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

### 2. Create Configuration File

Copy the example configuration:

```bash
cp config/config.yaml.example config/config.yaml
```

Or create manually:

```yaml
# config/config.yaml
cameras:
  - id: camera1
    name: "Main Camera"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    enabled: true
    fps_target: 10

detection:
  model: "yolo11n.pt"
  confidence: 0.45
  device: "cpu"
  pool_size: 2

recording:
  enabled: true
  pre_capture_s: 3
  post_capture_s: 8

api:
  host: "0.0.0.0"
  port: 8000
```

### 3. Test Your Configuration

```bash
# Validate config file
python -c "from config import load_config; c = load_config('config.yaml'); print(f'✓ Config loaded: {len(c.enabled_cameras)} cameras')"
```

### 4. Create Directories (Auto-created on first run)

```bash
mkdir -p recordings snapshots logs
```

---

## Troubleshooting

### Python Version Issues

**Problem**: `python --version` shows 3.8 or 3.9

**Solution**:
```bash
# Linux/macOS
python3.10 --version
python3.10 -m venv venv

# Windows
py -3.10 --version
py -3.10 -m venv venv
```

### FFmpeg Not Found

**Linux**:
```bash
sudo apt install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

**Windows**:
Check if ffmpeg is in PATH:
```powershell
Get-Command ffmpeg
# If not found, restart PowerShell after FFmpeg installation
```

### Permission Denied (Linux/macOS)

```bash
# Fix venv permissions
chmod +x venv/bin/activate
```

### Package Installation Errors

**`error: Microsoft Visual C++ 14.0 is required` (Windows)**

Download Visual C++ Build Tools:
```
https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**`pip: No module named pip` (any platform)**

```bash
python -m pip install --upgrade pip
```

### Virtual Environment Issues

Reset and recreate:

```bash
# Remove old venv
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows

# Create fresh venv
python -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows
```

### GPU Not Detected

**NVIDIA (check CUDA installation)**:
```bash
nvidia-smi
```

If command not found, install CUDA from:
```
https://developer.nvidia.com/cuda-downloads
```

**Reset GPU (if system freezes)**:
```bash
nvidia-smi -i 0 -pm 1  # Enable persistence mode (requires reboot)
```

---

## Next Steps

1. **Configure cameras**: See [README.md - Configuration](README.md#configuration)
2. **Run the system**: See [RUNNING.md](RUNNING.md)
3. **API documentation**: See [API.md](API.md)
4. **Advanced configuration**: See [CONFIGURATION.md](CONFIGURATION.md)

---

## Getting Help

- Check logs: `cat logs/raaqib.log`
- Test FFmpeg with your camera:
  ```bash
  ffmpeg -rtsp_transport tcp -i "rtsp://user:pass@camera-ip:554/stream" -t 5 -f null -
  ```
- Review [README.md - Troubleshooting](README.md#troubleshooting)
