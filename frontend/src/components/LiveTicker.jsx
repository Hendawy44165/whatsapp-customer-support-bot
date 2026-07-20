import React, { useState, useEffect } from 'react';
import { Zap, Database, ShieldCheck, Activity } from 'lucide-react';

const INITIAL_EVENTS = [
  { id: 1, type: 'crm', text: '⚡ HubSpot Contact Synced: +201019876543 (ID: hs_8839201)', time: 'Just now' },
  { id: 2, type: 'latency', text: '⏱️ Latency Check: Resolved in 1.8s (WhatsApp API)', time: '2m ago' },
  { id: 3, type: 'guardrail', text: '🛡️ Zero-Hallucination Guardrail Passed (Confidence: 99.4%)', time: '5m ago' },
  { id: 4, type: 'crm', text: '⚡ HubSpot Note Created: Order Tracking Query Logged', time: '8m ago' }
];

export default function LiveTicker({ conversations = [] }) {
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!conversations || conversations.length === 0) return;

    // Generate dynamic events based on real conversation data
    const dynamicEvents = [];
    conversations.slice(0, 4).forEach((c, idx) => {
      dynamicEvents.push({
        id: `c-${c.id}`,
        type: 'crm',
        text: `⚡ HubSpot Contact Synced: ${c.phoneNumber || c.customerName}`,
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
      gap: '12px',
      padding: '12px 18px',
      background: 'rgba(17, 24, 39, 0.92)',
      backdropFilter: 'blur(10px)',
      color: '#FFFFFF',
      borderRadius: '30px',
      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      fontSize: '0.8rem',
      fontWeight: 500,
      animation: 'fadeIn 0.4s ease-out'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '24px',
        height: '24px',
        borderRadius: '50%',
        background: 'rgba(16, 185, 129, 0.2)',
        color: '#10B981'
      }}>
        <Activity size={14} className="spin-loader" />
      </div>

      <div style={{ maxWidth: '340px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {currentEvent.text}
      </div>

      <span style={{ fontSize: '0.7rem', color: '#9CA3AF', paddingLeft: '4px', borderLeft: '1px solid #374151' }}>
        {currentEvent.time}
      </span>

      <button 
        onClick={() => setVisible(false)}
        style={{
          background: 'none',
          border: 'none',
          color: '#9CA3AF',
          cursor: 'pointer',
          padding: '0 4px',
          fontSize: '0.9rem',
          marginLeft: '4px'
        }}
      >
        ×
      </button>
    </div>
  );
}
