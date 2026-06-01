import React, { useState } from 'react';
import { 
  Search, 
  User, 
  Phone, 
  Clock, 
  Coins, 
  ShieldAlert, 
  Heart, 
  Compass, 
  MessageSquare,
  Sparkles,
  ChevronRight,
  AlertTriangle,
  HelpCircle
} from 'lucide-react';

export default function Inspector({ conversations }) {
  const [selectedId, setSelectedId] = useState(conversations[0]?.id || "");
  const [searchTerm, setSearchTerm] = useState("");

  const selectedThread = conversations.find(c => c.id === selectedId);

  // Filter conversations based on search
  const filteredConversations = conversations.filter(c => {
    const term = searchTerm.toLowerCase();
    return (
      c.customerName.toLowerCase().includes(term) ||
      c.phoneNumber.includes(term) ||
      c.intent.toLowerCase().includes(term) ||
      c.emotion.toLowerCase().includes(term) ||
      c.status.toLowerCase().includes(term)
    );
  });

  return (
    <div className="inspector-layout fade-in">
      {/* Sidebar List */}
      <div className="glass-panel threads-sidebar">
        <div className="search-input-wrapper">
          <Search />
          <input 
            type="text" 
            placeholder="Search by client, status, vibe..." 
            className="search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="threads-list">
          {filteredConversations.length === 0 ? (
            <div className="empty-state">
              <MessageSquare />
              <p>No conversations found</p>
            </div>
          ) : (
            filteredConversations.map(c => {
              const lastMessage = c.messages[c.messages.length - 1]?.text || "";
              const isActive = c.id === selectedId;
              
              return (
                <div 
                  key={c.id} 
                  className={`thread-item ${isActive ? 'active' : ''}`}
                  onClick={() => setSelectedId(c.id)}
                >
                  <div className="thread-item-header">
                    <span className="thread-client-name">{c.customerName}</span>
                    <span className="thread-time">
                      {new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  
                  <div className="thread-preview">{lastMessage}</div>
                  
                  <div className="thread-meta-row">
                    <span className={`badge ${c.status}`}>
                      {c.status}
                    </span>
                    <span className={`badge emotion-${c.emotion}`}>
                      {c.emotion}
                    </span>
                    <span style={{ fontSize: '0.65rem', color: '#707293' }}>
                      ${c.cost.toFixed(4)}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Details Panel */}
      {selectedThread ? (
        <div className="glass-panel thread-details-container" style={{ padding: 0 }}>
          {/* Chat Transcript pane */}
          <div className="chat-history-pane">
            <div className="chat-header-details">
              <div>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem' }}>
                  {selectedThread.customerName}
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#707293', marginTop: '2px', display: 'flex', gap: '10px' }}>
                  <span>ID: {selectedThread.id}</span>
                  <span>•</span>
                  <span>{new Date(selectedThread.timestamp).toLocaleString()}</span>
                </p>
              </div>
              <span className={`badge ${selectedThread.status}`}>
                {selectedThread.status}
              </span>
            </div>

            <div className="chat-messages-scroller">
              {selectedThread.messages.map((m, idx) => (
                <div key={idx} className={`chat-message-bubble ${m.sender}`}>
                  <span className="message-sender-name">
                    {m.sender === 'user' ? selectedThread.customerName : 'Nuit Fragrance Concierge'}
                  </span>
                  <div className="message-text-content">
                    {m.text}
                  </div>
                  <span className="message-timestamp">{m.timestamp}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right Inspector Drawer (Metadata / Auditor Logs) */}
          <div className="thread-inspector-panel" style={{ padding: '24px 20px', borderLeft: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.05)' }}>
            
            {/* Client Profile */}
            <div style={{ marginBottom: '24px' }}>
              <h4 className="metadata-section-title">Client Profile</h4>
              <div className="metadata-row-item">
                <span>Contact Name</span>
                <span>{selectedThread.customerName}</span>
              </div>
              <div className="metadata-row-item">
                <span>Phone Number</span>
                <span>{selectedThread.phoneNumber}</span>
              </div>
              <div className="metadata-row-item">
                <span>Detected Vibe</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Heart size={12} style={{ color: 'var(--accent-purple)' }} />
                  <span className={`badge emotion-${selectedThread.emotion}`} style={{ fontSize: '0.6rem', padding: '1px 4px' }}>{selectedThread.emotion}</span>
                </span>
              </div>
              <div className="metadata-row-item">
                <span>RAG Routing</span>
                <span>{selectedThread.intent}</span>
              </div>
            </div>

            {/* Token Analytics */}
            <div style={{ marginBottom: '24px' }}>
              <h4 className="metadata-section-title">Client Cost Metrics</h4>
              <div className="metadata-row-item">
                <span>Input Tokens</span>
                <span>{selectedThread.tokens.input.toLocaleString()}</span>
              </div>
              <div className="metadata-row-item">
                <span>Output Tokens</span>
                <span>{selectedThread.tokens.output.toLocaleString()}</span>
              </div>
              <div className="metadata-row-item" style={{ borderBottom: 'none' }}>
                <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Calculated Cost</span>
                <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>${selectedThread.cost.toFixed(5)}</span>
              </div>
            </div>

            {/* Handoff Summary (Only if escalated) */}
            {selectedThread.status === "escalated" && (
              <div style={{ marginBottom: '24px', border: '1px solid rgba(255, 62, 108, 0.25)', borderRadius: '10px', padding: '14px', background: 'rgba(255, 62, 108, 0.03)' }}>
                <h4 className="metadata-section-title" style={{ color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <AlertTriangle size={14} /> Human Handoff Report
                </h4>
                <div className="handoff-summary-text">
                  {selectedThread.handoffSummary}
                </div>
              </div>
            )}

            {/* Auditor Checklogs */}
            <div>
              <h4 className="metadata-section-title">LangGraph System Audits</h4>
              <div className="audit-log-scroller">
                {selectedThread.failedChecks && selectedThread.failedChecks.length > 0 && (
                  <div className="audit-log-card failed-checks-card">
                    <div style={{ fontWeight: 'bold', color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                      <ShieldAlert size={12} /> FAILED VIOLATION
                    </div>
                    {selectedThread.failedChecks.map((fc, i) => (
                      <div key={i}>• {fc}</div>
                    ))}
                  </div>
                )}
                {selectedThread.auditLogs.map((log, index) => (
                  <div key={index} className="audit-log-card">
                    {log}
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      ) : (
        <div className="glass-panel empty-state" style={{ height: '100%', display: 'flex', justifyContent: 'center' }}>
          <MessageSquare />
          <h2>No Conversation Selected</h2>
          <p>Click on any thread in the sidebar to review the conversation log and audit trace.</p>
        </div>
      )}
    </div>
  );
}
