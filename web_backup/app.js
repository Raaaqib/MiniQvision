/* ═══════════════════════════════════════════════════════════
   RAAQIB NVR — app.js
   Talks to FastAPI backend, drives the entire UI.
   ═══════════════════════════════════════════════════════════ */

'use strict';

// ── Config ────────────────────────────────────────────────────────────────────
const Config = {
  apiBase: localStorage.getItem('raaqib_api') || 'http://localhost:8000/api',
  refreshMs: parseInt(localStorage.getItem('raaqib_refresh') || '3000'),
  snapshotBase: () => `${Config.apiBase}/snapshots`,
  recordingBase: () => `${Config.apiBase}/recordings`,
};

// ── State ─────────────────────────────────────────────────────────────────────
const State = {
  cameras: {},          // camera_id → camera state dict
  activeEvents: [],
  recentEvents: [],
  clips: [],
  snapshots: [],
  stats: {},
  apiOnline: false,
  activeView: 'live',
  gridCols: 2,
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

const Dom = {
  clockTime:   $('clock-time'),
  clockDate:   $('clock-date'),
  pillApi:     $('pill-api'),
  pillMqtt:    $('pill-mqtt'),
  pillRec:     $('pill-rec'),
  cameraList:  $('camera-list'),
  cameraGrid:  $('camera-grid'),
  statEvents:  $('stat-events'),
  statClips:   $('stat-clips'),
  statSnaps:   $('stat-snaps'),
  statTracks:  $('stat-tracks'),
  activeList:  $('active-detections'),
  eventsTbody: $('events-tbody'),
  clipsGrid:   $('clips-grid'),
  snapsGrid:   $('snapshots-grid'),
  lastUpdate:  $('last-update'),
  lightbox:    $('lightbox'),
  lbImg:       $('lightbox-img'),
  lbCaption:   $('lightbox-caption'),
  lbClose:     $('lightbox-close'),
  toastCont:   $('toast-container'),
  filterCam:   $('filter-cam'),
  filterLabel: $('filter-label'),
  recCamFlt:   $('rec-cam-filter'),
  snapCamFlt:  $('snap-cam-filter'),
};

// ── Utilities ─────────────────────────────────────────────────────────────────

function fmtTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('en-GB', { hour12: false });
}

function fmtDatetime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleString('en-GB', { hour12: false });
}

function fmtDuration(s) {
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
}

function fmtBytes(mb) {
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

function escHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── Clock ─────────────────────────────────────────────────────────────────────

function tickClock() {
  const now = new Date();
  Dom.clockTime.textContent = now.toLocaleTimeString('en-GB', { hour12: false });
  Dom.clockDate.textContent = now.toLocaleDateString('en-GB', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
  }).toUpperCase();
}
setInterval(tickClock, 1000);
tickClock();

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, type = 'success', duration = 3000) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  Dom.toastCont.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ── API ───────────────────────────────────────────────────────────────────────

async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${Config.apiBase}${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return null;
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────

function switchView(view) {
  State.activeView = view;

  $$('.nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.view === view));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === `view-${view}`));

  // Trigger data load for the switched view
  if (view === 'events') loadEvents();
  if (view === 'recordings') loadRecordings();
  if (view === 'snapshots') loadSnapshots();
  if (view === 'settings') loadSettings();
}

$$('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

// ── Grid layout ───────────────────────────────────────────────────────────────

function setGridCols(n) {
  State.gridCols = n;
  Dom.cameraGrid.className = `camera-grid${n === 1 ? ' cols-1' : n === 3 ? ' cols-3' : ''}`;
  ['btn-grid-1', 'btn-grid-2', 'btn-grid-3'].forEach((id, i) => {
    $(id).classList.toggle('active', i + 1 === n);
  });
}

$('btn-grid-1').addEventListener('click', () => setGridCols(1));
$('btn-grid-2').addEventListener('click', () => setGridCols(2));
$('btn-grid-3').addEventListener('click', () => setGridCols(3));
$('btn-fullscreen').addEventListener('click', () => {
  document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
});

// ── Lightbox ──────────────────────────────────────────────────────────────────

function openLightbox(src, caption = '') {
  Dom.lbImg.src = src;
  Dom.lbCaption.textContent = caption;
  Dom.lightbox.classList.add('open');
  Dom.lightbox.setAttribute('aria-hidden', 'false');
}

function closeLightbox() {
  Dom.lightbox.classList.remove('open');
  Dom.lightbox.setAttribute('aria-hidden', 'true');
  Dom.lbImg.src = '';
}

Dom.lbClose.addEventListener('click', closeLightbox);
Dom.lightbox.addEventListener('click', e => { if (e.target === Dom.lightbox) closeLightbox(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

// ── Sidebar: Camera List ──────────────────────────────────────────────────────

function renderCameraList(cameras) {
  if (!Object.keys(cameras).length) {
    Dom.cameraList.innerHTML = '<div class="empty-state">NO CAMERAS</div>';
    return;
  }

  Dom.cameraList.innerHTML = Object.entries(cameras).map(([id, cam]) => {
    const online    = cam.online;
    const motion    = cam.motion;
    const recording = cam.recording;

    const stateClass = recording ? 'recording' : motion ? 'motion' : online ? 'online' : 'offline';

    const badges = [];
    if (!online)    badges.push(`<span class="badge badge-offline">OFFLINE</span>`);
    else            badges.push(`<span class="badge badge-live">LIVE</span>`);
    if (motion)     badges.push(`<span class="badge badge-motion">MOTION</span>`);
    if (recording)  badges.push(`<span class="badge badge-rec">● REC</span>`);

    return `
      <div class="cam-item ${stateClass}" data-cam="${escHtml(id)}">
        <div class="cam-item-id">${escHtml(id)}</div>
        <div class="cam-item-name">${escHtml(id.replace(/_/g, ' ').toUpperCase())}</div>
        <div class="cam-item-meta">
          <span>FPS ${(cam.fps || 0).toFixed(1)}</span>
          <span>TRK ${cam.active_tracks || 0}</span>
        </div>
        <div class="cam-item-badges">${badges.join('')}</div>
      </div>`;
  }).join('');
}

// ── Stats ─────────────────────────────────────────────────────────────────────

function renderStats(stats, cameras) {
  Dom.statEvents.textContent = stats?.total_events ?? '—';
  Dom.statClips.textContent  = stats?.total_clips  ?? '—';
  Dom.statSnaps.textContent  = stats?.snapshots_count ?? '—';

  const totalTracks = Object.values(cameras).reduce((s, c) => s + (c.active_tracks || 0), 0);
  Dom.statTracks.textContent = totalTracks;
}

// ── Threat Meter ──────────────────────────────────────────────────────────────

function updateThreatMeter(cameras) {
  const active = Object.values(cameras).filter(c => c.motion || c.recording).length;
  const total  = Object.keys(cameras).length || 1;
  const level  = Math.ceil((active / total) * 5);

  const colorMap = {1:'active-1', 2:'active-2', 3:'active-3', 4:'active-4', 5:'active-5'};

  [1,2,3,4,5].forEach(i => {
    const el = $(`tb${i}`);
    el.className = 'tbar';
    if (i <= level) el.classList.add(colorMap[level] || 'active-1');
  });
}

// ── Active Detections (Sidebar) ───────────────────────────────────────────────

function renderActiveDetections(events) {
  if (!events?.length) {
    Dom.activeList.innerHTML = '<div class="empty-state">NO ACTIVE DETECTIONS</div>';
    return;
  }

  Dom.activeList.innerHTML = events.map(ev => `
    <div class="active-item">
      <div class="active-label">${escHtml(ev.label?.toUpperCase() || '?')}</div>
      <div style="display:flex;justify-content:space-between">
        <span class="active-cam">${escHtml(ev.camera_id || '')}</span>
        <span class="active-dur">${fmtDuration(ev.duration || 0)}</span>
      </div>
    </div>`).join('');
}

// ── API Status Pills ──────────────────────────────────────────────────────────

function updatePills(apiOk, cameras) {
  // Update API status
  if (Dom.pillApi) {
    Dom.pillApi.className = `api-status ${apiOk ? 'pill--active' : 'pill--error'}`;
    const dot = Dom.pillApi.querySelector('.api-dot');
    if (dot) dot.className = `api-dot${apiOk ? '' : ''}`;
  }

  // Update recording status (hidden pill, kept for compat)
  if (Dom.pillRec) {
    const anyRec = Object.values(cameras).some(c => c.recording);
    Dom.pillRec.className = `pill ${anyRec ? 'pill--error' : ''}`;
    const dot = Dom.pillRec.querySelector('.pill-dot');
    if (dot) dot.className = `pill-dot${anyRec ? ' blink' : ''}`;
  }
}

// ── Per-camera snapshot pollers ─────────────────────────────────────────────
const _camPollers = {}; // camId → intervalId

function startPoller(camId, imgEl) {
  if (_camPollers[camId]) return; // already running
  _camPollers[camId] = setInterval(() => {
    const url = `${Config.apiBase}/cameras/${encodeURIComponent(camId)}/snapshot.jpg?t=${Date.now()}`;
    const tmp = new Image();
    tmp.onload = () => { imgEl.src = tmp.src; };
    tmp.src = url;
  }, 100);
}

function stopPoller(camId) {
  if (_camPollers[camId]) {
    clearInterval(_camPollers[camId]);
    delete _camPollers[camId];
  }
}

// ── Camera Grid (Live View) ───────────────────────────────────────────────────

function getOrCreateTile(camId) {
  let tile = Dom.cameraGrid.querySelector(`[data-cam-tile="${CSS.escape(camId)}"]`);
  if (!tile) {
    tile = document.createElement('div');
    tile.className = 'cam-tile';
    tile.dataset.camTile = camId;
    tile.innerHTML = `
      <div class="cam-tile-hdr">
        <span class="cam-tile-id">${escHtml(camId)}</span>
        <span class="cam-tile-status">
          <span class="cam-tile-dot offline" data-dot></span>
          <span data-status-text style="font-family:var(--font-mono);font-size:0.6rem;color:var(--text-dim)">CONNECTING</span>
        </span>
      </div>
      <div class="cam-tile-feed">
        <div class="cam-tile-nosignal" data-nosignal>
          <span class="nosignal-icon">⊘</span>
          <span>NO SIGNAL</span>
          <span style="font-size:0.55rem;opacity:0.5" data-err-msg></span>
        </div>
        <img class="cam-tile-img" data-img style="display:none" alt="Camera feed" />
        <div class="cam-tile-hud">
          <div class="hud-corner hud-tl"></div>
          <div class="hud-corner hud-tr"></div>
          <div class="hud-corner hud-bl"></div>
          <div class="hud-corner hud-br"></div>
          <div class="hud-ts" data-hud-ts></div>
          <div class="hud-fps" data-hud-fps></div>
        </div>
      </div>
      <div class="cam-tile-ftr">
        <span data-tracks>TRK 0</span>
        <span data-clips>CLIPS 0</span>
      </div>`;
    Dom.cameraGrid.appendChild(tile);
  }
  return tile;
}

function updateCameraTile(camId, cam) {
  const tile = getOrCreateTile(camId);
  const online    = cam.online;
  const motion    = cam.motion;
  const recording = cam.recording;

  // Tile state classes
  tile.classList.toggle('motion',    !!motion);
  tile.classList.toggle('recording', !!recording);

  // Status dot + text
  const dot    = tile.querySelector('[data-dot]');
  const stTxt  = tile.querySelector('[data-status-text]');
  dot.className = 'cam-tile-dot';
  if (recording) { dot.classList.add('rec'); stTxt.textContent = '● REC'; stTxt.style.color = 'var(--red)'; }
  else if (motion) { dot.classList.add('motion'); stTxt.textContent = '◈ MOTION'; stTxt.style.color = 'var(--amber)'; }
  else if (online) { stTxt.textContent = '○ LIVE'; stTxt.style.color = 'var(--green)'; }
  else { dot.classList.add('offline'); stTxt.textContent = 'OFFLINE'; stTxt.style.color = 'var(--muted)'; }

  // HUD
  const now = new Date();
  tile.querySelector('[data-hud-ts]').textContent = now.toLocaleTimeString('en-GB', { hour12: false });
  tile.querySelector('[data-hud-fps]').textContent = `${(cam.fps || 0).toFixed(1)} FPS`;
  tile.querySelector('[data-tracks]').textContent = `TRK ${cam.active_tracks || 0}`;
  tile.querySelector('[data-clips]').textContent = `CLIPS ${cam.clips_saved || 0}`;

  // Show snapshot as feed proxy
  const imgEl   = tile.querySelector('[data-img]');
  const noSig   = tile.querySelector('[data-nosignal]');
  const errMsg  = tile.querySelector('[data-err-msg]');

  if (online) {
    imgEl.style.display = 'block';
    noSig.style.display = 'none';
    startPoller(camId, imgEl);
  } else {
    stopPoller(camId);
    noSig.style.display = 'flex';
    imgEl.style.display = 'none';
    errMsg.textContent = cam.error || 'CONNECTION FAILED';
  }
}

function renderCameraGrid(cameras) {
  if (!Object.keys(cameras).length) {
    Dom.cameraGrid.innerHTML = `
      <div style="grid-column:1/-1;padding:60px;text-align:center;
           font-family:var(--font-mono);font-size:0.8rem;color:var(--muted);letter-spacing:2px">
        ⚠ NO CAMERAS — Check API connection in Settings
      </div>`;
    return;
  }

  Object.entries(cameras).forEach(([id, cam]) => updateCameraTile(id, cam));

  // Remove stale tiles
  Dom.cameraGrid.querySelectorAll('[data-cam-tile]').forEach(tile => {
    if (!cameras[tile.dataset.camTile]) tile.remove();
  });
}

// ── Events Table ──────────────────────────────────────────────────────────────

async function loadEvents() {
  const camF   = Dom.filterCam?.value   || '';
  const labelF = Dom.filterLabel?.value || '';
  let url = '/events?limit=100';
  if (camF)   url += `&camera_id=${encodeURIComponent(camF)}`;
  if (labelF) url += `&label=${encodeURIComponent(labelF)}`;

  const events = await apiFetch(url);

  if (!events || !events.length) {
    Dom.eventsTbody.innerHTML = `<tr><td colspan="6" class="table-empty">NO EVENTS FOUND</td></tr>`;
    return;
  }

  Dom.eventsTbody.innerHTML = events.map(ev => {
    const conf = ev.confidence || ev.peak_confidence || 0;
    const confPct = (conf * 100).toFixed(0);
    const active = !ev.end_time || ev.active;

    return `<tr>
      <td>${fmtDatetime(ev.start_time)}</td>
      <td class="td-cam">${escHtml(ev.camera_id || '')}</td>
      <td class="td-label">${escHtml((ev.label || '').toUpperCase())}</td>
      <td>
        <div class="conf-bar-wrap">
          <div class="conf-bar"><div class="conf-bar-fill" style="width:${confPct}%"></div></div>
          <span class="td-conf">${confPct}%</span>
        </div>
      </td>
      <td>${fmtDuration(ev.duration || 0)}</td>
      <td class="${active ? 'td-status-active' : 'td-status-ended'}">${active ? '● ACTIVE' : '✓ ENDED'}</td>
    </tr>`;
  }).join('');
}

Dom.filterCam?.addEventListener('input', debounce(loadEvents, 400));
Dom.filterLabel?.addEventListener('input', debounce(loadEvents, 400));
$('btn-refresh-events')?.addEventListener('click', loadEvents);

// ── Recordings ────────────────────────────────────────────────────────────────

async function loadRecordings() {
  const camF = Dom.recCamFlt?.value || '';
  let url = '/recordings';
  if (camF) url += `?camera_id=${encodeURIComponent(camF)}`;

  const clips = await apiFetch(url);
  State.clips = clips || [];

  if (!State.clips.length) {
    Dom.clipsGrid.innerHTML = `<div style="grid-column:1/-1;padding:40px;text-align:center;
      font-family:var(--font-mono);font-size:0.8rem;color:var(--muted);letter-spacing:2px">
      NO RECORDINGS YET
    </div>`;
    return;
  }

  Dom.clipsGrid.innerHTML = State.clips.map(clip => {
    const dlUrl = `${Config.apiBase}/recordings/${encodeURIComponent(clip.filename)}`;
    return `
    <div class="clip-card">
      <div class="clip-thumb">⏺</div>
      <div class="clip-info">
        <div class="clip-name" title="${escHtml(clip.filename)}">${escHtml(clip.filename)}</div>
        <div class="clip-meta">
          <span>${clip.size_mb} MB</span>
          <span>${fmtDatetime(clip.modified)}</span>
        </div>
        <div class="clip-actions">
          <a class="clip-btn" href="${dlUrl}" target="_blank">▶ PLAY</a>
          <a class="clip-btn" href="${dlUrl}" download="${escHtml(clip.filename)}">⬇ SAVE</a>
        </div>
      </div>
    </div>`;
  }).join('');
}

Dom.recCamFlt?.addEventListener('change', loadRecordings);

// ── Snapshots ─────────────────────────────────────────────────────────────────

async function loadSnapshots() {
  const camF = Dom.snapCamFlt?.value || '';
  let url = '/snapshots?limit=60';
  if (camF) url += `&camera_id=${encodeURIComponent(camF)}`;

  const snaps = await apiFetch(url);
  State.snapshots = snaps || [];

  if (!State.snapshots.length) {
    Dom.snapsGrid.innerHTML = `<div style="grid-column:1/-1;padding:40px;text-align:center;
      font-family:var(--font-mono);font-size:0.8rem;color:var(--muted);letter-spacing:2px">
      NO SNAPSHOTS YET
    </div>`;
    return;
  }

  Dom.snapsGrid.innerHTML = State.snapshots.map(snap => {
    const src = `${Config.apiBase}/snapshots/${encodeURIComponent(snap.filename)}`;
    return `
    <div class="snap-card" data-src="${src}" data-cap="${escHtml(snap.filename)}">
      <img class="snap-img" src="${src}" alt="${escHtml(snap.filename)}" loading="lazy" />
      <div class="snap-caption">${escHtml(snap.filename)}</div>
    </div>`;
  }).join('');

  Dom.snapsGrid.querySelectorAll('.snap-card').forEach(card => {
    card.addEventListener('click', () => openLightbox(card.dataset.src, card.dataset.cap));
  });
}

Dom.snapCamFlt?.addEventListener('change', loadSnapshots);

// ── Settings ──────────────────────────────────────────────────────────────────

function loadSettings() {
  $('cfg-api-url').value = Config.apiBase;
  $('cfg-refresh').value = Config.refreshMs / 1000;

  apiFetch('/status').then(data => {
    if (!data) return;
    $('cfg-model')?.textContent && ($('cfg-model').textContent = '—');
  });
}

$('btn-save-settings')?.addEventListener('click', () => {
  Config.apiBase  = $('cfg-api-url').value.replace(/\/$/, '');
  Config.refreshMs = parseInt($('cfg-refresh').value) * 1000 || 3000;
  localStorage.setItem('raaqib_api', Config.apiBase);
  localStorage.setItem('raaqib_refresh', Config.refreshMs);
  toast('Settings saved. Reconnecting...', 'success');
  poll();
});

// ── Camera filter selects ─────────────────────────────────────────────────────

function updateCamFilters(cameras) {
  const ids = Object.keys(cameras);
  [Dom.recCamFlt, Dom.snapCamFlt].forEach(sel => {
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">All Cameras</option>' +
      ids.map(id => `<option value="${escHtml(id)}"${id===current?' selected':''}>${escHtml(id)}</option>`).join('');
  });
}

// ── Main Poll Loop ────────────────────────────────────────────────────────────

let _pollTimer = null;

async function poll() {
  clearTimeout(_pollTimer);

  try {
    const [status, stats] = await Promise.all([
      apiFetch('/status'),
      apiFetch('/stats'),
    ]);

    const apiOk   = !!status;
    const cameras = status?.cameras || {};
    const active  = status?.active_events || [];

    State.cameras      = cameras;
    State.activeEvents = active;
    State.apiOnline    = apiOk;
    State.stats        = stats || {};

    // Update UI
    updatePills(apiOk, cameras);
    updateThreatMeter(cameras);
    renderCameraList(cameras);
    renderStats(stats, cameras);
    renderActiveDetections(active);
    updateCamFilters(cameras);

    if (State.activeView === 'live') {
      renderCameraGrid(cameras);
    }

    // Refresh current view data
    if (State.activeView === 'events') loadEvents();

    // Last update
    Dom.lastUpdate.textContent = `LAST UPDATE: ${new Date().toLocaleTimeString('en-GB', { hour12:false })}`;

    if (!apiOk && State.apiOnline !== false) {
      toast('API connection lost', 'error');
    }

  } catch (err) {
    console.error('Poll error:', err);
  }

  _pollTimer = setTimeout(poll, Config.refreshMs);
}

// ── Debounce ──────────────────────────────────────────────────────────────────

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  const map = { '1':'live', '2':'events', '3':'recordings', '4':'snapshots', '5':'settings' };
  if (map[e.key]) switchView(map[e.key]);
  if (e.key === 'f' || e.key === 'F') {
    document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────

(function boot() {
  toast('Connecting to Raaqib NVR...', 'success', 2000);
  switchView('live');
  poll();
})();
