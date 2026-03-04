# Raaqib NVR — Docker Setup Guide

> AI-powered surveillance system. Run it on any PC with Docker — just plug in your cameras and go.

---

## Prerequisites

1. Install [Docker Desktop](https://docs.docker.com/get-docker/) (Windows/Mac/Linux)
2. Install [FFmpeg](https://ffmpeg.org/download.html) on your PC (for webcam streaming)
3. Install [DroidCam](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam) on your phone (optional)

---

## 1. Download the Image

You'll receive a shared folder or zip with these files:

```
Raaqib/
  ├── raaqib-nvr.tar           ← Docker image (~275MB)
  ├── docker-compose.yml
  ├── stream_webcam.bat
  ├── config/
  │   └── config.yaml          ← edit this (cameras + settings)
  └── models/
      └── yolo11n.onnx         ← AI model (included)
```

### Load the image into Docker

Open a terminal in the `Raaqib` folder and run:

```powershell
docker load -i raaqib-nvr.tar
```

You should see: `Loaded image: raaqib-nvr:latest`

---

## 2. Find Your Webcam Name

Open a terminal and run:

```powershell
ffmpeg -list_devices true -f dshow -i dummy
```

Look for a line like:

```
"HP TrueVision HD Camera" (video)
```

Copy your camera name — you'll need it in the next step.

---

## 3. Update `stream_webcam.bat`

Open `stream_webcam.bat` in a text editor and replace the camera name:

```bat
ffmpeg -f dshow -i video="YOUR CAMERA NAME HERE" ^
```

For example:
```bat
ffmpeg -f dshow -i video="HP TrueVision HD Camera" ^
```

---

## 4. Start Everything

### Step 1 — Build & start the containers

```powershell
cd Raaqib
docker compose up -d --build
```

Wait for the build to finish (first time takes a few minutes).

### Step 2 — Stream your webcam

Double-click **`stream_webcam.bat`** or run it in a terminal:

```powershell
.\stream_webcam.bat
```

You should see FFmpeg streaming output. **Keep this window open** — it feeds your webcam to Docker.

### Step 3 — Open the Web UI

Open your browser and go to:

| Service       | URL                          |
|---------------|------------------------------|
| **Web UI**    | http://localhost:8000/ui      |
| **API Docs**  | http://localhost:8000/docs    |
| **Dashboard** | http://localhost:8501         |

---

## 5. Add DroidCam (Phone Camera)

1. Install **DroidCam** on your phone ([Android](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam) / [iOS](https://apps.apple.com/app/droidcam-webcam-obs-camera/id1510258102))
2. Connect your phone to the **same Wi-Fi** as your PC
3. Open the DroidCam app — it will show an IP like `192.168.1.42`
4. Edit `config/config.yaml` and update the DroidCam section:

```yaml
  - id: droidcam
    name: "DroidCam"
    source: "http://192.168.1.42:4747/video"    # ← your phone's IP
    enabled: true                                 # ← change to true
```

5. Restart Raaqib:

```powershell
docker compose restart raaqib
```

---

## 6. Using Both Cameras Together

Your `config/config.yaml` should look like this:

```yaml
cameras:
  - id: laptop_cam
    name: "Laptop Camera"
    source: "rtsp://rtsp:8554/laptop"
    enabled: true
    fps_target: 10
    width: 640
    height: 480

  - id: droidcam
    name: "DroidCam"
    source: "http://192.168.1.42:4747/video"     # ← your phone IP
    enabled: true
    fps_target: 10
    width: 640
    height: 480
```

---

## How It Works

```
┌─────────────────┐    FFmpeg (stream_webcam.bat)    ┌──────────────┐
│  Laptop Webcam   │ ──────────────────────────────→ │  RTSP Relay   │
└─────────────────┘    rtsp://localhost:8554/laptop   │  (MediaMTX)   │
                                                      └──────┬───────┘
                                                             │ rtsp://rtsp:8554/laptop
                                                             ▼
┌─────────────────┐    http://<phone_ip>:4747/video  ┌──────────────┐
│  Phone (DroidCam)│ ──────────────────────────────→ │  Raaqib NVR   │
└─────────────────┘                                   │  (Docker)     │
                                                      └──────┬───────┘
                                                             │
                                                      ┌──────▼───────┐
                                                      │  Web UI       │
                                                      │  :8000/ui     │
                                                      └──────────────┘
```

---

## Common Commands

```powershell
# Start everything
docker compose up -d --build

# View logs
docker compose logs -f raaqib

# Restart after config changes
docker compose restart raaqib

# Stop everything
docker compose down

# Reset all data (recordings, snapshots, database)
docker compose down -v
```

---

## Troubleshooting

### "Stream not connecting"
- Make sure `stream_webcam.bat` is running and showing FFmpeg output
- Check the camera name matches exactly (run `ffmpeg -list_devices true -f dshow -i dummy`)

### "DroidCam not working"
- Phone and PC must be on the **same Wi-Fi network**
- Try opening `http://<phone_ip>:4747/video` in your browser first — you should see the video

### "Build failed"
- Make sure Docker Desktop is running
- Check your internet connection
- Try again: `docker compose up -d --build`

### "No detections"
- The model file `yolo11n.onnx` must be in the `models/` folder
- Check `config/config.yaml` has `model: "yolo11n.onnx"`

---

## For Linux Users

On Linux you can access the webcam directly without the RTSP relay. Change the camera source in `config/config.yaml`:

```yaml
  - id: laptop_cam
    source: 0
```

And uncomment the `devices` section in `docker-compose.yml`:

```yaml
    devices:
      - /dev/video0:/dev/video0
```
