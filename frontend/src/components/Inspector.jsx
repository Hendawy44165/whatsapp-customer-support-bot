import React, { useState } from 'react';
import { 
  Search, 
  User, 
  Phone, 
  Clock, 
  Coins, 
  ShieldAlert, 
  Heart, 
  MessageSquare,
  AlertTriangle,
  Send,
  MessageCircle
} from 'lucide-react';

// Custom lightweight Markdown renderer to parse lists and **bold** text in the client portal
function MarkdownText({ text }) {
  if (!text) return null;
  
  const lines = text.split('\n');
  
  return (
    <div className="markdown-content">
      {lines.map((line, idx) => {
        // Detect bullet lists e.g. "1. **Customer Intent**:" or "- Item"
        const listMatch = line.match(/^(\d+\.\s+|\*\s+|-+\s+)(.*)/);
        
        // Helper to parse **bold** blocks
        const renderLineContent = (content) => {
          const parts = content.split('**');
          return parts.map((part, i) => {
            if (i % 2 === 1) {
              return <strong key={i}>{part}</strong>;
            }
            return part;
          });
        };

        if (listMatch) {
          const listPrefix = listMatch[1];
          const listText = listMatch[2];
          const isDecimal = /^\d/.test(listPrefix);
          
          return (
            <li 
              key={idx} 
              style={{ 
                listStyleType: isDecimal ? 'decimal' : 'disc', 
                marginLeft: '18px', 
                marginBottom: '6px',
                fontSize: '0.85rem',
                lineHeight: '1.45',
                color: '#2C2B29'
              }}
            >
              {renderLineContent(listText)}
            </li>
          );
        }

        return (
          <p 
            key={idx} 
            style={{ 
              marginBottom: '8px', 
              minHeight: line.trim() === "" ? '6px' : 'auto',
              fontSize: '0.85rem',
              lineHeight: '1.45',
              color: '#2C2B29'
            }}
          >
            {renderLineContent(line)}
          </p>
        );
      })}
    </div>
  );
}

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
      c.status.toLowerCase().includes(term) ||
      c.channel.toLowerCase().includes(term)
    );
  });

  // Color mapping/labels for platform channels
  const getChannelLabel = (channel) => {
    switch (channel) {
      case 'whatsapp': return 'WhatsApp';
      case 'facebook': return 'FB Messenger';
      case 'telegram': return 'Telegram';
      case 'webchat': return 'Live Web Chat';
      default: return channel;
    }
  };

  return (
    <div className="inspector-layout fade-in">
      {/* Sidebar List */}
      <div className="glass-panel threads-sidebar">
        <div className="search-input-wrapper">
          <Search />
          <input 
            type="text" 
            placeholder="Search by client, channel, vibe..." 
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
                    <span className={`badge channel-${c.channel}`}>
                      {getChannelLabel(c.channel)}
                    </span>
                    <span className={`badge emotion-${c.emotion}`}>
                      {c.emotion}
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
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', color: '#191816' }}>
                  {selectedThread.customerName}
                </h3>
                <div style={{ fontSize: '0.75rem', color: '#686256', marginTop: '4px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <span>ID: {selectedThread.id}</span>
                  <span>•</span>
                  <span>{new Date(selectedThread.timestamp).toLocaleString()}</span>
                  <span>•</span>
                  <span className={`badge channel-${selectedThread.channel}`} style={{ textTransform: 'none' }}>
                    Origin: {getChannelLabel(selectedThread.channel)}
                  </span>
                </div>
              </div>
              <span className={`badge ${selectedThread.status}`}>
                {selectedThread.status}
              </span>
            </div>

            {/* Plain text bubbles - no markdown parsing in chat history */}
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
          <div className="thread-inspector-panel" style={{ padding: '24px 20px', borderLeft: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.01)' }}>
            
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
                <span>Source Channel</span>
                <span style={{ fontWeight: 600 }}>{getChannelLabel(selectedThread.channel)}</span>
              </div>
              <div className="metadata-row-item">
                <span>Detected Vibe</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Heart size={12} style={{ color: 'var(--accent-orange)' }} />
                  <span className={`badge emotion-${selectedThread.emotion}`} style={{ fontSize: '0.6rem', padding: '1px 4px' }}>{selectedThread.emotion}</span>
                </span>
              </div>
              <div className="metadata-row-item">
                <span>Topic Classification</span>
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
                <span style={{ color: 'var(--accent-orange)', fontWeight: 600 }}>Calculated Cost</span>
                <span style={{ color: 'var(--accent-orange)', fontWeight: 700 }}>${selectedThread.cost.toFixed(5)}</span>
              </div>
            </div>

            {/* Handoff Summary (Only if escalated) - PARSES MARKDOWN */}
            {selectedThread.status === "escalated" && (
              <div style={{ marginBottom: '24px', border: '1px solid rgba(220, 38, 38, 0.25)', borderRadius: '10px', padding: '14px', background: 'rgba(220, 38, 38, 0.02)' }}>
                <h4 className="metadata-section-title" style={{ color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                  <AlertTriangle size={14} /> Human Handoff Report
                </h4>
                <div className="handoff-summary-text">
                  <MarkdownText text={selectedThread.handoffSummary} />
                </div>
              </div>
            )}

            {/* Auditor Checklogs */}
            <div>
              <h4 className="metadata-section-title">Auditing Verifications</h4>
              <div className="audit-log-scroller">
                {selectedThread.failedChecks && selectedThread.failedChecks.length > 0 && (
                  <div className="audit-log-card failed-checks-card">
                    <div style={{ fontWeight: 'bold', color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
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
