import React from 'react';
import { useSystem } from './context/SystemContext';
import { Layout } from './components/layout/Layout';
import { LiveMonitor } from './components/views/LiveMonitor';
import { EventsView } from './components/views/EventsView';
import { RecordingsView } from './components/views/RecordingsView';
import { SnapshotsView } from './components/views/SnapshotsView';
import { SettingsView } from './components/views/SettingsView';

function AppContent() {
  const { activeView } = useSystem();

  const renderView = () => {
    switch (activeView) {
      case 'live': return <LiveMonitor />;
      case 'events': return <EventsView />;
      case 'recordings': return <RecordingsView />;
      case 'snapshots': return <SnapshotsView />;
      case 'settings': return <SettingsView />;
      default: return <LiveMonitor />;
    }
  };

  return (
    <Layout>
      {renderView()}
    </Layout>
  );
}

export default function App() {
  return (
    <div className="dark">
      <AppContent />
    </div>
  );
}
