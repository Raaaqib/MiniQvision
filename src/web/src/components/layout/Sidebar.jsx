import React from 'react';
import { useSystem } from '../../context/SystemContext';
import { cn } from '../../utils/cn';
import { 
  Activity, 
  Camera, 
  History, 
  Image as ImageIcon, 
  Settings, 
  LayoutDashboard,
  Circle
} from 'lucide-react';

const navItems = [
  { id: 'live', label: 'Live Monitor', icon: LayoutDashboard },
  { id: 'events', label: 'Events', icon: Activity },
  { id: 'recordings', label: 'Recordings', icon: History },
  { id: 'snapshots', label: 'Snapshots', icon: ImageIcon },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { activeView, setActiveView, state } = useSystem();
  const cameras = Object.entries(state.cameras);

  return (
    <aside className="w-64 bg-[var(--bg-secondary)] border-r border-white/5 flex flex-col h-full transition-all duration-300">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/20">
            <Camera className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold tracking-tight text-white">RAAQIB</h1>
            <p className="text-[10px] text-slate-500 font-mono">NVR SYSTEM V2.0</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={cn(
                "nav-item w-full",
                activeView === item.id && "nav-item-active"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium text-sm">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        <div>
          <h3 className="text-[10px] font-bold text-slate-500 tracking-widest uppercase mb-4">Cameras</h3>
          <div className="space-y-2">
            {cameras.length > 0 ? cameras.map(([id, cam]) => (
              <div key={id} className="group flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  cam.recording ? "bg-red-500 animate-pulse" : 
                  cam.motion ? "bg-amber-500" : 
                  cam.online ? "bg-emerald-500" : "bg-slate-700"
                )} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-300 truncate">{id.replace(/_/g, ' ').toUpperCase()}</p>
                  <p className="text-[10px] text-slate-500 font-mono">FPS: {cam.fps?.toFixed(1) || 0}</p>
                </div>
              </div>
            )) : (
              <p className="text-xs text-slate-600 italic">No cameras detected</p>
            )}
          </div>
        </div>
      </div>

      <div className="p-6 border-t border-white/5">
        <div className="bg-white/5 rounded-xl p-4">
          <p className="text-[10px] text-slate-500 font-mono mb-2 uppercase tracking-wide">Last Update</p>
          <p className="text-xs text-slate-300 font-mono">{state.lastUpdate || '--:--:--'}</p>
        </div>
      </div>
    </aside>
  );
}
