import React, { useState, useMemo } from 'react';
import {
  Ticket,
  Phone,
  Clock,
  CheckCircle2,
  AlertCircle,
  UserCheck,
  TicketX,
  Search,
  Send,
  Sparkles,
  MessageSquare
} from 'lucide-react';

const STATUS_CONFIG = {
  open: {
    label: 'Open',
    color: 'var(--garnet)',
    bg: 'rgba(193, 73, 90, 0.12)',
    border: 'rgba(193, 73, 90, 0.3)',
    icon: AlertCircle
  },
  claimed: {
    label: 'Claimed',
    color: 'var(--amber)',
    bg: 'rgba(201, 154, 79, 0.12)',
    border: 'rgba(201, 154, 79, 0.3)',
    icon: UserCheck
  },
  resolved: {
    label: 'Resolved',
    color: 'var(--emerald)',
    bg: 'rgba(53, 161, 132, 0.12)',
    border: 'rgba(53, 161, 132, 0.3)',
    icon: CheckCircle2
  }
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open;
  const Icon = cfg.icon;
  return (
    <span
      className="status-tag"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
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

function ReasonBadge({ reason }) {
  if (!reason) return null;
  const labels = {
    customer_anger: "Customer Anger",
    react_failure: "System Error",
    direct_request: "Direct Request",
    user_stalling: "Customer Stalling",
    repeated_failure: "Repeated Failures",
  };
  const text = labels[reason] || reason;
  return (
    <span style={{
      fontSize: '0.72rem',
      fontWeight: 500,
      padding: '2px 8px',
      borderRadius: '3px',
      color: 'var(--text-2)',
      background: 'var(--surface-2)',
      border: '1px solid var(--hairline)',
      fontFamily: 'var(--font-body)'
    }}>
      {text}
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

export default function Tickets({ tickets = [], onResolve, onOpenConversation }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterTab, setFilterTab] = useState("all"); // 'all' | 'open' | 'claimed' | 'resolved'
  const [selectedTicketId, setSelectedTicketId] = useState(tickets[0]?.id || null);

  const openCount = tickets.filter(t => t.status === 'open').length;
  const claimedCount = tickets.filter(t => t.status === 'claimed').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;

  // Priority sort and filter
  const filteredTickets = useMemo(() => {
    return tickets
      .filter(t => {
        if (filterTab !== 'all' && t.status !== filterTab) return false;
        if (!searchTerm.trim()) return true;
        const q = searchTerm.toLowerCase();
        return (
          t.id.toString().includes(q) ||
          (t.customer_phone && t.customer_phone.toLowerCase().includes(q)) ||
          (t.summary && t.summary.toLowerCase().includes(q)) ||
          (t.reason && t.reason.toLowerCase().includes(q))
        );
      })
      .sort((a, b) => {
        const statusOrder = { open: 0, claimed: 1, resolved: 2 };
        const orderA = statusOrder[a.status] ?? 1;
        const orderB = statusOrder[b.status] ?? 1;
        if (orderA !== orderB) return orderA - orderB;
        return (b.urgency || 0) - (a.urgency || 0);
      });
  }, [tickets, filterTab, searchTerm]);

  const activeTicket = useMemo(() => {
    if (filteredTickets.length === 0) return null;
    const match = filteredTickets.find(t => t.id === selectedTicketId);
    return match || filteredTickets[0];
  }, [filteredTickets, selectedTicketId]);

  return (
    <div className="fade-in">

      {/* Summary KPI Strip — Topnote Pattern */}
      <div className="topnote">
        <div className="metric">
          <div className="label">Open Tickets</div>
          <div className="value" style={{ color: 'var(--garnet)' }}>{openCount}</div>
          <div className="sub">require human attention</div>
        </div>
        <div className="metric">
          <div className="label">Claimed</div>
          <div className="value" style={{ color: 'var(--amber)' }}>{claimedCount}</div>
          <div className="sub">agent assigned</div>
        </div>
        <div className="metric">
          <div className="label">Resolved</div>
          <div className="value" style={{ color: 'var(--emerald)' }}>{resolvedCount}</div>
          <div className="sub">successfully closed</div>
        </div>
        <div className="metric">
          <div className="label">Total Escalations</div>
          <div className="value">{tickets.length}</div>
          <div className="sub">all tickets logged</div>
        </div>
      </div>

      {/* List + Detail Dual-Pane Workspace */}
      <div className="ticket-workspace-layout">

        {/* Left Column: Ticket List Pane */}
        <div className="ticket-list-panel">
          
          {/* Search Box */}
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)' }} />
            <input 
              type="text" 
              placeholder="Search tickets..." 
              style={{ width: '100%', padding: '7px 12px 7px 32px', fontSize: '0.8rem' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Segmented Filter Tabs */}
          <div className="ticket-filter-tabs">
            {['all', 'open', 'claimed', 'resolved'].map(tab => (
              <button
                key={tab}
                className={`ticket-filter-tab ${filterTab === tab ? 'active' : ''}`}
                onClick={() => setFilterTab(tab)}
              >
                {tab === 'all' ? `All (${tickets.length})` : tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Scrollable Ticket List */}
          <div className="ticket-items-scroller">
            {filteredTickets.length === 0 ? (
              <div style={{ padding: '30px 10px', textAlign: 'center', color: 'var(--text-3)', fontSize: '0.82rem' }}>
                No tickets match search or filter.
              </div>
            ) : (
              filteredTickets.map(t => {
                const isActive = activeTicket?.id === t.id;
                let dotClass = 'low';
                if (t.urgency > 0.7) dotClass = 'high';
                else if (t.urgency > 0.4) dotClass = 'medium';

                return (
                  <div
                    key={t.id}
                    className={`ticket-list-item ${isActive ? 'active' : ''}`}
                    onClick={() => setSelectedTicketId(t.id)}
                  >
                    <div className="ticket-item-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <StatusBadge status={t.status} />
                        <span style={{ fontFamily: 'var(--font-data)', fontSize: '0.78rem', color: 'var(--text-1)', fontWeight: 600 }}>
                          #{t.id}
                        </span>
                      </div>
                      <span className={`urgency-dot ${dotClass}`} title={`Urgency: ${Math.round((t.urgency || 0) * 100)}%`} />
                    </div>

                    <div className="ticket-item-snippet">
                      {t.summary || 'No summary provided.'}
                    </div>

                    <div className="ticket-item-footer">
                      <span>{t.customer_phone || 'WhatsApp Client'}</span>
                      <span>{formatRelativeTime(t.created_at)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

        </div>

        {/* Right Column: Ticket Detail Pane */}
        {activeTicket ? (
          <div className="ticket-detail-pane">

            {/* Header: Title + Resolution Action */}
            <div className="ticket-detail-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h2 className="ticket-detail-title">
                  Ticket #{activeTicket.id}
                </h2>
                <StatusBadge status={activeTicket.status} />
              </div>

              {activeTicket.status === 'open' && onResolve && (
                <button
                  id={`resolve-ticket-${activeTicket.id}`}
                  onClick={() => onResolve(activeTicket.id)}
                  className="btn-gold"
                  style={{
                    borderColor: 'var(--emerald)',
                    color: 'var(--emerald)',
                    fontSize: '11px',
                    padding: '6px 14px'
                  }}
                >
                  Mark Resolved
                </button>
              )}
            </div>

            {/* Quiet Metadata Line */}
            <div className="ticket-meta-line">
              <span>
                <Phone size={12} style={{ color: 'var(--gold)' }} />
                {activeTicket.customer_phone}
              </span>
              <span>•</span>
              {activeTicket.conversation_id && (
                <>
                  <span>conv: {activeTicket.conversation_id}</span>
                  <span>•</span>
                </>
              )}
              <ReasonBadge reason={activeTicket.reason} />
              <span>•</span>
              <span>
                <Clock size={12} /> Opened {formatRelativeTime(activeTicket.created_at)}
              </span>
              {activeTicket.assigned_to && (
                <>
                  <span>•</span>
                  <span style={{ color: 'var(--gold)' }}>
                    <UserCheck size={12} /> Assigned to {activeTicket.assigned_to}
                  </span>
                </>
              )}
            </div>

            {/* Prominent Full Customer Issue Statement */}
            <div className="ticket-issue-heading">Customer Issue Statement</div>
            <div className="ticket-issue-body">
              {activeTicket.summary || 'No issue summary recorded for this escalation.'}
            </div>

            {/* AI Recommended Action Box */}
            {activeTicket.recommended_action && (
              <div className="ai-recommendation-box" style={{ marginBottom: '24px' }}>
                <span className="ai-recommendation-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={12} /> AI Recommended Action
                </span>
                {activeTicket.recommended_action}
              </div>
            )}

            {/* Bottom Action Bar: Open Conversation Link or Resolution Banner */}
            <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid var(--hairline)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {onOpenConversation && activeTicket.conversation_id && (
                <button
                  onClick={() => onOpenConversation(activeTicket.conversation_id)}
                  className="btn-gold"
                  style={{
                    width: '100%',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    fontSize: '0.85rem'
                  }}
                >
                  <MessageSquare size={14} />
                  <span>Open Conversation & Take Over in Client Conversations</span>
                </button>
              )}

              {activeTicket.status === 'resolved' && (
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--surface-2)',
                  border: '1px solid var(--hairline)',
                  borderRadius: '4px',
                  color: 'var(--emerald)',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontFamily: 'var(--font-body)'
                }}>
                  <CheckCircle2 size={14} />
                  <span>Ticket Resolved {activeTicket.resolved_at ? formatRelativeTime(activeTicket.resolved_at) : 'successfully'}.</span>
                </div>
              )}
            </div>

          </div>
        ) : (
          <div className="panel empty-state" style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)' }}>
            <TicketX size={36} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--text-1)', fontSize: '1.2rem', marginBottom: '4px' }}>No Escalation Selected</h2>
            <p style={{ fontSize: '0.85rem' }}>Select a ticket from the left panel to view full issue details and recommended actions.</p>
          </div>
        )}

      </div>
    </div>
  );
}
