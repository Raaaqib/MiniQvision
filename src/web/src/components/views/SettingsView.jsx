import React, { useState } from 'react';
import { useSystem } from '../../context/SystemContext';
import { Save, Globe, RefreshCcw, Cpu, HardDrive, Shield } from 'lucide-react';
import { motion } from 'framer-motion';

export function SettingsView() {
  const { config, updateConfig, state } = useSystem();
  const [form, setForm] = useState({
    apiBase: config.apiBase,
    refreshMs: config.refreshMs / 1000
  });

  const handleSave = (e) => {
    e.preventDefault();
    updateConfig({
      apiBase: form.apiBase.replace(/\/$/, ''),
      refreshMs: parseInt(form.refreshMs) * 1000
    });
    // Add toast notification later
  };

  return (
    <div className="h-full flex flex-col p-8 space-y-8 overflow-y-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white mb-1">System Settings</h2>
        <p className="text-sm text-slate-500">Configure connection and monitoring parameters</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* API Config */}
        <section className="bg-[var(--bg-secondary)] rounded-2xl border border-white/5 p-8 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <Globe className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-bold text-white">API Connection</h3>
          </div>
          
          <form onSubmit={handleSave} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Base API URL</label>
              <input 
                type="text"
                value={form.apiBase}
                onChange={e => setForm({...form, apiBase: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500/50 transition-colors"
                placeholder="http://localhost:8000/api"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Refresh Interval (Seconds)</label>
              <input 
                type="number"
                value={form.refreshMs}
                onChange={e => setForm({...form, refreshMs: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-blue-500/50 transition-colors"
                min="1"
              />
            </div>

            <button 
              type="submit"
              className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs py-4 rounded-xl transition-all shadow-lg shadow-blue-600/20 active:scale-95"
            >
              <Save className="w-4 h-4" />
              SAVE & RECONNECT
            </button>
          </form>
        </section>

        {/* System Info */}
        <div className="space-y-8">
          <section className="bg-[var(--bg-secondary)] rounded-2xl border border-white/5 p-8 space-y-6">
            <div className="flex items-center gap-3 mb-2">
              <Cpu className="w-5 h-5 text-emerald-500" />
              <h3 className="text-lg font-bold text-white">System Status</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white/5 p-4 rounded-xl">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Status</p>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${state.apiOnline ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  <span className="text-sm font-bold text-slate-200">{state.apiOnline ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
              </div>
              <div className="bg-white/5 p-4 rounded-xl">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Events</p>
                <span className="text-sm font-bold text-slate-200">{state.stats?.total_events || 0}</span>
              </div>
            </div>
          </section>

          <section className="bg-blue-600/10 rounded-2xl border border-blue-500/20 p-8">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-blue-500/20 rounded-xl">
                <Shield className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white mb-1">MiniQvision Pro v2.0</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Your system is running with hardware acceleration enabled. All detection models are initialized and patrolling.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
