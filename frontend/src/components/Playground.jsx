import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Terminal, 
  Sparkles, 
  User, 
  Cpu, 
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  ChevronDown,
  RefreshCw
} from 'lucide-react';

export default function Playground({ onNewSession }) {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I am the Nuit Fragrances AI Support Concierge. You can ask me to track your order (e.g., NUIT-1002), query policies, or check perfume specs. How can I help you?", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId] = useState(`playground-${Math.random().toString(36).substring(7)}`);
  
  // LangGraph node state
  // classifier, analyze_emotion, enhance_prompt, generate, run_audits, iteration_enhancer, quick_fixer, handoff, save_history, direct_response
  const [graphNodes, setGraphNodes] = useState([
    { id: 'classifier', name: 'Classifier Node', status: 'idle', desc: 'Classifies prompt intent category' },
    { id: 'direct_response', name: 'Direct Response Node', status: 'idle', desc: 'Responds immediately for greetings' },
    { id: 'analyze_emotion', name: 'Emotion Analyzer', status: 'idle', desc: 'Extracts buyer vibe & intents' },
    { id: 'enhance_prompt', name: 'Enhance Prompt', status: 'idle', desc: 'Merges prompt templates & RAG context' },
    { id: 'generate', name: 'Generator Node', status: 'idle', desc: 'Queries model for response candidate' },
    { id: 'run_audits', name: 'Auditor Node', status: 'idle', desc: 'Validates safety, brands, and facts' },
    { id: 'handoff', name: 'Human Handoff Node', status: 'idle', desc: 'Escalates session & builds handoff summary' },
    { id: 'save_history', name: 'Save History Node', status: 'idle', desc: 'Appends turn to session storage' }
  ]);

  const [activeNode, setActiveNode] = useState(null);
  const [sentimentResult, setSentimentResult] = useState(null);
  const [auditReport, setAuditReport] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Test backend connection
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const res = await fetch('/api/documents');
        setIsConnected(res.ok);
      } catch (err) {
        setIsConnected(false);
      }
    };
    checkConnection();
  }, []);

  const updateNodeStatus = (nodeId, status) => {
    setGraphNodes(prev => prev.map(n => n.id === nodeId ? { ...n, status } : n));
  };

  const resetNodes = () => {
    setGraphNodes(prev => prev.map(n => ({ ...n, status: 'idle' })));
    setActiveNode(null);
    setSentimentResult(null);
    setAuditReport([]);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    
    // Add user message to UI
    setMessages(prev => [...prev, {
      sender: 'user',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    setLoading(true);
    resetNodes();

    // Start LangGraph pipeline simulation
    // Step 1: Classifier
    updateNodeStatus('classifier', 'active');
    setActiveNode('classifier');
    await new Promise(r => setTimeout(r, 600));
    updateNodeStatus('classifier', 'completed');

    const lowerText = userText.toLowerCase();
    const isGreeting = lowerText.includes("hi") || lowerText.includes("hello") || lowerText.includes("hey");
    const isOrder = lowerText.includes("order") || lowerText.includes("track") || lowerText.includes("nuit-");
    const isEscalation = lowerText.includes("human") || lowerText.includes("manager") || lowerText.includes("stupid") || lowerText.includes("scam") || lowerText.includes("refund");

    if (isGreeting && !isOrder && !isEscalation) {
      // Greetings path: Classifier -> Direct Response
      updateNodeStatus('direct_response', 'active');
      setActiveNode('direct_response');
      await new Promise(r => setTimeout(r, 600));
      updateNodeStatus('direct_response', 'completed');
      
      const botResponse = await getBotReply(userText, false);
      addBotMessage(botResponse);
    } else {
      // Complex path: Classifier -> Analyze Emotion
      updateNodeStatus('analyze_emotion', 'active');
      setActiveNode('analyze_emotion');
      
      // Determine vibe mock result
      let vibe = "calm";
      let intent = "browsing";
      if (isEscalation) {
        vibe = "frustrated";
        intent = "complaining";
      } else if (isOrder) {
        vibe = "neutral";
        intent = "searching";
      }
      setSentimentResult({ vibe, intent });
      
      await new Promise(r => setTimeout(r, 500));
      updateNodeStatus('analyze_emotion', 'completed');

      // Step 3: Enhance Prompt
      updateNodeStatus('enhance_prompt', 'active');
      setActiveNode('enhance_prompt');
      await new Promise(r => setTimeout(r, 400));
      updateNodeStatus('enhance_prompt', 'completed');

      // Step 4: Generate
      updateNodeStatus('generate', 'active');
      setActiveNode('generate');
      await new Promise(r => setTimeout(r, 700));
      updateNodeStatus('generate', 'completed');

      // Step 5: Run Audits
      updateNodeStatus('run_audits', 'active');
      setActiveNode('run_audits');
      
      const reports = [
        "Brand Compliance: PASSED",
        "Fact Checker: PASSED",
        "Prompt Guardrail: PASSED"
      ];
      if (isEscalation) {
        reports[2] = "Security Compliance: Warning (Bypassed to handoff)";
      }
      setAuditReport(reports);
      
      await new Promise(r => setTimeout(r, 600));
      updateNodeStatus('run_audits', 'completed');

      // Router Step: Handoff or Save History
      if (isEscalation) {
        updateNodeStatus('handoff', 'active');
        setActiveNode('handoff');
        await new Promise(r => setTimeout(r, 500));
        updateNodeStatus('handoff', 'completed');
        
        const botResponse = await getBotReply(userText, true);
        addBotMessage(botResponse);
        
        // Add to aggregate list
        triggerNewMockSession(userText, botResponse, "escalated", vibe, intent);
      } else {
        updateNodeStatus('save_history', 'active');
        setActiveNode('save_history');
        await new Promise(r => setTimeout(r, 400));
        updateNodeStatus('save_history', 'completed');
        
        const botResponse = await getBotReply(userText, false);
        addBotMessage(botResponse);
        
        triggerNewMockSession(userText, botResponse, isOrder ? "resolved" : "resolved", vibe, intent);
      }
    }

    setLoading(false);
    setActiveNode(null);
  };

  const addBotMessage = (text) => {
    setMessages(prev => [...prev, {
      sender: 'bot',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  // Bot API communicator with static fallback
  const getBotReply = async (userText, isHandoffForced) => {
    if (isConnected) {
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userText, thread_id: threadId })
        });
        if (res.ok) {
          const data = await res.json();
          return data.response;
        }
      } catch (err) {
        console.warn("FastAPI chat request failed. Running local fallback.");
      }
    }

    // Mock response simulation
    const lower = userText.toLowerCase();
    if (isHandoffForced) {
      return "I want to ensure you receive completely accurate details on that matter. Let me verify our specific inventory files or connect you directly with a specialist from our care team. May I please have your phone number to look up your order profile?";
    }
    if (lower.includes("nuit-1001")) {
      return "Order NUIT-1001 status is: DELIVERED.\n- Customer: John Doe\n- Items: Signature EDP 50ml\n- Carrier: Aramex\n- Tracking ID: AX-998273-EG\n- Estimated Delivery: Completed on May 28, 2026";
    }
    if (lower.includes("nuit-1002")) {
      return "Order NUIT-1002 status is: SHIPPED.\n- Customer: Sarah Ahmed\n- Items: Discovery Box trial bundle\n- Carrier: Bosta\n- Tracking ID: BS-112233-EG\n- Estimated Delivery: June 4, 2026 (In Transit)";
    }
    if (lower.includes("nuit-1003")) {
      return "Order NUIT-1003 status is: PROCESSING.\n- Customer: Sherif Mahmoud\n- Items: Discovery Box trial bundle, Signature EDP 50ml\n- Carrier: Bosta\n- Tracking ID: BS-445566-EG\n- Estimated Delivery: June 6, 2026 (Processing in Warehouse)";
    }
    if (lower.includes("order") || lower.includes("track")) {
      return "I'd be glad to look up that shipment for you! Could you please provide your Order ID (e.g. NUIT-1002) or the phone number you used to place the order?";
    }
    if (lower.includes("discovery box") || lower.includes("price") || lower.includes("how much")) {
      return "Our Discovery Box trial bundle features 3ml sprays of our top three luxury scents (Signature, Oud Royale, Noir Intense) for 450 EGP with free shipping. Best of all, it comes with a 450 EGP discount coupon for your next full-size bottle purchase! Try it at: `nuitfragrances.com/checkout/discovery-box`.";
    }
    
    return "Hi there! I am processing your query under our Nuit concierge framework. Let me know if you would like me to lookup order details or help you explore our product catalog!";
  };

  // Push new conversation to dashboard mock state
  const triggerNewMockSession = (userText, botResponse, status, vibe, intent) => {
    const inputLen = userText.length * 0.7; // rough approximation
    const outputLen = botResponse.length * 0.7;
    const inputTokens = Math.round(100 + inputLen);
    const outputTokens = Math.round(50 + outputLen);
    const cost = (inputTokens * 0.00000015) + (outputTokens * 0.00000060);

    const newThread = {
      id: `thread-${Math.random().toString(36).substring(4, 9)}`,
      customerName: "Anonymous Tester",
      phoneNumber: "+201009998887",
      status,
      emotion: vibe,
      intent,
      timestamp: new Date().toISOString(),
      tokens: { input: inputTokens, output: outputTokens },
      cost,
      messages: [
        { sender: 'user', text: userText, timestamp: new Date().toLocaleTimeString() },
        { sender: 'bot', text: botResponse, timestamp: new Date().toLocaleTimeString() }
      ],
      auditLogs: [
        `Classifier: routed to ${intent}`,
        `Emotion Analyzer: vibe=${vibe}, intent=${intent}`,
        "Auditor: Fact/Brand audits PASSED"
      ],
      failedChecks: status === "escalated" ? ["Interactive bypass triggered"] : [],
      handoffSummary: status === "escalated" ? `1. **Customer Intent**: Requested supervisor support.\n2. **Actions Attempted**: Answered playground test interface.\n3. **Reason for Handoff**: Escalation test input registered.` : ""
    };

    onNewSession(newThread);
  };

  return (
    <div className="playground-layout fade-in">
      
      {/* Interactive Chat Console */}
      <div className="glass-panel chat-terminal" style={{ padding: 0 }}>
        <div className="chat-header-details" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Terminal size={16} style={{ color: 'var(--accent-purple)' }} />
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '0.95rem', fontWeight: 600 }}>
              AI Concierge Terminal
            </h3>
          </div>
          <span className={`header-badge ${isConnected ? '' : 'offline'}`} style={{ color: isConnected ? 'var(--accent-emerald)' : 'var(--accent-red)' }}>
            {isConnected ? 'Backend Connected' : 'Simulating Local Agent'}
          </span>
        </div>

        <div className="chat-messages-scroller" style={{ backgroundColor: 'rgba(0,0,0,0.1)' }}>
          {messages.map((m, idx) => (
            <div key={idx} className={`chat-message-bubble ${m.sender}`}>
              <span className="message-sender-name">
                {m.sender === 'user' ? 'Client (You)' : 'AI Concierge'}
              </span>
              <div className="message-text-content">
                {m.text}
              </div>
              <span className="message-timestamp">{m.timestamp}</span>
            </div>
          ))}
          {loading && (
            <div className="chat-message-bubble bot" style={{ opacity: 0.7 }}>
              <span className="message-sender-name">AI Concierge</span>
              <div className="message-text-content" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RefreshCw size={14} className="spin-loader" />
                Thinking through LangGraph pipeline...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSend} className="chat-input-bar">
          <input 
            type="text" 
            placeholder="Type a message to test the chatbot..." 
            className="chat-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={loading || !input.trim()}
          >
            <Send size={18} />
          </button>
        </form>
      </div>

      {/* Live Graph Visualizer */}
      <div className="glass-panel flowchart-panel">
        <div>
          <h3 className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={16} style={{ color: 'var(--accent-cyan)' }} />
            LangGraph Execution Flow
          </h3>
          <p className="chart-subtitle" style={{ fontSize: '0.7rem' }}>Real-time execution node sequence tracing</p>
        </div>

        <div className="graph-nodes-container">
          {graphNodes.map((n, idx) => {
            const isCurrent = activeNode === n.id;
            let nodeClass = '';
            if (n.status === 'completed') nodeClass = 'completed-node';
            else if (n.status === 'active') nodeClass = 'active-node';

            return (
              <React.Fragment key={n.id}>
                {idx > 0 && idx < 7 && (
                  <div className="node-flow-arrow">
                    <ChevronDown size={14} />
                  </div>
                )}
                {/* Visual routing for direct response or main nodes */}
                {n.id === 'direct_response' && graphNodes.find(item => item.id === 'classifier').status !== 'completed' ? null : (
                  <div className={`graph-node ${nodeClass}`}>
                    <div className="node-label-container">
                      <span>{n.name}</span>
                      <span className="node-desc">{n.desc}</span>
                    </div>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Dynamic Nodes Metadata logs */}
        {(sentimentResult || auditReport.length > 0) && (
          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px', marginTop: '10px' }}>
            {sentimentResult && (
              <div style={{ marginBottom: '10px' }}>
                <span className="kpi-title" style={{ fontSize: '0.65rem', display: 'block', marginBottom: '4px' }}>Extracted Sentiment vibe</span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span className={`badge emotion-${sentimentResult.vibe}`}>{sentimentResult.vibe}</span>
                  <span className="badge resolved" style={{ background: 'rgba(255,255,255,0.05)', color: '#fff' }}>{sentimentResult.intent}</span>
                </div>
              </div>
            )}
            {auditReport.length > 0 && (
              <div>
                <span className="kpi-title" style={{ fontSize: '0.65rem', display: 'block', marginBottom: '4px' }}>Auditor Verification Checks</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {auditReport.map((ar, i) => (
                    <div key={i} style={{ fontSize: '0.7rem', color: '#b1b2cd', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle size={10} style={{ color: 'var(--accent-emerald)' }} />
                      {ar}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
