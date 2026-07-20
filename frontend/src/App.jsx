import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  MessageSquare, 
  Ticket,
  RefreshCw,
  Coins,
  Sparkles
} from 'lucide-react';
import { getAnalyticsSummary } from './mockData';
import { supabase } from './lib/supabaseClient';
import Dashboard from './components/Dashboard';
import Inspector from './components/Inspector';
import Tickets from './components/Tickets';


export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [conversations, setConversations] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchConversations = async () => {
    try {
      if (supabase) {
        // Supabase path
        const { data: convData } = await supabase
          .from('conversations')
          .select('*')
          .order('created_at', { ascending: false });

        if (Array.isArray(convData)) {
          setConversations(convData);
        }

        const { data: ticketsData } = await supabase
          .from('tickets')
          .select('*')
          .order('created_at', { ascending: false });

        if (Array.isArray(ticketsData)) {
          setTickets(ticketsData);
        }
      } else {
        // REST API fallback
        const res = await fetch('/api/conversations');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setConversations(data);
          }
          setIsBackendConnected(true);
        } else {
          setIsBackendConnected(false);
        }

        const ticketsRes = await fetch('/api/tickets');
        if (ticketsRes.ok) {
          const data = await ticketsRes.json();
          if (Array.isArray(data)) {
            setTickets(data);
          }
        }
      }
    } catch (err) {
      console.warn('Could not fetch data from server. Using mock data.');
      setIsBackendConnected(false);
    }
  };

  useEffect(() => {
    fetchConversations();

    // Auto-refresh conversations and tickets every 5 seconds
    const interval = setInterval(() => {
      fetchConversations();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchConversations();
    await new Promise(r => setTimeout(r, 600)); // visual spin duration
    setRefreshing(false);
  };

  const handleResolveTicket = async (ticketId) => {
    try {
      if (supabase) {
        await supabase
          .from('tickets')
          .update({ status: 'resolved', resolved_at: new Date().toISOString() })
          .eq('id', ticketId);
      } else {
        await fetch(`/api/tickets/${ticketId}/resolve`, { method: 'PATCH' });
      }
      // Refresh tickets after resolving
      await fetchConversations();
    } catch (err) {
      // Optimistic update on failure — update local state directly
      setTickets(prev =>
        prev.map(t =>
          t.id === ticketId
            ? { ...t, status: 'resolved', resolved_at: new Date().toISOString() }
            : t
        )
      );
    }
  };

  const handleReplyToConversation = async (conversationId, replyText) => {
    try {
      const res = await fetch(`/api/conversations/${conversationId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: replyText })
      });
      if (res.ok) {
        await fetchConversations();
      }
    } catch (err) {
      console.error('Error replying to conversation:', err);
    }
  };

  const getSummary = getAnalyticsSummary(conversations);

  const menuItems = [
    { id: 'dashboard', name: 'Overview Dashboard', icon: BarChart3 },
    { id: 'inspector', name: 'Client Conversations', icon: MessageSquare },
    { id: 'tickets', name: 'Escalation Tickets', icon: Ticket }
  ];

  const headerContent = {
    dashboard: {
      title: 'Nuit Fragrances Concierge Dashboard',
      subtitle: 'Monitor token rates, customer emotion classifications, and automated resolutions.'
    },
    inspector: {
      title: 'Customer Session Auditor',
      subtitle: 'Inspect conversation transcripts, social platform origin, and LangGraph audit trails.'
    },
    tickets: {
      title: 'Escalation Ticket Queue',
      subtitle: 'Review and resolve human-handoff escalations raised by the AI concierge.'
    }
  };

  const currentHeader = headerContent[activeTab] || headerContent.dashboard;

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
            <h1>{currentHeader.title}</h1>
            <p>{currentHeader.subtitle}</p>
          </div>

          <div className="header-actions">
            <button 
              onClick={handleRefresh}
              className={`header-badge refresh-button ${refreshing ? 'spin-loader' : ''}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(0, 0, 0, 0.04)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: '#686256',
                cursor: 'pointer',
                padding: '6px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                transition: 'all 0.2s ease',
                outline: 'none'
              }}
            >
              <RefreshCw size={12} className={refreshing ? 'spin-loader' : ''} />
              <span>Refresh</span>
            </button>
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
          {activeTab === 'inspector' && <Inspector conversations={conversations} onReply={handleReplyToConversation} />}
          {activeTab === 'tickets' && <Tickets tickets={tickets} onResolve={handleResolveTicket} onReply={handleReplyToConversation} />}
        </div>

      </main>

    </div>
  );
}
