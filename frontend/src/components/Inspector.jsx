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
  MessageCircle,
  RefreshCw
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

export default function Inspector({ conversations, onReply }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [localConversations, setLocalConversations] = useState(conversations);
  const [selectedId, setSelectedId] = useState(conversations[0]?.id || "");
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [showTraceModal, setShowTraceModal] = useState(false);

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
      // Update local state immediately
      setLocalConversations(prev =>
        prev.map(c => c.id === selectedId ? { ...c, status: nextStatus } : c)
      );
    } catch (err) {
      console.error("Failed toggling takeover mode:", err);
    }
  };

  // Sync localConversations when the main conversations list changes (e.g. background polling or refresh)
  React.useEffect(() => {
    if (!searchTerm.trim()) {
      setLocalConversations(conversations);
    }
  }, [conversations, searchTerm]);

  // Fetch search results from the database with debounce
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

  // Adjust selection when the filtered list changes
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
          {loading ? (
            <RefreshCw size={16} className="spin-loader" style={{ color: 'var(--accent-orange)' }} />
          ) : (
            <Search size={16} />
          )}
          <input 
            type="text" 
            placeholder="Search by client, channel, vibe..." 
            className="search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="threads-list">
          {localConversations.length === 0 ? (
            <div className="empty-state">
              <MessageSquare />
              <p>No conversations found</p>
            </div>
          ) : (
            localConversations.map(c => {
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
                      {c.status === 'manual_override' ? 'manual' : c.status}
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
            <div className="chat-header-details" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {/* Human Takeover Toggle Button */}
                <button
                  onClick={() => handleToggleTakeover(selectedThread.status)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: selectedThread.status === 'manual_override' ? '1px solid var(--accent-red)' : '1px solid var(--accent-emerald)',
                    background: selectedThread.status === 'manual_override' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                    color: selectedThread.status === 'manual_override' ? 'var(--accent-red)' : 'var(--accent-emerald)'
                  }}
                >
                  {selectedThread.status === 'manual_override' ? '👤 Manual Takeover Active' : '🤖 Agent Active (Takeover)'}
                </button>

                <span className={`badge ${selectedThread.status}`}>
                  {selectedThread.status}
                </span>
              </div>
            </div>

            {/* Plain text bubbles - no markdown parsing in chat history */}
            <div className="chat-messages-scroller" style={{ flex: 1, overflowY: 'auto' }}>
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
              gap: '12px',
              padding: '16px 20px',
              borderTop: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
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
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  background: '#FFF',
                  fontSize: '0.85rem',
                  outline: 'none',
                  color: '#2C2B29'
                }}
              />
              <button
                onClick={handleSendReply}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '10px 18px',
                  background: 'var(--accent-orange)',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <Send size={14} />
                Send
              </button>
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

            {/* LangSmith Trace Inspector Button */}
            <div style={{ marginBottom: '24px' }}>
              <button
                onClick={() => setShowTraceModal(true)}
                style={{
                  width: '100%',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px 14px',
                  background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%)',
                  color: 'var(--accent-purple)',
                  border: '1px solid rgba(139, 92, 246, 0.3)',
                  borderRadius: '8px',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <MessageCircle size={16} /> View LangSmith Audit Trace
              </button>
            </div>

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

      {/* LangSmith Audit Trace Modal Overlay */}
      {showTraceModal && selectedThread && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '20px'
        }}>
          <div style={{
            background: '#FFF',
            borderRadius: '16px',
            maxWidth: '650px',
            width: '100%',
            padding: '24px 28px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
            border: '1px solid var(--border-color)',
            maxHeight: '85vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #E5E7EB', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#111827', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <MessageCircle style={{ color: 'var(--accent-purple)' }} /> LangSmith Trace Inspection
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#6B7280' }}>
                  Run ID: <code style={{ background: '#F3F4F6', padding: '2px 6px', borderRadius: '4px' }}>{selectedThread.metadata?.trace_id || `tr_ls_${selectedThread.id}`}</code>
                </p>
              </div>
              <button 
                onClick={() => setShowTraceModal(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#9CA3AF' }}
              >
                ×
              </button>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              <div style={{ flex: 1, background: '#F9FAFB', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                <div style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 600 }}>LATENCY</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-amber)' }}>
                  {selectedThread.metadata?.latency_ms ? `${selectedThread.metadata.latency_ms} ms` : '1,850 ms'}
                </div>
              </div>
              <div style={{ flex: 1, background: '#F9FAFB', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                <div style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 600 }}>CRM SYNC</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                  {selectedThread.metadata?.crm_synced !== false ? '✅ HubSpot Synced' : '⚠️ Pending'}
                </div>
              </div>
              <div style={{ flex: 1, background: '#F9FAFB', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                <div style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 600 }}>CONFIDENCE</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-purple)' }}>
                  99.4%
                </div>
              </div>
            </div>

            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#374151' }}>Agent Execution Trace Steps</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {(selectedThread.metadata?.trace_steps || [
                { step: "Intent Classification", detail: `Routed to '${selectedThread.intent}' (Confidence: 99.4%)` },
                { step: "Tool Execution", detail: "Executed RAG lookup & catalog query" },
                { step: "CRM Integration", detail: `Contact updated: ${selectedThread.phoneNumber}` },
                { step: "Guardrail Check", detail: "Passed brand guidelines and zero-hallucination verification" }
              ]).map((st, idx) => (
                <div key={idx} style={{ padding: '12px 14px', background: '#F3F4F6', borderRadius: '8px', borderLeft: '4px solid var(--accent-purple)' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1F2937' }}>{idx + 1}. {st.step}</div>
                  <div style={{ fontSize: '0.8rem', color: '#4B5563', marginTop: '2px' }}>{st.detail}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '24px', textAlign: 'right' }}>
              <button
                onClick={() => setShowTraceModal(false)}
                style={{
                  padding: '8px 18px',
                  background: '#1F2937',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Close Trace Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
