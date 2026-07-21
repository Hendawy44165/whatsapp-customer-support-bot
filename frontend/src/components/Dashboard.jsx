import React from 'react';
import { getAnalyticsSummary, getEmotionDistribution } from '../mockData';

export default function Dashboard({ conversations }) {
  const summary = getAnalyticsSummary(conversations);
  const emotionCounts = getEmotionDistribution(conversations);

  // Group conversations by day of the week
  const dailyData = {
    MON: { clients: 0, handoffs: 0 },
    TUE: { clients: 0, handoffs: 0 },
    WED: { clients: 0, handoffs: 0 },
    THU: { clients: 0, handoffs: 0 },
    FRI: { clients: 0, handoffs: 0 },
    SAT: { clients: 0, handoffs: 0 },
    SUN: { clients: 0, handoffs: 0 }
  };

  conversations.forEach(c => {
    if (!c.timestamp) return;
    const date = new Date(c.timestamp);
    const dayIndex = date.getDay(); // 0 = Sunday, 1 = Monday, etc.
    const dayNames = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const dayName = dayNames[dayIndex];
    if (dailyData[dayName]) {
      dailyData[dayName].clients += 1;
      if (c.status === 'escalated' || c.status === 'pending_handoff') {
        dailyData[dayName].handoffs += 1;
      }
    }
  });

  const rawMax = Math.max(1, ...Object.values(dailyData).map(d => d.clients));

  // Sentiment calculation
  const totalEmotions = Object.values(emotionCounts).reduce((a, b) => a + b, 0) || 1;
  const satisfiedPct = Math.round(((emotionCounts.satisfied || 0) / totalEmotions) * 100);
  const neutralPct = Math.round(((emotionCounts.neutral || 0) / totalEmotions) * 100);
  const calmPct = Math.round(((emotionCounts.calm || 0) / totalEmotions) * 100);
  const anxiousPct = Math.round(((emotionCounts.anxious || 0) / totalEmotions) * 100);
  const frustratedPct = Math.round(((emotionCounts.frustrated || 0) / totalEmotions) * 100);
  const angryPct = Math.round(((emotionCounts.angry || 0) / totalEmotions) * 100);

  // Calculate weighted position marker (0% to 100% on spectrum)
  // Positive emotions (satisfied, calm) pull right; Negative (angry, frustrated, anxious) pull left
  const posWeight = (satisfiedPct * 1.0) + (calmPct * 0.8) + (neutralPct * 0.5);
  const markerPos = Math.min(95, Math.max(5, Math.round(posWeight)));

  return (
    <div className="fade-in">

      {/* TOP NOTE */}
      <div className="eyebrow">Top Note <small>— today's opening impression</small></div>
      <div className="topnote">
        <div className="metric">
          <div className="label">Deflection rate</div>
          <div className="value accent">{summary.deflectionRate || 70}%</div>
          <div className="sub">handled without a human</div>
        </div>
        <div className="metric">
          <div className="label">Avg response latency</div>
          <div className="value">{summary.avgLatencySec || '1.8'}s</div>
          <div className="sub">first-token to reply</div>
        </div>
        <div className="metric">
          <div className="label">Est. payroll saved</div>
          <div className="value">
            {summary.egpPayrollSaved ? summary.egpPayrollSaved.toLocaleString() : '650'} <span style={{ fontSize: '20px', color: 'var(--text-2)' }}>EGP</span>
          </div>
          <div className="sub">today, vs. staffed equivalent</div>
        </div>
        <div className="metric">
          <div className="label">CRM sync rate</div>
          <div className="value">100%</div>
          <div className="sub">all sessions reconciled</div>
        </div>
      </div>

      {/* HEART NOTE */}
      <div className="eyebrow">Heart Note <small>— how the day is developing</small></div>
      <div className="heartnote">
        
        {/* Conversational Trends */}
        <div className="panel">
          <h3>Conversational Trends</h3>
          <div className="desc">Clients contacted vs. human handoffs, by day</div>
          <div className="chart">
            {Object.entries(dailyData).map(([day, d]) => {
              const totalH = Math.max(4, Math.round((d.clients / rawMax) * 100));
              const escH = Math.round((d.handoffs / rawMax) * 100);
              return (
                <div className="chartcol" key={day}>
                  <div className="bars">
                    <div className="bar total" style={{ height: `${totalH}%` }} title={`Clients: ${d.clients}`}></div>
                    {d.handoffs > 0 && (
                      <div className="bar esc" style={{ height: `${escH}%` }} title={`Handoffs: ${d.handoffs}`}></div>
                    )}
                  </div>
                  <div className="daylabel">{day}</div>
                </div>
              );
            })}
          </div>
          <div className="legend">
            <span><span className="swatch" style={{ background: 'var(--gold-dark)' }}></span>Total clients contacted</span>
            <span><span className="swatch" style={{ background: 'var(--forest)' }}></span>Human handoff escalations</span>
          </div>
        </div>

        {/* Customer Sentiment */}
        <div className="panel">
          <h3>Customer Sentiment</h3>
          <div className="desc">Weighted emotional read, negative to positive</div>
          <div className="spectrum-wrap">
            <div className="spectrum">
              <div className="marker" style={{ left: `${markerPos}%` }}></div>
            </div>
            <div className="spectrum-labels">
              <span>NEGATIVE</span>
              <span>NEUTRAL</span>
              <span>POSITIVE</span>
            </div>
          </div>
          <div className="sentirow"><span className="name">Satisfied</span><span className="pct">{satisfiedPct}%</span></div>
          <div className="sentirow"><span className="name">Neutral</span><span className="pct">{neutralPct}%</span></div>
          <div className="sentirow"><span className="name">Calm</span><span className="pct">{calmPct}%</span></div>
          <div className="sentirow"><span className="name">Anxious</span><span className="pct">{anxiousPct}%</span></div>
          <div className="sentirow"><span className="name">Frustrated</span><span className="pct">{frustratedPct}%</span></div>
          <div className="sentirow"><span className="name">Angry</span><span className="pct">{angryPct}%</span></div>
        </div>

      </div>

      {/* BASE NOTE */}
      <div className="eyebrow">Base Note <small>— what the day settles into</small></div>
      <div className="basenote">
        <div className="basecard">
          <div className="label">Avg input tokens / client</div>
          <div className="value">{summary.avgInputTokens.toLocaleString()}</div>
          <div className="foot">across {summary.totalClients} clients contacted today</div>
        </div>
        <div className="basecard">
          <div className="label">Avg output tokens / client</div>
          <div className="value">{summary.avgOutputTokens.toLocaleString()}</div>
          <div className="foot">concierge reply volume</div>
        </div>
        <div className="basecard">
          <div className="label">Purchase closures</div>
          <div className="value gold">{summary.conversionRate}%</div>
          <div className="foot">conversion to a completed sale</div>
          <div className="costnote">
            <span>AI compute cost / client</span>
            <span>${(summary.avgCost || 0.00059).toFixed(5)}</span>
          </div>
        </div>
      </div>

    </div>
  );
}
