import React, { useState, useEffect } from 'react';
import { useSystem } from '../../context/SystemContext';
import { 
  Wifi, 
  WifiOff, 
  Clock, 
  Database,
  Shield,
  ShieldAlert
} from 'lucide-react';
import { cn } from '../../utils/cn';

export function Topbar() {
  const { state } = useSystem();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const storageUsed = state.stats?.storage_percent || 0;
  const isArmed = true; // Placeholder for armed state logic if available

  return (
    <header className="h-16 bg-[var(--bg-secondary)] border-b border-white/5 px-8 flex items-center justify-between z-20">
      <div className="flex items-center gap-8">
        <div className="flex flex-col items-center border-r border-white/10 pr-8">
          <div className="flex items-center gap-2 text-white font-mono text-lg font-medium tracking-wider">
            <Clock className="w-4 h-4 text-blue-500" />
            {time.toLocaleTimeString('en-GB', { hour12: false })}
          </div>
          <div className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">
            {time.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Database className="w-3 h-3 text-slate-400" />
              <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-500" 
                  style={{ width: `${storageUsed}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-400 font-mono">{storageUsed}%</span>
            </div>
            <span className="text-[9px] text-slate-500 font-bold tracking-tight uppercase">Storage</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <button className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300",
          isArmed 
            ? "border-red-500/20 bg-red-500/5 text-red-500 shadow-lg shadow-red-500/10"
            : "border-slate-700 bg-slate-800 text-slate-400"
        )}>
          {isArmed ? <ShieldAlert className="w-3.5 h-3.5" /> : <Shield className="w-3.5 h-3.5" />}
          <span className="text-[10px] font-bold tracking-widest uppercase">{isArmed ? 'Armed' : 'Disarmed'}</span>
          <div className={cn("w-1.5 h-1.5 rounded-full", isArmed ? "bg-red-500 animate-pulse" : "bg-slate-600")} />
        </button>

        <div className="h-6 w-px bg-white/10" />

        <div className="flex items-center gap-3">
          <div className={cn(
            "flex items-center gap-2 px-3 py-1 bg-white/5 rounded-lg border border-white/5",
            state.apiOnline ? "text-emerald-500" : "text-red-500"
          )}>
            {state.apiOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span className="text-[10px] font-bold font-mono tracking-widest">API</span>
          </div>
        </div>
      </div>
    </header>
  );
}
