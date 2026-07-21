import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  MessageSquare, 
  Ticket,
  RefreshCw
} from 'lucide-react';
import Dashboard from './components/Dashboard';
import Inspector from './components/Inspector';
import Tickets from './components/Tickets';
import LiveTicker from './components/LiveTicker';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [conversations, setConversations] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setConversations(data);
          setIsBackendConnected(true);
        }
      } else {
        setIsBackendConnected(false);
      }

      const ticketsRes = await fetch('/api/tickets');
      if (ticketsRes.ok) {
        const ticketsData = await ticketsRes.json();
        if (Array.isArray(ticketsData)) {
          setTickets(ticketsData);
        }
      }
    } catch (err) {
      console.warn('Could not fetch data from server.');
      setIsBackendConnected(false);
    }
  };

  const handleOpenConversation = (convId) => {
    setSelectedConversationId(convId);
    setActiveTab('inspector');
  };

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(() => {
      fetchConversations();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchConversations();
    await new Promise(r => setTimeout(r, 600));
    setRefreshing(false);
  };

  const handleResolveTicket = async (ticketId) => {
    try {
      await fetch(`/api/tickets/${ticketId}/resolve`, { method: 'PATCH' });
      await fetchConversations();
    } catch (err) {
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

  const menuItems = [
    { id: 'dashboard', name: 'Overview Dashboard', icon: BarChart3 },
    { id: 'inspector', name: 'Client Conversations', icon: MessageSquare },
    { id: 'tickets', name: 'Escalation Tickets', icon: Ticket }
  ];

  return (
    <div className="app-container">
      
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="wordmark">nu<span>i</span>t</div>
          <div className="logo-tagline">AI CONCIERGE — OPERATIONS</div>
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
          <div className="sync-status">
            <span className={`sync-dot ${isBackendConnected ? '' : 'offline'}`}></span>
            <span>{isBackendConnected ? 'SYNC ONLINE' : 'SYNC SIMULATED'}</span>
          </div>
          
          <button 
            onClick={handleRefresh}
            className="btn-gold"
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '8px', 
              width: '100%',
              marginTop: '4px'
            }}
          >
            <RefreshCw size={12} className={refreshing ? 'spin-loader' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="main-content">
        
        {/* Content Body */}
        <div className="content-body">
          {activeTab === 'dashboard' && <Dashboard conversations={conversations} />}
          {activeTab === 'inspector' && (
            <Inspector 
              conversations={conversations} 
              tickets={tickets}
              selectedConversationId={selectedConversationId}
              onSelectConversation={setSelectedConversationId}
              onReply={handleReplyToConversation} 
            />
          )}
          {activeTab === 'tickets' && (
            <Tickets 
              tickets={tickets} 
              onResolve={handleResolveTicket} 
              onOpenConversation={handleOpenConversation} 
            />
          )}
        </div>

        <LiveTicker conversations={conversations} />

      </main>

    </div>
  );
}
