import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  MessageSquare, 
  FileText, 
  Terminal, 
  Moon, 
  Sparkles,
  RefreshCw,
  Coins
} from 'lucide-react';
import { mockConversations, getAnalyticsSummary } from './mockData';
import Dashboard from './components/Dashboard';
import Inspector from './components/Inspector';
import FileManager from './components/FileManager';
import Playground from './components/Playground';

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
    await new Promise(r => setTimeout(r, 600)); // nice visual spin duration
    setRefreshing(false);
  };

  // Add conversation from playground tests to the active list
  const handleAddNewSession = (newSession) => {
    setConversations(prev => [newSession, ...prev]);
  };

  const getSummary = getAnalyticsSummary(conversations);

  const menuItems = [
    { id: 'dashboard', name: 'Overview Dashboard', icon: BarChart3 },
    { id: 'inspector', name: 'Client Conversations', icon: MessageSquare },
    { id: 'files', name: 'Knowledge Ingestion', icon: FileText },
    { id: 'playground', name: 'AI Concierge Playground', icon: Terminal }
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
            <span>{isBackendConnected ? 'Backend Server Online' : 'Simulated Mock Mode'}</span>
          </div>
          
          <button 
            onClick={handleRefresh}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '8px', 
              padding: '8px', 
              background: 'rgba(255,255,255,0.03)', 
              border: '1px solid rgba(255,255,255,0.06)', 
              borderRadius: '6px', 
              color: '#9fa0bd', 
              fontSize: '0.75rem', 
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease'
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
              {activeTab === 'files' && 'RAG Ingestion Center'}
              {activeTab === 'playground' && 'AI Support Concierge Sandbox'}
            </h1>
            <p>
              {activeTab === 'dashboard' && 'Monitor token rates, customer emotion classifications, and automated resolutions.'}
              {activeTab === 'inspector' && 'Inspect conversation transcripts, agent sentiment classification, and LangGraph audit trails.'}
              {activeTab === 'files' && 'Manage static instructions and upload dynamic documents to the chatbot knowledge base.'}
              {activeTab === 'playground' && 'Chat with the bot concierge directly and trace the execution path of the LangGraph.'}
            </p>
          </div>

          <div className="header-actions">
            <span className="header-badge" style={{ color: 'var(--accent-cyan)' }}>
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
          {activeTab === 'playground' && <Playground onNewSession={handleAddNewSession} />}
        </div>

      </main>

    </div>
  );
}
