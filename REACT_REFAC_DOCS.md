# MiniQvision React Dashboard Refactor - Documentation

This document explains the comprehensive refactoring of the MiniQvision web dashboard from a Vanilla HTML/JS structure to a modern ReactJS application.

## 1. Architecture Overview

The previous dashboard was a single-file application (`app.js`) that handled DOM manipulation, API polling, and state management in a monolithic way. The new architecture is modular, component-based, and leverages modern web technologies.

### Technology Stack
- **Framework**: ReactJS (v18+) via Vite.
- **Styling**: Tailwind CSS (Utility-first styling).
- **Animations**: Framer Motion (State-driven transitions).
- **Icons**: Lucide React (Vector-based icons).
- **Routing**: Internal state-based view management.

---

## 2. Directory Structure (`/web`)

```text
web/
├── dist/                # Production build output
├── public/              # Static assets (logos, etc.)
├── src/
│   ├── components/
│   │   ├── layout/      # Sidebar, Topbar, Main Shell
│   │   ├── shared/      # Reusable UI elements
│   │   └── views/       # Page-level components
│   ├── context/         # React Context (Global State)
│   ├── utils/           # Helper functions (CN utility, formatting)
│   ├── App.jsx          # Root component & View router
│   ├── main.jsx         # Entry point (Provider wrapper)
│   └── index.css        # Tailwind directives & design tokens
├── tailwind.config.js   # Style configuration
└── vite.config.js       # Build configuration
```

---

## 3. Core Logic & State Management

### SystemContext (`src/context/SystemContext.jsx`)
This is the "brain" of the application. It centralizes all communication with the MiniQvision API.
- **Polling Loop**: Automatically fetches `/status` and `/stats` every X seconds (configurable).
- **State Object**: Stores camera statuses, active detections, and system performance metrics.
- **Config Management**: Persists API URL and refresh rates in `localStorage`.

### Performance Optimization
- **Snapshot Polling**: Instead of expensive MJPEG streams in the grid, the `CameraTile` component polls individual snapshots at 10fps when visible, reducing browser memory overhead.

---

## 4. UI Components

### Layout Shell
- **Topbar**: Displays the system clock, storage usage bar, and a real-time "API Online" status pill.
- **Sidebar**: Manage navigation between views and provides a quick-glance status list of all connected cameras.

### Views
1. **Live Monitor**: A dynamic camera grid. Users can toggle between 1, 2, or 3 columns. Each tile scales responsively and highlights cameras with active motion or recording.
2. **Events**: A modern table view for historical data. It includes filtering by camera or label and confidence progress bars.
3. **Recordings**: A thumbnail-based grid of stored `.mp4` clips. Supports direct playback and download.
4. **Snapshots**: An image gallery of captured freeze-frames with an integrated full-screen lightbox.
5. **Settings**: A clean interface to reconfigure the API connection and view system diagnostics.

---

## 5. Animations & Styling

### Redesign philosophy
We shifted from a dense, industrial UI to a "Dark Minimalist" aesthetic:
- **Design Tokens**: Defined in `index.css` (slate/zinc colors, blue accents).
- **Glassmorphism**: Subtle use of `backdrop-blur` and border-transparency for depth.
- **Transitions**: 
  - Page transitions use `AnimatePresence`.
  - Camera tiles use `layout` animations to smoothly reorganize when the grid size changes.

---

## 6. Integration with Backend

The FastAPI backend in `api/app.py` was updated to recognize the new React structure. 

### Static File Routes
- The backend now checks for the existence of `web/dist`.
- It mounts the `dist` folder to the `/ui` route.
- **URL**: `http://localhost:8000/ui`

### API Compatibility
The React app remains 100% compatible with the existing REST endpoints:
- `GET /api/status`
- `GET /api/stats`
- `GET /api/events`
- `GET /api/recordings`
- `GET /api/snapshots`

---

## 7. Development & Deployment

### To execute a new build:
```bash
cd web
npm install
npm run build
```

### To run in development mode (with Hot Module Replacement):
```bash
cd web
npm run dev
```

---

## 8. Running the Complete System

To run the entire MiniQvision system with the new React dashboard, follow these steps:

### 1. Prerequisite: Frontend Build
Since the FastAPI backend serves the React app as static files, you must build the frontend at least once:
```bash
cd web
npm install
npm run build
```
This generates the `web/dist` folder which the API looks for.

### 2. Prerequisite: Python Dependencies
Ensure all backend dependencies are installed:
```bash
# In the project root
pip install -r requirements.txt
```

### 3. Launch the Backend
The main entry point starts the API, camera captures, and AI processing:
```bash
python app.py
```

### 4. Access the UI
Once `app.py` is running, open your browser to:
- **New Dashboard**: [http://localhost:8000/ui](http://localhost:8000/ui)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

> [!TIP]
> If you are actively developing the frontend, you can run `npm run dev` in the `web` folder and access the dashboard at `http://localhost:5173`. By default, it is configured to talk to the API at `http://localhost:8000/api`.
