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

  const kpis = [
    {
      title: "Clients Contacted",
      value: summary.totalClients,
      trend: "+12.5% vs yesterday",
      trendType: "up",
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
      value: summary.totalClients - Math.round(summary.totalClients * summary.successRate / 100),
      trend: `${summary.handoffRate}% handoff rate`,
      trendType: "down",
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
              <span>8</span>
              <span>6</span>
              <span>4</span>
              <span>2</span>
              <span>0</span>
            </div>
            <div className="bar-chart-body">
              {/* Mon */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '50%' }}>
                  <div className="bar-tooltip">Clients: 4</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '12%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 1</div>
                </div>
                <span className="chart-bar-label">Mon</span>
              </div>
              {/* Tue */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '75%' }}>
                  <div className="bar-tooltip">Clients: 6</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '25%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 2</div>
                </div>
                <span className="chart-bar-label">Tue</span>
              </div>
              {/* Wed */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '37%' }}>
                  <div className="bar-tooltip">Clients: 3</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '0%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 0</div>
                </div>
                <span className="chart-bar-label">Wed</span>
              </div>
              {/* Thu */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '62%' }}>
                  <div className="bar-tooltip">Clients: 5</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '12%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 1</div>
                </div>
                <span className="chart-bar-label">Thu</span>
              </div>
              {/* Fri */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '87%' }}>
                  <div className="bar-tooltip">Clients: 7</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '25%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 2</div>
                </div>
                <span className="chart-bar-label">Fri</span>
              </div>
              {/* Sat */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '100%' }}>
                  <div className="bar-tooltip">Clients: 8</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '12%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 1</div>
                </div>
                <span className="chart-bar-label">Sat</span>
              </div>
              {/* Sun */}
              <div className="bar-item-wrapper">
                <div className="chart-bar-pillar secondary" style={{ height: '87%' }}>
                  <div className="bar-tooltip">Clients: 7</div>
                </div>
                <div className="chart-bar-pillar" style={{ height: '37%' }}>
                  <div className="bar-tooltip" style={{ background: 'var(--accent-red)' }}>Handoffs: 3</div>
                </div>
                <span className="chart-bar-label">Sun</span>
              </div>
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
