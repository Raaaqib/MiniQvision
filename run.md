# Running Raaqib NVR

---

## Source Code

### Start

```bash
# Activate virtual environment
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Run
python app.py config_local.yaml
```

Open:
- Web UI:   http://localhost:8000/ui
- API docs: http://localhost:8000/docs
- Status:   http://localhost:8000/api/status

### Kill

Press `Ctrl+C` in the terminal.

Or force kill:

```bash
# Windows
taskkill /F /IM python.exe

# macOS / Linux
pkill -f "python app.py"
```

---

## Docker

Before starting:
- Edit `config.docker.yaml` for your environment.
- On Windows/macOS, comment out the `devices:` block in `docker-compose.yml`.

### Build image (first time only)

```bash
docker compose build
```

### Start

```bash
docker compose up -d
```

If `config.docker.yaml` is missing, the container exits immediately with a clear startup error.

Open:
- Web UI:   http://localhost:8000/ui
- API docs: http://localhost:8000/docs

### Shut Down

```bash
docker compose down
```
