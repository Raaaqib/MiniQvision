import React, { useState, useEffect } from 'react';
import { useSystem } from '../../context/SystemContext';
import { Camera, RefreshCw, Maximize2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function SnapshotsView() {
  const { fetchApi, config } = useSystem();
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  const loadSnapshots = async () => {
    setLoading(true);
    const data = await fetchApi('/snapshots?limit=60');
    setSnapshots(data || []);
    setLoading(false);
  };

  useEffect(() => {
    loadSnapshots();
  }, []);

  return (
    <div className="h-full flex flex-col p-8 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white mb-1">Snapshots</h2>
          <p className="text-sm text-slate-500">Captured freeze-frames from cameras</p>
        </div>
        <button 
           onClick={loadSnapshots}
           className="p-2.5 bg-white/5 border border-white/5 rounded-xl text-slate-400 hover:text-white transition-colors"
         >
           <RefreshCw className={loading ? "animate-spin w-4 h-4" : "w-4 h-4"} />
         </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {snapshots.length > 0 ? (
          <div className="grid grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 gap-4">
            {snapshots.map((snap, idx) => {
              const src = `${config.apiBase}/snapshots/${encodeURIComponent(snap.filename)}`;
              return (
                <motion.div
                  key={snap.filename}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.01 }}
                  whileHover={{ y: -4 }}
                  onClick={() => setSelected(src)}
                  className="group relative aspect-video bg-slate-900 rounded-xl overflow-hidden cursor-pointer border border-white/5 shadow-lg shadow-black/20"
                >
                  <img 
                    src={src} 
                    alt={snap.filename} 
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-blue-600/0 group-hover:bg-blue-600/10 transition-colors" />
                  <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <p className="text-[9px] font-mono text-white/70 truncate">{snap.filename}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        ) : !loading && (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-4">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
              <Camera className="w-8 h-8 opacity-20" />
            </div>
            <p className="text-sm font-medium uppercase tracking-widest opacity-50">No snapshots yet</p>
          </div>
        )}
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex items-center justify-center p-4 md:p-12"
            onClick={() => setSelected(null)}
          >
            <button className="absolute top-8 right-8 p-3 bg-white/10 hover:bg-white/20 rounded-full text-white transition-all">
              <X className="w-6 h-6" />
            </button>
            <motion.img
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              src={selected}
              className="max-w-full max-h-full rounded-2xl shadow-3xl object-contain border border-white/10"
              onClick={e => e.stopPropagation()}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
