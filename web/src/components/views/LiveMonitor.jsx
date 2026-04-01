import React, { useState, useEffect } from 'react';
import { useSystem } from '../../context/SystemContext';
import { Maximize2, Minimize2, Grid2X2, Grid3X3, Square, WifiOff } from 'lucide-react';
import { cn } from '../../utils/cn';
import { motion, AnimatePresence } from 'framer-motion';

function CameraTile({ id, cam, gridCols }) {
  const { config } = useSystem();
  const [snapshotUrl, setSnapshotUrl] = useState('');
  
  useEffect(() => {
    let interval;
    if (cam.online) {
      const updateSnapshot = () => {
        setSnapshotUrl(`${config.apiBase}/cameras/${encodeURIComponent(id)}/snapshot.jpg?t=${Date.now()}`);
      };
      updateSnapshot();
      interval = setInterval(updateSnapshot, 100); // 10fps snapshot polling
    }
    return () => clearInterval(interval);
  }, [id, cam.online, config.apiBase]);

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "relative group bg-[var(--bg-tertiary)] rounded-2xl overflow-hidden border border-white/5 transition-all duration-300",
        cam.motion && "ring-2 ring-amber-500/50 shadow-lg shadow-amber-500/10",
        cam.recording && "ring-2 ring-red-500/50 shadow-lg shadow-red-500/10"
      )}
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 p-4 z-10 bg-gradient-to-b from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold font-mono text-white tracking-widest uppercase truncate max-w-[120px]">
              {id.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "px-2 py-0.5 rounded text-[9px] font-bold font-mono uppercase tracking-tighter",
              cam.recording ? "bg-red-500 text-white animate-pulse" :
              cam.motion ? "bg-amber-500 text-black" :
              cam.online ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-400"
            )}>
              {cam.recording ? '● REC' : cam.motion ? '◈ MOTION' : cam.online ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Feed */}
      <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
        {cam.online ? (
          <img 
            src={snapshotUrl} 
            alt={id} 
            className="w-full h-full object-cover"
            onError={() => setSnapshotUrl('')}
          />
        ) : (
          <div className="flex flex-col items-center gap-3 text-slate-600">
            <WifiOff className="w-8 h-8 opacity-20" />
            <span className="text-[10px] font-bold font-mono tracking-widest uppercase">No Signal</span>
            {cam.error && <span className="text-[8px] opacity-50 max-w-[80%] text-center uppercase">{cam.error}</span>}
          </div>
        )}

        {/* HUD Elements */}
        {cam.online && (
          <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between pointer-events-none transition-transform duration-300 group-hover:-translate-y-1">
            <div className="flex flex-col gap-1">
               <div className="text-[9px] font-mono text-white/50 bg-black/40 backdrop-blur-sm px-2 py-0.5 rounded">
                 TRK {cam.active_tracks || 0}
               </div>
            </div>
            <div className="text-[9px] font-mono text-white/50 bg-black/40 backdrop-blur-sm px-2 py-0.5 rounded">
              {cam.fps?.toFixed(1) || 0} FPS
            </div>
          </div>
        )}
      </div>

      {/* Interaction Overlay */}
      <div className="absolute inset-0 bg-blue-600/0 group-hover:bg-blue-600/5 transition-colors cursor-pointer" />
    </motion.div>
  );
}

export function LiveMonitor() {
  const { state } = useSystem();
  const [gridCols, setGridCols] = useState(2);
  const cameras = Object.entries(state.cameras);

  return (
    <div className="h-full flex flex-col p-8 space-y-6 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white mb-1">Live Monitor</h2>
          <p className="text-sm text-slate-500">Real-time surveillance overview</p>
        </div>
        
        <div className="flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5">
          <button 
            onClick={() => setGridCols(1)}
            className={cn("p-2 rounded-lg transition-all", gridCols === 1 ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300")}
          >
            <Square className="w-4 h-4" />
          </button>
          <button 
            onClick={() => setGridCols(2)}
            className={cn("p-2 rounded-lg transition-all", gridCols === 2 ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300")}
          >
            <Grid2X2 className="w-4 h-4" />
          </button>
          <button 
            onClick={() => setGridCols(3)}
            className={cn("p-2 rounded-lg transition-all", gridCols === 3 ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300")}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {cameras.length > 0 ? (
        <motion.div 
          className={cn(
            "grid gap-6 auto-rows-min",
            gridCols === 1 ? "grid-cols-1" : 
            gridCols === 2 ? "grid-cols-1 lg:grid-cols-2" : 
            "grid-cols-1 md:grid-cols-2 xl:grid-cols-3"
          )}
        >
          {cameras.map(([id, cam]) => (
            <CameraTile key={id} id={id} cam={cam} gridCols={gridCols} />
          ))}
        </motion.div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-600 space-y-4">
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
            <WifiOff className="w-8 h-8 opacity-20" />
          </div>
          <p className="text-sm font-medium uppercase tracking-widest opacity-50">No cameras configured or connected</p>
        </div>
      )}
    </div>
  );
}
