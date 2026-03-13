import React, { useState, useEffect } from 'react';
import { useSystem } from '../../context/SystemContext';
import { Play, Download, Video, Calendar, Search } from 'lucide-react';
import { motion } from 'framer-motion';

export function RecordingsView() {
  const { fetchApi, config } = useSystem();
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadRecordings = async () => {
    setLoading(true);
    const data = await fetchApi('/recordings');
    setRecordings(data || []);
    setLoading(false);
  };

  useEffect(() => {
    loadRecordings();
  }, []);

  return (
    <div className="h-full flex flex-col p-8 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white mb-1">Recordings</h2>
          <p className="text-sm text-slate-500">Stored video clips and event replays</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {recordings.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
            {recordings.map((clip, idx) => {
              const dlUrl = `${config.apiBase}/recordings/${encodeURIComponent(clip.filename)}`;
              return (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.02 }}
                  key={clip.filename}
                  className="group bg-[var(--bg-tertiary)] rounded-2xl border border-white/5 overflow-hidden hover:border-blue-500/30 transition-all duration-300"
                >
                  <div className="aspect-video bg-slate-900 flex items-center justify-center relative group-hover:scale-105 transition-transform duration-500">
                    <Video className="w-12 h-12 text-slate-800" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <a 
                        href={dlUrl} 
                        target="_blank" 
                        rel="noreferrer"
                        className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white shadow-xl shadow-blue-600/40 hover:scale-110 active:scale-95 transition-all"
                      >
                        <Play className="w-6 h-6 ml-1" />
                      </a>
                    </div>
                  </div>
                  
                  <div className="p-5 space-y-3">
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-slate-200 truncate" title={clip.filename}>
                        {clip.filename}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 mt-1 uppercase">
                        {new Date(clip.modified * 1000).toLocaleString()}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-white/5">
                      <span className="text-[10px] font-mono font-bold text-blue-500/80 bg-blue-500/5 px-2 py-0.5 rounded">
                        {clip.size_mb} MB
                      </span>
                      <a 
                        href={dlUrl} 
                        download={clip.filename}
                        className="text-[10px] font-bold text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                      >
                        <Download className="w-3 h-3" />
                        DOWNLOAD
                      </a>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        ) : !loading && (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-4">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
              <Video className="w-8 h-8 opacity-20" />
            </div>
            <p className="text-sm font-medium uppercase tracking-widest opacity-50">No recordings available</p>
          </div>
        )}
      </div>
    </div>
  );
}
