import React from 'react';
import { 
  Users, 
  UserCheck, 
  Coins, 
  Smile, 
  Activity, 
  TrendingDown
} from 'lucide-react';
import { getAnalyticsSummary, getEmotionDistribution } from '../mockData';

export default function Dashboard({ conversations }) {
  const summary = getAnalyticsSummary(conversations);
  const emotionCounts = getEmotionDistribution(conversations);

  // Group conversations by day of the week
  const dailyData = {
    Mon: { clients: 0, handoffs: 0 },
    Tue: { clients: 0, handoffs: 0 },
    Wed: { clients: 0, handoffs: 0 },
    Thu: { clients: 0, handoffs: 0 },
    Fri: { clients: 0, handoffs: 0 },
    Sat: { clients: 0, handoffs: 0 },
    Sun: { clients: 0, handoffs: 0 }
  };

  conversations.forEach(c => {
    if (!c.timestamp) return;
    const date = new Date(c.timestamp);
    const dayIndex = date.getDay(); // 0 = Sunday, 1 = Monday, etc.
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const dayName = dayNames[dayIndex];
    if (dailyData[dayName]) {
      dailyData[dayName].clients += 1;
      if (c.status === 'escalated') {
        dailyData[dayName].handoffs += 1;
      }
    }
  });

  const rawMax = Math.max(...Object.values(dailyData).map(d => d.clients));
  const maxVal = Math.max(4, Math.ceil(rawMax / 4) * 4);

  // Calculate trend dynamically for Clients Contacted (Today vs Yesterday relative to newest DB entry)
  let clientsTrend = "No comparison data";
  let clientsTrendType = "neutral";

  const timestamps = conversations.map(c => c.timestamp ? new Date(c.timestamp).getTime() : 0).filter(t => t > 0);
  const latestTime = timestamps.length > 0 ? Math.max(...timestamps) : Date.now();
  const oneDayMs = 24 * 60 * 60 * 1000;

  const last24hCount = conversations.filter(c => {
    if (!c.timestamp) return false;
    const diff = latestTime - new Date(c.timestamp).getTime();
    return diff >= 0 && diff <= oneDayMs;
  }).length;

  const prev24hCount = conversations.filter(c => {
    if (!c.timestamp) return false;
    const diff = latestTime - new Date(c.timestamp).getTime();
    return diff > oneDayMs && diff <= 2 * oneDayMs;
  }).length;

  if (prev24hCount > 0) {
    const pctChange = ((last24hCount - prev24hCount) / prev24hCount) * 100;
    const sign = pctChange >= 0 ? "+" : "";
    clientsTrend = `${sign}${pctChange.toFixed(1)}% vs yesterday`;
    clientsTrendType = pctChange >= 0 ? "up" : "down";
  } else if (last24hCount > 0) {
    clientsTrend = `+${last24hCount} new today`;
    clientsTrendType = "up";
  }

  const kpis = [
    {
      title: "Clients Contacted",
      value: summary.totalClients,
      trend: clientsTrend,
      trendType: clientsTrendType,
      icon: Users,
      color: "var(--accent-purple)"
    },
    {
      title: "Success Rate",
      value: `${summary.successRate}%`,
      trend: "Conversations resolved",
      trendType: "neutral",
      icon: UserCheck,
      color: "var(--accent-emerald)"
    },
    {
      title: "Human Escalations",
      value: conversations.filter(c => c.status === 'escalated').length,
      trend: `${summary.handoffRate}% handoff rate`,
      trendType: summary.handoffRate > 20 ? "down" : "neutral",
      icon: TrendingDown,
      color: "var(--accent-red)"
    },
    {
      title: "Average Cost / Client",
      value: `$${summary.avgCost.toFixed(5)}`,
      trend: "Combined prompt/completion",
      trendType: "neutral",
      icon: Coins,
      color: "var(--accent-orange)"
    }
  ];

  const tokenMetrics = [
    { label: "Avg Input Tokens / Client", value: summary.avgInputTokens.toLocaleString(), color: "var(--accent-purple)", unit: "tokens/client" },
    { label: "Avg Output Tokens / Client", value: summary.avgOutputTokens.toLocaleString(), color: "var(--accent-cyan)", unit: "tokens/client" },
    { label: "Purchase Closures (Sales)", value: `${summary.conversionRate}%`, color: "var(--accent-amber)", unit: "conversion rate" }
  ];

  // Colors mapping for emotions
  const emotionColors = {
    satisfied: "var(--accent-emerald)",
    calm: "var(--accent-blue)",
    neutral: "#686256",
    anxious: "var(--accent-amber)",
    frustrated: "var(--accent-red)",
    angry: "#ff003c"
  };

  const totalEmotions = Object.values(emotionCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="fade-in">
      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        {kpis.map((kpi, idx) => (
          <div key={idx} className="glass-panel kpi-card">
            <div className="kpi-header">
              <span className="kpi-title">{kpi.title}</span>
              <div className="kpi-icon-wrapper" style={{ color: kpi.color }}>
                <kpi.icon size={20} />
              </div>
            </div>
            <div className="kpi-value">{kpi.value}</div>
            <div className={`kpi-trend ${kpi.trendType}`}>
              {kpi.trend}
            </div>
          </div>
        ))}
      </div>

      {/* Analytics Breakdown Grid */}
      <div className="dashboard-charts-grid">
        
        {/* Weekly Traffic & Success Trends Chart */}
        <div className="glass-panel">
          <div className="chart-header">
            <div>
              <h2 className="chart-title">
                <Activity size={18} style={{ color: "var(--accent-orange)" }} />
                Conversational Trends
              </h2>
              <p className="chart-subtitle">Daily distribution of customer sessions and human escalations</p>
            </div>
            <span className="header-badge" style={{ color: "var(--accent-orange)" }}>
              Live Stats
            </span>
          </div>

          <div className="svg-chart-container" style={{ marginTop: '20px' }}>
            <div className="bar-chart-y-axis">
              <span>{maxVal}</span>
              <span>{maxVal * 3 / 4}</span>
              <span>{maxVal / 2}</span>
              <span>{maxVal / 4}</span>
              <span>0</span>
            </div>
            <div className="bar-chart-body">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => {
                const d = dailyData[day];
                const clientHeight = `${(d.clients / maxVal) * 100}%`;
                const handoffHeight = `${(d.handoffs / maxVal) * 100}%`;
                return (
                  <div className="bar-item-wrapper" key={day}>
                    <div className="chart-bar-pillar secondary" style={{ height: clientHeight }}>
                      <div className="bar-tooltip">Clients: {d.clients}</div>
                    </div>
                    <div className="chart-bar-pillar" style={{ height: handoffHeight }}>
                      <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: {d.handoffs}</div>
                    </div>
                    <span className="chart-bar-label">{day}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginTop: '20px', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#EADFC9', border: '1px solid #D5CEBF' }}></div>
              <span style={{ color: '#686256' }}>Total Clients Contacted</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'linear-gradient(to top, var(--accent-orange), var(--accent-amber))' }}></div>
              <span style={{ color: '#686256' }}>Human Handoff Escalations</span>
            </div>
          </div>
        </div>

        {/* Emotion Distribution */}
        <div className="glass-panel">
          <div className="chart-header">
            <div>
              <h2 className="chart-title">
                <Smile size={18} style={{ color: "var(--accent-purple)" }} />
                Customer Sentiment
              </h2>
              <p className="chart-subtitle">Distribution of customer emotional profiles</p>
            </div>
          </div>

          <div className="emotion-list-container">
            {Object.entries(emotionCounts).map(([emotion, count]) => {
              const pct = totalEmotions > 0 ? Math.round((count / totalEmotions) * 100) : 0;
              const color = emotionColors[emotion] || "#686256";
              return (
                <div className="emotion-row" key={emotion}>
                  <div className="emotion-meta">
                    <span className="emotion-dot" style={{ backgroundColor: color, boxShadow: `0 0 4px ${color}` }}></span>
                    <span style={{ textTransform: 'capitalize' }}>{emotion}</span>
                  </div>
                  <div className="emotion-progress-bg">
                    <div className="emotion-progress-fill" style={{ width: `${pct}%`, backgroundColor: color }}></div>
                  </div>
                  <span className="emotion-percent">{pct}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Average Token Details Section */}
      <div className="glass-panel">
        <h3 className="metadata-section-title" style={{ color: 'var(--accent-orange)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Coins size={16} /> Token Usage & Cost Per Client (Average)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          {tokenMetrics.map((tm, idx) => (
            <div key={idx} style={{ padding: '16px', background: '#FDFBF7', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '0.8rem', color: '#686256', fontWeight: 600 }}>{tm.label}</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '1.6rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: tm.color }}>{tm.value}</span>
                <span style={{ fontSize: '0.75rem', color: '#686256' }}>{tm.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
