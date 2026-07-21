import React, { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';

const INITIAL_EVENTS = [
  { id: 1, type: 'crm', text: 'HubSpot Contact Synced: +201019876543 (ID: hs_8839201)', time: 'Just now' },
  { id: 2, type: 'latency', text: 'Latency Check: Resolved in 1.8s (WhatsApp API)', time: '2m ago' },
  { id: 3, type: 'guardrail', text: 'Zero-Hallucination Guardrail Passed (Confidence: 99.4%)', time: '5m ago' },
  { id: 4, type: 'crm', text: 'HubSpot Note Created: Order Tracking Query Logged', time: '8m ago' }
];

export default function LiveTicker({ conversations = [] }) {
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!conversations || conversations.length === 0) return;

    const dynamicEvents = [];
    conversations.slice(0, 4).forEach((c, idx) => {
      dynamicEvents.push({
        id: `c-${c.id}`,
        type: 'crm',
        text: `HubSpot Contact Synced: ${c.phoneNumber || c.customerName}`,
        time: `${(idx + 1) * 3}m ago`
      });
    });

    if (dynamicEvents.length > 0) {
      setEvents(dynamicEvents);
    }
  }, [conversations]);

  if (!visible || events.length === 0) return null;

  const currentEvent = events[0];

  return (
    <div style={{
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: 999,
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      padding: '10px 16px',
      background: 'var(--surface)',
      color: 'var(--text-1)',
      borderRadius: '4px',
      border: '1px solid var(--hairline-strong)',
      fontSize: '0.78rem',
      fontFamily: 'var(--font-body)',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '18px',
        height: '18px',
        borderRadius: '50%',
        background: 'rgba(53, 161, 132, 0.15)',
        color: 'var(--emerald)'
      }}>
        <Activity size={11} className="spin-loader" />
      </div>

      <div style={{ maxWidth: '320px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {currentEvent.text}
      </div>

      <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', paddingLeft: '4px', borderLeft: '1px solid var(--hairline)' }}>
        {currentEvent.time}
      </span>

      <button 
        onClick={() => setVisible(false)}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--text-3)',
          cursor: 'pointer',
          padding: '0 2px',
          fontSize: '0.9rem',
          marginLeft: '4px'
        }}
      >
        ×
      </button>
    </div>
  );
}
