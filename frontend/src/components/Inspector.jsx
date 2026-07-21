import React, { useState } from 'react';
import { 
  Search, 
  ShieldAlert, 
  Heart, 
  MessageSquare,
  AlertTriangle,
  Send,
  MessageCircle,
  RefreshCw,
  Sparkles
} from 'lucide-react';

// Custom lightweight Markdown renderer for client portal
function MarkdownText({ text }) {
  if (!text) return null;
  
  const lines = text.split('\n');
  
  return (
    <div className="markdown-content">
      {lines.map((line, idx) => {
        const listMatch = line.match(/^(\d+\.\s+|\*\s+|-+\s+)(.*)/);
        
        const renderLineContent = (content) => {
          const parts = content.split('**');
          return parts.map((part, i) => {
            if (i % 2 === 1) {
              return <strong key={i} style={{ color: 'var(--gold)' }}>{part}</strong>;
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
                color: 'var(--text-1)'
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
              color: 'var(--text-1)'
            }}
          >
            {renderLineContent(line)}
          </p>
        );
      })}
    </div>
  );
}

export default function Inspector({ conversations = [], tickets = [], selectedConversationId, onSelectConversation, onReply }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [localConversations, setLocalConversations] = useState(conversations);
  const [selectedId, setSelectedId] = useState(selectedConversationId || conversations[0]?.id || "");
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState("");

  React.useEffect(() => {
    if (selectedConversationId) {
      setSelectedId(selectedConversationId);
    }
  }, [selectedConversationId]);

  const handleSelectId = (id) => {
    setSelectedId(id);
    if (onSelectConversation) {
      onSelectConversation(id);
    }
  };

  const handleSendReply = async () => {
    if (!replyText.trim() || !onReply) return;
    await onReply(selectedId, replyText);
    setReplyText("");
  };

  const handleToggleTakeover = async (currentStatus) => {
    if (!selectedId) return;
    const nextStatus = currentStatus === 'manual_override' ? 'active' : 'manual_override';
    try {
      await fetch(`/api/conversations/${selectedId}/takeover`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      setLocalConversations(prev =>
        prev.map(c => c.id === selectedId ? { ...c, status: nextStatus } : c)
      );
    } catch (err) {
      console.error("Failed toggling takeover mode:", err);
    }
  };

  React.useEffect(() => {
    if (!searchTerm.trim()) {
      setLocalConversations(conversations);
    }
  }, [conversations, searchTerm]);

  React.useEffect(() => {
    if (!searchTerm.trim()) {
      setLocalConversations(conversations);
      return;
    }

    const fetchSearch = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/conversations?search=${encodeURIComponent(searchTerm)}`);
        if (res.ok) {
          const data = await res.json();
          setLocalConversations(data);
        }
      } catch (err) {
        console.error("Failed searching database:", err);
      } finally {
        setLoading(false);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      fetchSearch();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm, conversations]);

  React.useEffect(() => {
    if (localConversations.length > 0) {
      const exists = localConversations.some(c => c.id === selectedId);
      if (!exists) {
        setSelectedId(localConversations[0].id);
      }
    } else {
      setSelectedId("");
    }
  }, [localConversations, selectedId]);

  const selectedThread = localConversations.find(c => c.id === selectedId);

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
      <div className="panel threads-sidebar" style={{ padding: '16px' }}>
        <div style={{ position: 'relative' }}>
          {loading ? (
            <RefreshCw size={14} className="spin-loader" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--gold)' }} />
          ) : (
            <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)' }} />
          )}
          <input 
            type="text" 
            placeholder="Search by client, channel, vibe..." 
            style={{ width: '100%', padding: '8px 12px 8px 34px', fontSize: '0.82rem' }}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="threads-list">
          {localConversations.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-3)', fontSize: '0.85rem' }}>
              No conversations found
            </div>
          ) : (
            localConversations.map(c => {
              const lastMessage = c.messages[c.messages.length - 1]?.text || "";
              const isActive = c.id === selectedId;
              
              return (
                <div 
                  key={c.id} 
                  className={`thread-item ${isActive ? 'active' : ''}`}
                  onClick={() => handleSelectId(c.id)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="thread-client-name">{c.customerName}</span>
                    <span className="thread-time">
                      {new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  
                  <div className="thread-preview">{lastMessage}</div>
                  
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap', marginTop: '2px' }}>
                    <span className={`status-tag ${c.status === 'manual_override' ? 'claimed' : c.status === 'pending_handoff' ? 'escalated' : c.status}`}>
                      {c.status === 'manual_override' ? 'manual' : c.status === 'pending_handoff' ? 'escalated' : c.status}
                    </span>
                    <span style={{ fontSize: '10.5px', color: 'var(--text-3)', fontFamily: 'var(--font-body)' }}>
                      {getChannelLabel(c.channel)}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Details & Inspector Panels */}
      {selectedThread ? (
        <>
          {/* Chat Transcript pane */}
          <div className="chat-history-pane">
            <div className="chat-header-details">
              <div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', color: 'var(--text-1)', margin: 0 }}>
                  {selectedThread.customerName}
                </h3>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', marginTop: '2px', display: 'flex', gap: '10px', alignItems: 'center', fontFamily: 'var(--font-body)' }}>
                  <span>ID: {selectedThread.id}</span>
                  <span>•</span>
                  <span>{new Date(selectedThread.timestamp).toLocaleString()}</span>
                  <span>•</span>
                  <span>{getChannelLabel(selectedThread.channel)}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  onClick={() => handleToggleTakeover(selectedThread.status)}
                  className="btn-gold"
                  style={{
                    fontSize: '11px',
                    borderColor: selectedThread.status === 'manual_override' 
                      ? 'var(--garnet)' 
                      : (selectedThread.status === 'pending_handoff' || selectedThread.status === 'escalated')
                        ? 'var(--gold)'
                        : 'var(--emerald)',
                    color: selectedThread.status === 'manual_override' 
                      ? 'var(--garnet)' 
                      : (selectedThread.status === 'pending_handoff' || selectedThread.status === 'escalated')
                        ? 'var(--gold)'
                        : 'var(--emerald)'
                  }}
                >
                  {selectedThread.status === 'manual_override' 
                    ? 'Human Operator Active (Release)' 
                    : (selectedThread.status === 'pending_handoff' || selectedThread.status === 'escalated')
                      ? 'Take Over Conversation'
                      : selectedThread.status === 'resolved'
                        ? 'Reopen Conversation'
                        : 'AI Concierge Active (Takeover)'}
                </button>

                <span className={`status-tag ${selectedThread.status === 'manual_override' ? 'claimed' : selectedThread.status === 'pending_handoff' ? 'escalated' : selectedThread.status}`}>
                  {selectedThread.status === 'manual_override' ? 'manual' : selectedThread.status === 'pending_handoff' ? 'escalated' : selectedThread.status}
                </span>
              </div>
            </div>

            {/* Chat message bubbles */}
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

            {/* Chat Reply Input Bar */}
            <div style={{
              display: 'flex',
              gap: '10px',
              padding: '14px 20px',
              borderTop: '1px solid var(--hairline)',
              background: 'var(--surface-2)',
              alignItems: 'center'
            }}>
              <input
                type="text"
                placeholder="Type manual response to send..."
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSendReply();
                  }
                }}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  fontSize: '0.85rem'
                }}
              />
              <button
                onClick={handleSendReply}
                className="btn-primary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Send size={12} />
                <span>Send</span>
              </button>
            </div>
          </div>

          {/* Right Inspector Drawer (Metadata / Auditor Logs) */}
          <div className="thread-inspector-panel">
            
            {/* Client Profile */}
            <div>
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
                <span>{getChannelLabel(selectedThread.channel)}</span>
              </div>
              <div className="metadata-row-item">
                <span>Detected Vibe</span>
                <span style={{ color: 'var(--gold)', textTransform: 'capitalize' }}>
                  {selectedThread.emotion}
                </span>
              </div>
              <div className="metadata-row-item">
                <span>Topic Classification</span>
                <span>{selectedThread.intent}</span>
              </div>
            </div>

            {/* Token Analytics */}
            <div>
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
                <span style={{ color: 'var(--gold)' }}>Calculated Cost</span>
                <span style={{ color: 'var(--gold)' }}>${selectedThread.cost.toFixed(5)}</span>
              </div>
            </div>

            {/* Handoff Summary & Ticket Metadata */}
            {(() => {
              const matchingTicket = tickets.find(t => t.conversation_id === selectedThread.id);
              const hasReport = matchingTicket || selectedThread.handoffSummary || selectedThread.status === "escalated" || selectedThread.status === "pending_handoff" || selectedThread.status === "manual_override";
              if (!hasReport) return null;

              return (
                <div style={{ border: '1px solid rgba(193, 73, 90, 0.3)', borderRadius: '6px', padding: '14px', background: 'rgba(193, 73, 90, 0.06)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h4 className="metadata-section-title" style={{ color: 'var(--garnet)', display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
                      <AlertTriangle size={12} /> Human Handoff Report
                    </h4>
                    {matchingTicket && (
                      <span style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(193, 73, 90, 0.2)', color: 'var(--garnet)', borderRadius: '3px', fontWeight: 600 }}>
                        URGENCY: {Math.round((matchingTicket.urgency || 0.8) * 100)}%
                      </span>
                    )}
                  </div>

                  {matchingTicket?.reason && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--gold)', fontWeight: 600 }}>
                      Reason: {matchingTicket.reason}
                    </div>
                  )}

                  <div className="handoff-summary-text" style={{ fontSize: '0.8rem', color: 'var(--text-1)' }}>
                    <MarkdownText text={matchingTicket?.summary || selectedThread.handoffSummary || "Escalated to care team for human resolution."} />
                  </div>

                  {matchingTicket?.recommended_action && (
                    <div style={{ fontSize: '0.75rem', padding: '8px 10px', background: 'var(--surface-2)', border: '1px solid var(--hairline)', borderRadius: '4px', color: 'var(--text-2)' }}>
                      <div style={{ color: 'var(--gold)', fontWeight: 600, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Sparkles size={10} /> AI Recommended Action
                      </div>
                      {matchingTicket.recommended_action}
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Auditor Checklogs */}
            <div>
              <h4 className="metadata-section-title">Auditing Verifications</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedThread.failedChecks && selectedThread.failedChecks.length > 0 && (
                  <div style={{ padding: '8px 10px', background: 'rgba(193, 73, 90, 0.1)', border: '1px solid rgba(193, 73, 90, 0.3)', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--garnet)' }}>
                    <div style={{ fontWeight: '600', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ShieldAlert size={12} /> FAILED VIOLATION
                    </div>
                    {selectedThread.failedChecks.map((fc, i) => (
                      <div key={i}>• {fc}</div>
                    ))}
                  </div>
                )}
                {selectedThread.auditLogs.map((log, index) => (
                  <div key={index} style={{ padding: '8px 10px', background: 'var(--surface-2)', border: '1px solid var(--hairline)', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-2)', fontFamily: 'var(--font-data)' }}>
                    {log}
                  </div>
                ))}
              </div>
            </div>

          </div>
        </>
      ) : (
        <div className="panel empty-state" style={{ gridColumn: '2 / 4', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)' }}>
          <MessageSquare size={32} style={{ marginBottom: '12px', opacity: 0.5 }} />
          <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-1)', fontSize: '1.2rem', marginBottom: '4px' }}>No Conversation Selected</h2>
          <p style={{ fontSize: '0.85rem' }}>Select a thread from the sidebar to review logs and audit trace.</p>
        </div>
      )}
    </div>
  );
}
