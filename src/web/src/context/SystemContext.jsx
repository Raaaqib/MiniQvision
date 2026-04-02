import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const SystemContext = createContext();

export function SystemProvider({ children }) {
  const [config, setConfig] = useState({
    apiBase: localStorage.getItem('raaqib_api') || 'http://localhost:8000/api',
    refreshMs: parseInt(localStorage.getItem('raaqib_refresh') || '3000'),
  });

  const [state, setState] = useState({
    cameras: {},
    stats: {},
    activeEvents: [],
    apiOnline: false,
    lastUpdate: null,
  });

  const [activeView, setActiveView] = useState('live');

  const updateConfig = (newConfig) => {
    const updated = { ...config, ...newConfig };
    setConfig(updated);
    localStorage.setItem('raaqib_api', updated.apiBase);
    localStorage.setItem('raaqib_refresh', updated.refreshMs);
  };

  const fetchApi = useCallback(async (endpoint) => {
    try {
      const res = await fetch(`${config.apiBase}${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`Fetch error (${endpoint}):`, err);
      return null;
    }
  }, [config.apiBase]);

  const poll = useCallback(async () => {
    const [status, stats] = await Promise.all([
      fetchApi('/status'),
      fetchApi('/stats'),
    ]);

    const apiOk = !!status;
    
    setState(prev => ({
      ...prev,
      cameras: status?.cameras || {},
      activeEvents: status?.active_events || [],
      stats: stats || {},
      apiOnline: apiOk,
      lastUpdate: new Date().toLocaleTimeString('en-GB', { hour12: false }),
    }));
  }, [fetchApi]);

  useEffect(() => {
    poll();
    const timer = setInterval(poll, config.refreshMs);
    return () => clearInterval(timer);
  }, [poll, config.refreshMs]);

  const value = {
    config,
    state,
    activeView,
    setActiveView,
    updateConfig,
    refresh: poll,
    fetchApi
  };

  return <SystemContext.Provider value={value}>{children}</SystemContext.Provider>;
}

export function useSystem() {
  const context = useContext(SystemContext);
  if (!context) throw new Error('useSystem must be used within SystemProvider');
  return context;
}
