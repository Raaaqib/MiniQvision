"""
Raaqib NVR — Streamlit Dashboard
Run: streamlit run web/dashboard.py -- --config ../config.yaml
"""

from __future__ import annotations
import sys
import time
import requests
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Raaqib NVR",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Raaqib NVR — AI-powered surveillance system"}
)

API_BASE = "http://localhost:8000/api"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
    --bg:       #060810;
    --surface:  #0c1020;
    --border:   #1a2540;
    --accent:   #3b82f6;
    --accent2:  #22d3ee;
    --warn:     #f59e0b;
    --danger:   #ef4444;
    --success:  #22c55e;
    --text:     #cbd5e1;
    --muted:    #475569;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
    font-family: 'Space Grotesk', sans-serif;
}
[data-testid="stSidebar"] {
    background: var(--surface);
    border-right: 1px solid var(--border);
}
h1,h2,h3,h4 { font-family: 'Space Grotesk', sans-serif; font-weight: 700; }
h1 { font-size: 1.6rem; color: var(--accent2); letter-spacing: -0.5px; }

.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 6px 0;
}
.cam-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--accent2);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 4px;
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 1px;
}
.badge-online  { background: #052e16; color: var(--success); border: 1px solid #166534; }
.badge-offline { background: #1c0a0a; color: var(--danger);  border: 1px solid #7f1d1d; }
.badge-motion  { background: #1c1200; color: var(--warn);    border: 1px solid #92400e; }
.badge-rec     { background: #1c0a0a; color: var(--danger);  border: 1px solid #7f1d1d; }

.stat-value { font-size: 2rem; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
.stat-label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; }

.event-row {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 12px; margin: 3px 0;
    background: #0c1020;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 0 6px 6px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}
.event-cam  { color: var(--muted); }
.event-label { color: var(--accent2); font-weight: 700; }
.event-conf  { color: var(--muted); }
.event-time  { color: var(--muted); margin-left: auto; }

.no-signal {
    background: #0c1020;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 60px 20px;
    text-align: center;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}

div[data-testid="stImage"] img {
    border-radius: 0 0 8px 8px;
    border: 1px solid var(--border);
    border-top: none;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--muted);
    border-radius: 6px 6px 0 0;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important;
    color: var(--accent2) !important;
    border-bottom: 2px solid var(--accent2) !important;
}
</style>
""", unsafe_allow_html=True)


# ── API Helpers ───────────────────────────────────────────────────────────────

def api_get(endpoint: str, timeout: float = 2.0):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def fmt_datetime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ── Main App ──────────────────────────────────────────────────────────────────

def main():
    status = api_get("/status")
    stats  = api_get("/stats")
    events = api_get("/events?limit=30") or []
    active = api_get("/events/active") or []

    api_ok = status is not None
    cameras = status.get("cameras", {}) if status else {}

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        # System header
        st.markdown("""
        <div style="padding:16px 0 8px 0">
            <div style="font-size:1.4rem;font-weight:700;color:#22d3ee;letter-spacing:-0.5px">
                RAAQIB NVR
            </div>
            <div style="font-size:0.7rem;color:#475569;letter-spacing:2px;text-transform:uppercase">
                AI Surveillance System
            </div>
        </div>
        """, unsafe_allow_html=True)

        # API status
        dot = "🟢" if api_ok else "🔴"
        st.markdown(f"{dot} API {'Connected' if api_ok else 'Offline'}")
        st.markdown("---")

        # Camera statuses
        st.markdown("#### 📹 Cameras")
        if cameras:
            for cam_id, cam in cameras.items():
                online = cam.get("online", False)
                motion = cam.get("motion", False)
                rec    = cam.get("recording", False)
                fps    = cam.get("fps", 0)

                badges = []
                if online:
                    badges.append('<span class="badge badge-online">LIVE</span>')
                else:
                    badges.append('<span class="badge badge-offline">OFFLINE</span>')
                if motion:
                    badges.append('<span class="badge badge-motion">MOTION</span>')
                if rec:
                    badges.append('<span class="badge badge-rec">● REC</span>')

                st.markdown(f"""
                <div class="card" style="padding:10px 14px;margin:4px 0">
                    <div class="cam-name">{cam_id}</div>
                    <div style="margin:4px 0">{"".join(badges)}</div>
                    <div style="font-size:0.72rem;color:#475569;font-family:'JetBrains Mono',monospace">
                        FPS: {fps:.1f} | Tracks: {cam.get('active_tracks',0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No cameras found. Is the API running?")

        st.markdown("---")

        # Stats
        st.markdown("#### 📊 Stats")
        if stats:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style="text-align:center">
                    <div class="stat-value">{stats.get('total_events', 0)}</div>
                    <div class="stat-label">Events</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style="text-align:center">
                    <div class="stat-value">{stats.get('total_clips', 0)}</div>
                    <div class="stat-label">Clips</div>
                </div>""", unsafe_allow_html=True)

            # Top labels
            by_label = stats.get("by_label", [])
            if by_label:
                st.markdown("<div style='margin-top:8px;font-size:0.72rem;color:#475569;text-transform:uppercase;letter-spacing:1px'>Top Objects</div>", unsafe_allow_html=True)
                for item in by_label[:5]:
                    pct = item['count'] / max(stats['total_events'], 1) * 100
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;font-size:0.78rem;
                         font-family:'JetBrains Mono',monospace;padding:2px 0">
                        <span style="color:#94a3b8">{item['label']}</span>
                        <span style="color:#3b82f6">{item['count']}</span>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Active events
        if active:
            st.markdown(f"#### ⚡ Active Events ({len(active)})")
            for ev in active:
                st.markdown(f"""
                <div style="background:#0c1020;border-left:3px solid #ef4444;
                     padding:8px 10px;margin:3px 0;border-radius:0 4px 4px 0;
                     font-family:'JetBrains Mono',monospace;font-size:0.75rem">
                    <span style="color:#22d3ee">{ev['label'].upper()}</span>
                    <span style="color:#475569"> on {ev['camera_id']}</span>
                    <div style="color:#475569">{ev['duration']:.1f}s</div>
                </div>""", unsafe_allow_html=True)

        # Refresh
        st.markdown("---")
        refresh = st.slider("Refresh (s)", 1, 10, 2)

    # ── Main Tabs ─────────────────────────────────────────────────────────────
    st.markdown("# 🔍 RAAQIB NVR")

    tab_live, tab_events, tab_recordings, tab_snapshots = st.tabs([
        "📺  Live View", "⚡  Events", "🎬  Recordings", "📸  Snapshots"
    ])

    # ── Live View ─────────────────────────────────────────────────────────────
    with tab_live:
        if not cameras:
            st.markdown("""
            <div class="no-signal">
                ⚠ No cameras connected<br>
                <small>Check API is running: <code>python app.py</code></small>
            </div>""", unsafe_allow_html=True)
        else:
            cols = st.columns(min(len(cameras), 2))
            for i, (cam_id, cam) in enumerate(cameras.items()):
                col = cols[i % 2]
                with col:
                    online = cam.get("online", False)
                    motion = cam.get("motion", False)
                    rec    = cam.get("recording", False)

                    status_text = "● REC" if rec else ("◈ MOTION" if motion else "○ LIVE")
                    status_color = "#ef4444" if rec else ("#f59e0b" if motion else "#22c55e")

                    st.markdown(f"""
                    <div style="background:#0c1020;border:1px solid #1a2540;
                         border-radius:8px 8px 0 0;padding:8px 14px;
                         display:flex;justify-content:space-between;align-items:center">
                        <span class="cam-name">{cam_id}</span>
                        <span style="font-family:'JetBrains Mono',monospace;
                               font-size:0.72rem;color:{status_color}">{status_text}</span>
                    </div>""", unsafe_allow_html=True)

                    if not online:
                        st.markdown(f"""
                        <div class="no-signal">
                            ⚫ NO SIGNAL<br>
                            <small>{cam.get('error', 'Connecting...')}</small>
                        </div>""", unsafe_allow_html=True)
                    else:
                        # Embed MJPEG stream directly — live feed from capture process
                        stream_url = f"http://localhost:8000/api/cameras/{cam_id}/stream"
                        st.markdown(
                            f'<img src="{stream_url}" '
                            f'style="width:100%;border-radius:0 0 4px 4px" '
                            f'alt="{cam_id} live feed">',
                            unsafe_allow_html=True
                        )

                    st.markdown(f"""
                    <div style="background:#0c1020;border:1px solid #1a2540;
                         border-top:none;border-radius:0 0 8px 8px;
                         padding:6px 14px;font-size:0.7rem;
                         font-family:'JetBrains Mono',monospace;color:#475569">
                        FPS {cam.get('fps', 0):.1f} &nbsp;|&nbsp;
                        Tracks {cam.get('active_tracks', 0)} &nbsp;|&nbsp;
                        Clips {cam.get('clips_saved', 0)}
                    </div>""", unsafe_allow_html=True)

    # ── Events ────────────────────────────────────────────────────────────────
    with tab_events:
        st.markdown("### Detection Event Log")

        # Filter row
        fcol1, fcol2, _ = st.columns([2, 2, 6])
        with fcol1:
            filter_cam = st.text_input("Filter by camera", placeholder="cam1")
        with fcol2:
            filter_label = st.text_input("Filter by label", placeholder="person")

        url = f"/events?limit=50"
        if filter_cam:
            url += f"&camera_id={filter_cam}"
        if filter_label:
            url += f"&label={filter_label}"

        filtered_events = api_get(url) or []

        if not filtered_events:
            st.info("No events found. Detections will appear here.")
        else:
            for ev in filtered_events:
                ts = fmt_datetime(ev["start_time"])
                dur = f"{ev.get('duration', 0):.1f}s"
                conf = f"{ev.get('confidence', 0):.0%}"
                st.markdown(f"""
                <div class="event-row">
                    <span style="color:#22d3ee;font-weight:700">{ev['label'].upper()}</span>
                    <span class="event-cam">{ev['camera_id']}</span>
                    <span class="badge badge-online" style="font-size:0.65rem">{conf}</span>
                    <span style="color:#475569">{dur}</span>
                    <span class="event-time">{ts}</span>
                </div>""", unsafe_allow_html=True)

    # ── Recordings ────────────────────────────────────────────────────────────
    with tab_recordings:
        st.markdown("### Saved Recordings")
        clips = api_get("/recordings") or []

        if not clips:
            st.info("No recordings yet. Clips are saved automatically on detection.")
        else:
            st.caption(f"{len(clips)} clip(s) found")
            for clip in clips[:20]:
                ts = fmt_datetime(clip["modified"])
                with st.expander(f"🎬 {clip['filename']}  ·  {clip['size_mb']} MB  ·  {ts}"):
                    clip_url = f"{API_BASE}/recordings/{clip['filename']}"
                    st.video(clip_url)
                    st.markdown(f"[⬇ Download]({clip_url})")

    # ── Snapshots ─────────────────────────────────────────────────────────────
    with tab_snapshots:
        st.markdown("### Detection Snapshots")
        snap_cam = st.selectbox("Camera", ["All"] + list(cameras.keys()))
        cam_filter = None if snap_cam == "All" else snap_cam
        snaps = api_get(f"/snapshots{'?camera_id='+cam_filter if cam_filter else ''}") or []

        if not snaps:
            st.info("No snapshots yet.")
        else:
            st.caption(f"{len(snaps)} snapshot(s)")
            grid = st.columns(3)
            for i, snap in enumerate(snaps[:30]):
                with grid[i % 3]:
                    img_r = requests.get(f"{API_BASE}/snapshots/{snap['filename']}", timeout=2)
                    if img_r.status_code == 200:
                        st.image(img_r.content, caption=snap["filename"][:30],
                                 use_container_width=True)

    # Auto-refresh
    time.sleep(refresh)
    st.rerun()


if __name__ == "__main__":
    main()
