# ⚡ Quick Run & Kill Commands

## Run Raaqib NVR (with both cameras)

```powershell
.\.venv\Scripts\Activate.ps1 ; cd Raaqib-Docker ; python app.py config_local.yaml
```

**What happens:**
- ✅ Activates virtual environment
- ✅ Enters Raaqib-Docker directory
- ✅ Starts app with config_local.yaml (HP TrueVision + DroidCam enabled)
- ✅ Spawns 16 Python child processes
- ✅ API available at `http://localhost:8000`
- ✅ Swagger UI at `http://localhost:8000/docs`

---

## Kill All Processes

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue ; Start-Sleep -Seconds 3 ; Write-Host "✓ All processes killed"
```

**What happens:**
- ✅ Force kills all Python processes
- ✅ Waits 3 seconds for cleanup
- ✅ Prints confirmation message

---

## Run & Kill Together (Full Cycle)

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue ; Start-Sleep -Seconds 3 ; .\.venv\Scripts\Activate.ps1 ; cd Raaqib-Docker ; python app.py config_local.yaml
```

**What this does:**
1. **Kill** - Stops all existing processes
2. **Wait** - 3 second pause
3. **Run** - Activates venv and starts fresh Raaqib with both cameras

---

## Verify System Running

```powershell
Get-Process python | Measure-Object | Select-Object Count
```

**Expected output:** `Count: 16` (main + 15 child processes)

---

## Check API Status

```powershell
Start-Sleep -Seconds 2 ; (Invoke-WebRequest http://localhost:8000/api/status).Content | ConvertFrom-Json | Select-Object status, uptime_seconds
```

**Expected output:**
```
status uptime_seconds
------ ---------------
running           5.2
```

---

## View Logs

```powershell
Get-Content "Raaqib-Docker\logs\raaqib.log" -Tail 50
```

---

## Camera Configuration

**File:** `Raaqib-Docker\config_local.yaml`

Current setup:
- **cam1**: HP TrueVision HD Camera (index 1) - **ENABLED**
- **cam2**: DroidCam (index 0) - **ENABLED**

To disable a camera, change `enabled: true` to `enabled: false` in config_local.yaml, then restart.

---

## Quick Reference

| Task | Command |
|------|---------|
| Run | `.\.venv\Scripts\Activate.ps1 ; cd Raaqib-Docker ; python app.py config_local.yaml` |
| Kill | `Stop-Process -Name python -Force -ErrorAction SilentlyContinue` |
| Run & Kill | `Stop-Process -Name python -Force -ErrorAction SilentlyContinue ; Start-Sleep -Seconds 3 ; .\.venv\Scripts\Activate.ps1 ; cd Raaqib-Docker ; python app.py config_local.yaml` |
| Check Status | `(Invoke-WebRequest http://localhost:8000/api/status).Content \| ConvertFrom-Json` |
| View Docs | Open `http://localhost:8000/docs` in browser |

---
