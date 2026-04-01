# Running On Windows With Webcam

This guide is only for running the project on Windows with a local webcam.
Installation steps are intentionally not repeated here.

For installation, use [INSTALLATION.md](INSTALLATION.md).

## 1. Open PowerShell In Project Root

Run commands from the project folder:

```powershell
cd <path-to-your-project>\raqiv_nvr
```

## 2. Ensure The ONNX Model Exists

This project expects an ONNX model file for detection.

Check model folder:

```powershell
Get-ChildItem .\models
```

If `yolo11n.onnx` is missing, download it:

```powershell
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx" -OutFile ".\models\yolo11n.onnx"
```

## 3. Run With Local Webcam Config

Use the existing local config file:

```powershell
.\venv\Scripts\python.exe app.py config_local.yaml
```

This uses [config_local.yaml](config_local.yaml), where webcam source is currently set to `"0"`.

## 4. Run Frontend (web)

The frontend lives in `./web`.

In a new terminal:

```powershell
cd .\web
npm install
npm run dev
```

Frontend dev URL (Vite default):

- http://localhost:5173

## 5. Open The UI

After startup, use:

- UI: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/status
- Frontend Dev UI: http://localhost:5173

Quick health check from PowerShell:

```powershell
(Invoke-WebRequest http://localhost:8000/api/status -UseBasicParsing).Content
```

## 6. Stop The App

In the terminal where app is running, press `Ctrl+C`.

To stop frontend dev server, press `Ctrl+C` in the `npm run dev` terminal.

If the process is stuck:

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```

## Troubleshooting

### Error: ONNX model not found

Symptom includes: `ONNX model not found: yolo11n.onnx`.

Fix:

1. Confirm file exists in [models](models).
2. Confirm [config_local.yaml](config_local.yaml) has `detection.model: "yolo11n.onnx"`.
3. Restart the app.

### Webcam not detected or wrong camera

Edit [config_local.yaml](config_local.yaml) camera `source`.

Common values:

- `"0"` first camera
- `"1"` second camera

Then restart:

```powershell
.\venv\Scripts\python.exe app.py config_local.yaml
```

### Port 8000 already in use

Find process:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

Stop conflicting process, then run again.
