import React from 'react';
import {
  Ticket,
  Phone,
  Clock,
  CheckCircle2,
  AlertCircle,
  UserCheck,
  TicketX
} from 'lucide-react';

// Status badge config
const STATUS_CONFIG = {
  open: {
    label: 'Open',
    color: 'var(--accent-red)',
    bg: 'rgba(220, 38, 38, 0.08)',
    border: 'rgba(220, 38, 38, 0.2)',
    icon: AlertCircle
  },
  claimed: {
    label: 'Claimed',
    color: 'var(--accent-amber)',
    bg: 'rgba(217, 119, 6, 0.08)',
    border: 'rgba(217, 119, 6, 0.2)',
    icon: UserCheck
  },
  resolved: {
    label: 'Resolved',
    color: 'var(--accent-emerald)',
    bg: 'rgba(21, 128, 61, 0.08)',
    border: 'rgba(21, 128, 61, 0.2)',
    icon: CheckCircle2
  }
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open;
  const Icon = cfg.icon;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: '0.65rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.6px',
        padding: '3px 8px',
        borderRadius: '4px',
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`
      }}
    >
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function Tickets({ tickets = [], onResolve, onReply }) {
  const openCount = tickets.filter(t => t.status === 'open').length;
  const claimedCount = tickets.filter(t => t.status === 'claimed').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;

  return (
    <div className="fade-in">

      {/* Summary KPI strip */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: '24px' }}>
        <div className="glass-panel kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Open Tickets</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-red)' }}>
              <AlertCircle size={20} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>{openCount}</div>
          <div className="kpi-trend down">Require human attention</div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Claimed</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-amber)' }}>
              <UserCheck size={20} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>{claimedCount}</div>
          <div className="kpi-trend neutral">Agent assigned</div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Resolved</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-emerald)' }}>
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-emerald)' }}>{resolvedCount}</div>
          <div className="kpi-trend up">Successfully closed</div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Total Tickets</span>
            <div className="kpi-icon-wrapper" style={{ color: 'var(--accent-purple)' }}>
              <Ticket size={20} />
            </div>
          </div>
          <div className="kpi-value">{tickets.length}</div>
          <div className="kpi-trend neutral">All escalations</div>
        </div>
      </div>

      {/* Ticket list panel */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Panel header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
            borderRadius: '16px 16px 0 0'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Ticket size={18} style={{ color: 'var(--accent-orange)' }} />
            <h2
              className="chart-title"
              style={{ margin: 0, fontSize: '1rem' }}
            >
              Escalation Tickets
            </h2>
          </div>
          {openCount > 0 && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                background: 'rgba(220, 38, 38, 0.08)',
                color: 'var(--accent-red)',
                border: '1px solid rgba(220, 38, 38, 0.2)',
                padding: '4px 10px',
                borderRadius: '12px'
              }}
            >
              {openCount} need attention
            </span>
          )}
        </div>

        {/* Empty state */}
        {tickets.length === 0 ? (
          <div className="empty-state" style={{ padding: '80px 24px' }}>
            <TicketX />
            <h2 style={{ fontSize: '1.1rem', marginBottom: '8px', color: '#382F2D' }}>
              No Escalation Tickets
            </h2>
            <p style={{ fontSize: '0.85rem' }}>
              When the AI escalates a conversation to a human agent, tickets will appear here.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {tickets.map((ticket, index) => (
              <TicketRow
                key={ticket.id}
                ticket={ticket}
                onResolve={onResolve}
                onReply={onReply}
                isLast={index === tickets.length - 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UrgencyBar({ urgency }) {
  if (urgency === null || urgency === undefined) return null;
  const val = Math.round(urgency * 100);
  let color = 'var(--accent-emerald)';
  if (urgency > 0.7) color = 'var(--accent-red)';
  else if (urgency > 0.4) color = 'var(--accent-amber)';

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', minWidth: '110px' }}>
      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#686256' }}>Urgency:</span>
      <div style={{ flex: 1, width: '60px', height: '6px', background: 'rgba(0,0,0,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${val}%`, height: '100%', background: color, borderRadius: '3px' }}></div>
      </div>
      <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#686256' }}>{val}%</span>
    </div>
  );
}

function ReasonBadge({ reason }) {
  if (!reason) return null;
  const labels = {
    customer_anger: { text: "Customer Anger 😡", color: "var(--accent-red)", bg: "rgba(220, 38, 38, 0.06)" },
    react_failure: { text: "System Error 🤖❌", color: "var(--accent-purple)", bg: "rgba(147, 51, 234, 0.06)" },
    direct_request: { text: "Direct Request 🙋", color: "var(--accent-blue)", bg: "rgba(37, 99, 235, 0.06)" },
    user_stalling: { text: "Customer Stalling ⏳", color: "var(--accent-amber)", bg: "rgba(217, 119, 6, 0.06)" },
    repeated_failure: { text: "Repeated Failures 🔄", color: "var(--accent-orange)", bg: "rgba(234, 88, 12, 0.06)" },
  };
  const cfg = labels[reason] || { text: reason, color: "#686256", bg: "rgba(0,0,0,0.04)" };
  return (
    <span style={{
      fontSize: '0.68rem',
      fontWeight: 700,
      padding: '2px 8px',
      borderRadius: '4px',
      color: cfg.color,
      background: cfg.bg,
      border: `1px solid ${cfg.color}1c`
    }}>
      {cfg.text}
    </span>
  );
}

const parseMetadata = (meta) => {
  if (!meta) return {};
  if (typeof meta === 'object') return meta;
  try {
    return JSON.parse(meta);
  } catch (e) {
    return {};
  }
};

function TicketRow({ ticket, onResolve, onReply, isLast }) {
  const isOpen = ticket.status === 'open';
  const [replyText, setReplyText] = React.useState("");
  const [sending, setSending] = React.useState(false);
  const [sentSuccess, setSentSuccess] = React.useState(false);

  const handleSendReply = async () => {
    if (!replyText.trim() || !onReply) return;
    setSending(true);
    try {
      await onReply(ticket.conversation_id, replyText);
      setReplyText("");
      setSentSuccess(true);
      setTimeout(() => setSentSuccess(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  const metadata = parseMetadata(ticket.metadata);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        alignItems: 'start',
        gap: '16px',
        padding: '20px 24px',
        borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
        background: isOpen ? 'rgba(220, 38, 38, 0.015)' : 'transparent',
        transition: 'background 0.2s ease'
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = isOpen
          ? 'rgba(220, 38, 38, 0.03)'
          : 'rgba(0, 0, 0, 0.015)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = isOpen
          ? 'rgba(220, 38, 38, 0.015)'
          : 'transparent';
      }}
    >
      {/* Left: ticket body */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: 0 }}>
        {/* Row 1: badge + id + phone + reason + urgency */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <StatusBadge status={ticket.status} />
          <span
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: '#686256',
              letterSpacing: '0.5px'
            }}
          >
            #{ticket.id}
          </span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
              color: '#382F2D'
            }}
          >
            <Phone size={12} style={{ color: 'var(--accent-orange)' }} />
            {ticket.customer_phone}
          </span>
          {ticket.conversation_id && (
            <span
              style={{
                fontSize: '0.7rem',
                color: '#686256',
                background: 'rgba(0,0,0,0.04)',
                padding: '2px 6px',
                borderRadius: '4px',
                border: '1px solid var(--border-color)',
                fontFamily: 'monospace'
              }}
            >
              conv: {ticket.conversation_id}
            </span>
          )}

          <ReasonBadge reason={ticket.reason} />
          <UrgencyBar urgency={ticket.urgency} />
        </div>

        {/* Row 2: summary */}
        <p
          style={{
            fontSize: '0.875rem',
            color: '#2C2B29',
            lineHeight: 1.55,
            margin: 0,
            paddingLeft: '2px'
          }}
        >
          {ticket.summary || <em style={{ color: '#686256' }}>No summary provided.</em>}
        </p>

        {/* Row 2.5: AI Recommended Action */}
        {ticket.recommended_action && (
          <div style={{
            marginTop: '6px',
            padding: '10px 14px',
            background: 'rgba(217, 119, 6, 0.02)',
            borderLeft: '3px solid var(--accent-amber)',
            borderRadius: '0 8px 8px 0',
            fontSize: '0.8rem',
            lineHeight: '1.45',
            color: '#4B3F2F'
          }}>
            <strong style={{ color: 'var(--accent-amber)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>AI Recommended Action</strong>
            {ticket.recommended_action}
          </div>
        )}

        {/* Row 2.7: Metadata tags */}
        {Object.keys(metadata).length > 0 && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
            {Object.entries(metadata).map(([k, v]) => {
              if (v === null || v === undefined || (typeof v === 'object' && Object.keys(v).length === 0) || (Array.isArray(v) && v.length === 0)) return null;
              return (
                <span key={k} style={{
                  fontSize: '0.7rem',
                  color: '#686256',
                  background: 'rgba(0,0,0,0.03)',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)'
                }}>
                  <strong style={{ textTransform: 'capitalize' }}>{k.replace('_', ' ')}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </span>
              );
            })}
          </div>
        )}

        {/* Row 3: meta footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap'
          }}
        >
          {/* Created timestamp */}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.72rem',
              color: '#686256'
            }}
          >
            <Clock size={11} />
            Opened {formatRelativeTime(ticket.created_at)}
          </span>

          {/* Assigned to */}
          {ticket.assigned_to && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.72rem',
                color: 'var(--accent-amber)',
                fontWeight: 600
              }}
            >
              <UserCheck size={11} />
              {ticket.assigned_to}
            </span>
          )}

          {/* Resolved timestamp */}
          {ticket.resolved_at && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.72rem',
                color: 'var(--accent-emerald)',
                fontWeight: 600
              }}
            >
              <CheckCircle2 size={11} />
              Resolved {formatRelativeTime(ticket.resolved_at)}
            </span>
          )}
        </div>

        {/* Quick Reply Form for Open tickets */}
        {isOpen && (
          <div style={{
            marginTop: '12px',
            display: 'flex',
            gap: '10px',
            alignItems: 'center',
            background: 'rgba(0,0,0,0.01)',
            padding: '10px 14px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            maxWidth: '500px'
          }}>
            <input
              type="text"
              placeholder={sentSuccess ? "Message sent successfully!" : "Type quick response to customer..."}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSendReply();
                }
              }}
              disabled={sending}
              style={{
                flex: 1,
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                fontSize: '0.8rem',
                outline: 'none',
                background: sentSuccess ? 'rgba(21, 128, 61, 0.05)' : '#FFF',
                color: sentSuccess ? 'var(--accent-emerald)' : '#2C2B29'
              }}
            />
            <button
              onClick={handleSendReply}
              disabled={sending || !replyText.trim()}
              style={{
                padding: '6px 12px',
                background: 'var(--accent-orange)',
                color: '#FFF',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                opacity: (sending || !replyText.trim()) ? 0.6 : 1
              }}
            >
              Reply
            </button>
          </div>
        )}
      </div>

      {/* Right: action button (only for open tickets) */}
      {isOpen && onResolve && (
        <button
          id={`resolve-ticket-${ticket.id}`}
          onClick={() => onResolve(ticket.id)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            background: 'rgba(21, 128, 61, 0.06)',
            color: 'var(--accent-emerald)',
            border: '1px solid rgba(21, 128, 61, 0.2)',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
            flexShrink: 0
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(21, 128, 61, 0.12)';
            e.currentTarget.style.borderColor = 'rgba(21, 128, 61, 0.35)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(21, 128, 61, 0.06)';
            e.currentTarget.style.borderColor = 'rgba(21, 128, 61, 0.2)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          <CheckCircle2 size={14} />
          Mark Resolved
        </button>
      )}
    </div>
  );
}
