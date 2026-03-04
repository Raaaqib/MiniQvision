# Models — Download Required

Model files are **not included** in the repo (too large for git).
You must download `yolo11n.onnx` and place it here before running.

## Quick download (PowerShell)
```powershell
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx" `
  -OutFile "$PSScriptRoot\yolo11n.onnx"
```

## Or manually
1. Go to https://github.com/ultralytics/assets/releases
2. Download `yolo11n.onnx` (or any yolo11*.onnx)
3. Place the file in this `models/` folder

## Supported models
| File | Speed | Accuracy |
|------|-------|----------|
| yolo11n.onnx | fastest | lower |
| yolo11s.onnx | fast | good |
| yolo11m.onnx | medium | better |
| yolo11l.onnx | slow | best |

The model name must match `detection.model` in `config/config.yaml`.
