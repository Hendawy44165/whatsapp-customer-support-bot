import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  MessageSquare, 
  FileText, 
  Settings as SettingsIcon, 
  RefreshCw,
  Coins,
  Sparkles
} from 'lucide-react';
import { mockConversations, getAnalyticsSummary } from './mockData';
import Dashboard from './components/Dashboard';
import Inspector from './components/Inspector';
import FileManager from './components/FileManager';
import Settings from './components/Settings';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [conversations, setConversations] = useState(mockConversations);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Check connection to FastAPI backend
  const checkConnection = async () => {
    try {
      const res = await fetch('/api/documents');
      setIsBackendConnected(res.ok);
    } catch (err) {
      setIsBackendConnected(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await checkConnection();
    await new Promise(r => setTimeout(r, 600)); // visual spin duration
    setRefreshing(false);
  };

  const getSummary = getAnalyticsSummary(conversations);

  const menuItems = [
    { id: 'dashboard', name: 'Overview Dashboard', icon: BarChart3 },
    { id: 'inspector', name: 'Client Conversations', icon: MessageSquare },
    { id: 'files', name: 'Help Library & Docs', icon: FileText },
    { id: 'settings', name: 'System Settings', icon: SettingsIcon }
  ];

  return (
    <div className="app-container">
      
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">🔮</div>
          <div>
            <h1 className="logo-text">NUIT</h1>
            <span className="logo-subtitle">AI Support Concierge</span>
          </div>
        </div>

        <nav className="nav-menu">
          {menuItems.map(item => (
            <button 
              key={item.id} 
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <item.icon />
              <span>{item.name}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className={`server-status ${isBackendConnected ? '' : 'offline-status'}`}>
            <span className={`status-indicator ${isBackendConnected ? '' : 'offline'}`}></span>
            <span>{isBackendConnected ? 'Sync Server Online' : 'Sync Simulated'}</span>
          </div>
          
          <button 
            onClick={handleRefresh}
            title="Scans knowledge directories, re-indexes customer reference sheets, and refreshes chatbot configurations."
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '8px', 
              padding: '8px', 
              background: 'rgba(0, 0, 0, 0.04)', 
              border: '1px solid var(--border-color)', 
              borderRadius: '6px', 
              color: '#686256', 
              fontSize: '0.75rem', 
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease',
              width: '100%',
              fontWeight: 500
            }}
          >
            <RefreshCw size={12} className={refreshing ? 'spin-loader' : ''} />
            <span>Sync System Indexes</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="main-content">
        
        {/* Header */}
        <header className="main-header">
          <div className="header-title-container">
            <h1>
              {activeTab === 'dashboard' && 'Nuit Fragrances Concierge Dashboard'}
              {activeTab === 'inspector' && 'Customer Session Auditor'}
              {activeTab === 'files' && 'Help Library & Docs'}
              {activeTab === 'settings' && 'System Configuration & Settings'}
            </h1>
            <p>
              {activeTab === 'dashboard' && 'Monitor token rates, customer emotion classifications, and automated resolutions.'}
              {activeTab === 'inspector' && 'Inspect conversation transcripts, social platform origin, and LangGraph audit trails.'}
              {activeTab === 'files' && 'Manage static instructions and upload custom guidelines to the chatbot reference registry.'}
              {activeTab === 'settings' && 'Configure active models, temperature parameters, API credentials, and default instructions.'}
            </p>
          </div>

          <div className="header-actions">
            <span className="header-badge" style={{ color: 'var(--accent-orange)' }}>
              <Coins />
              <span>Avg Cost: ${getSummary.avgCost.toFixed(5)}</span>
            </span>
            <span className="header-badge" style={{ color: 'var(--accent-purple)' }}>
              <Sparkles />
              <span>v1.0.0 Stable</span>
            </span>
          </div>
        </header>

        {/* Content Body */}
        <div className="content-body">
          {activeTab === 'dashboard' && <Dashboard conversations={conversations} />}
          {activeTab === 'inspector' && <Inspector conversations={conversations} />}
          {activeTab === 'files' && <FileManager />}
          {activeTab === 'settings' && <Settings />}
        </div>

      </main>

    </div>
  );
}
