import React, { useState, useEffect } from 'react';
import { useSystem } from '../../context/SystemContext';
import { RefreshCw, Filter, Search, Calendar, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

export function EventsView() {
  const { fetchApi } = useSystem();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ camera: '', label: '' });

  const loadEvents = async () => {
    setLoading(true);
    let url = '/events?limit=100';
    if (filter.camera) url += `&camera_id=${encodeURIComponent(filter.camera)}`;
    if (filter.label) url += `&label=${encodeURIComponent(filter.label)}`;
    
    const data = await fetchApi(url);
    setEvents(data || []);
    setLoading(false);
  };

  useEffect(() => {
    loadEvents();
  }, [filter]);

  return (
    <div className="h-full flex flex-col p-8 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white mb-1">Detection Events</h2>
          <p className="text-sm text-slate-500">Historical trail of identified objects</p>
        </div>
        
        <div className="flex items-center gap-3">
           <div className="flex items-center gap-2 bg-white/5 px-3 py-2 rounded-xl border border-white/5">
              <Search className="w-4 h-4 text-slate-500" />
              <input 
                type="text" 
                placeholder="Filter label..." 
                className="bg-transparent border-none text-xs text-white focus:ring-0 w-32 outline-none"
                value={filter.label}
                onChange={(e) => setFilter(prev => ({...prev, label: e.target.value}))}
              />
           </div>
           <button 
             onClick={loadEvents}
             className="p-2.5 bg-white/5 border border-white/5 rounded-xl text-slate-400 hover:text-white transition-colors"
           >
             <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
           </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-[var(--bg-secondary)] rounded-2xl border border-white/5 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Time</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Camera</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Object</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Confidence</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Duration</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {events.length > 0 ? events.map((ev, idx) => {
              const conf = (ev.confidence || ev.peak_confidence || 0) * 100;
              return (
                <motion.tr 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.01 }}
                  key={ev.id || idx} 
                  className="group hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-slate-300">
                        {new Date((ev.start_time || 0) * 1000).toLocaleTimeString('en-GB', { hour12: false })}
                      </span>
                      <span className="text-[10px] text-slate-600 font-mono">
                         {new Date((ev.start_time || 0) * 1000).toLocaleDateString()}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-bold font-mono text-blue-500/80 uppercase tracking-wider bg-blue-500/5 px-2 py-1 rounded">
                      {ev.camera_id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-semibold text-white capitalize">{ev.label}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600" style={{ width: `${conf}%` }} />
                      </div>
                      <span className="text-xs font-mono text-slate-500">{conf.toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs text-slate-400 font-mono">
                      {(ev.duration || 0).toFixed(1)}s
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-2 text-slate-600 hover:text-white transition-colors group-hover:translate-x-1 duration-300">
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              );
            }) : !loading && (
              <tr>
                <td colSpan="6" className="px-6 py-20 text-center">
                  <div className="flex flex-col items-center gap-3 text-slate-600">
                    <Calendar className="w-8 h-8 opacity-20" />
                    <span className="text-sm uppercase tracking-widest opacity-50">No events found</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
