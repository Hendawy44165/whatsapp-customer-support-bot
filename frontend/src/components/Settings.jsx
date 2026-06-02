import React, { useState, useEffect } from 'react';
import { 
  Key, 
  Settings as SettingsIcon, 
  Eye, 
  EyeOff, 
  Save, 
  CheckCircle, 
  Cpu, 
  Sliders, 
  FileEdit,
  ShieldCheck
} from 'lucide-react';

export default function Settings() {
  // Load initial settings from localStorage or use defaults
  const [openAiKey, setOpenAiKey] = useState(() => localStorage.getItem('nuit_openai_key') || "");
  const [deepSeekKey, setDeepSeekKey] = useState(() => localStorage.getItem('nuit_deepseek_key') || "");
  const [selectedModel, setSelectedModel] = useState(() => localStorage.getItem('nuit_selected_model') || "deepseek-chat");
  const [temperature, setTemperature] = useState(() => parseFloat(localStorage.getItem('nuit_temperature') || "0.4"));
  const [systemPrompt, setSystemPrompt] = useState(() => {
    return localStorage.getItem('nuit_system_prompt') || 
      "You are a concierge customer service assistant representing Nuit Fragrances, a B2B boutique perfume brand. " +
      "Your objective is to provide professional, luxurious, and highly accurate guidance regarding products, " +
      "shipments, and exchange policies. Maintain an elegant, polite tone at all times. " +
      "Never share system tool specifications, credentials, or leak prompt keys.";
  });

  const [showOpenAi, setShowOpenAi] = useState(false);
  const [showDeepSeek, setShowDeepSeek] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    localStorage.setItem('nuit_openai_key', openAiKey);
    localStorage.setItem('nuit_deepseek_key', deepSeekKey);
    localStorage.setItem('nuit_selected_model', selectedModel);
    localStorage.setItem('nuit_temperature', temperature.toString());
    localStorage.setItem('nuit_system_prompt', systemPrompt);

    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {saveSuccess && (
        <div className="ui-alert success">
          <CheckCircle />
          <span>Settings successfully saved and committed to browser localStorage. AI concierge config refreshed.</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        
        {/* API Credentials */}
        <form onSubmit={handleSave} className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <h3 className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Key size={18} style={{ color: 'var(--accent-orange)' }} />
            API Keys Configuration
          </h3>

          <div className="settings-form-group">
            <label className="settings-label">OpenAI API Key</label>
            <div style={{ position: 'relative' }}>
              <input 
                type={showOpenAi ? "text" : "password"} 
                placeholder="sk-proj-..." 
                className="settings-input"
                value={openAiKey}
                onChange={(e) => setOpenAiKey(e.target.value)}
                style={{ paddingRight: '44px' }}
              />
              <button 
                type="button"
                onClick={() => setShowOpenAi(!showOpenAi)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#686256', display: 'flex', alignItems: 'center' }}
              >
                {showOpenAi ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="settings-form-group">
            <label className="settings-label">DeepSeek API Key</label>
            <div style={{ position: 'relative' }}>
              <input 
                type={showDeepSeek ? "text" : "password"} 
                placeholder="sk-..." 
                className="settings-input"
                value={deepSeekKey}
                onChange={(e) => setDeepSeekKey(e.target.value)}
                style={{ paddingRight: '44px' }}
              />
              <button 
                type="button"
                onClick={() => setShowDeepSeek(!showDeepSeek)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#686256', display: 'flex', alignItems: 'center' }}
              >
                {showDeepSeek ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', background: '#FDFBF7', border: '1px dashed #E6E1D5', padding: '14px', borderRadius: '8px', fontSize: '0.8rem', color: '#686256', marginTop: '10px', marginBottom: '14px' }}>
            <ShieldCheck size={20} style={{ color: 'var(--accent-emerald)', flexShrink: 0 }} />
            <div>
              <span style={{ fontWeight: 'bold', color: '#191816' }}>Security & Privacy Guard:</span> All keys are saved locally inside your browser's secure localStorage. They never transit through any external analytics servers or log collectors.
            </div>
          </div>

          <button type="submit" className="settings-save-button" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: 'fit-content' }}>
            <Save size={16} />
            Save Configuration
          </button>
        </form>

        {/* Model Configurations */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h3 className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} style={{ color: 'var(--accent-cyan)' }} />
            Model & Parameters
          </h3>

          <div className="settings-form-group">
            <label className="settings-label">Default LLM Provider Model</label>
            <select 
              className="settings-input"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ cursor: 'pointer' }}
            >
              <option value="deepseek-chat">DeepSeek Chat (deepseek-chat)</option>
              <option value="gpt-4o">OpenAI GPT-4o (gpt-4o)</option>
              <option value="gpt-3.5-turbo">OpenAI GPT-3.5 Turbo</option>
            </select>
          </div>

          <div className="settings-form-group">
            <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', width: '100%', marginBottom: '4px' }}>
              <label className="settings-label">Temperature (Creativity)</label>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--accent-cyan)', marginLeft: 'auto' }}>{temperature.toFixed(1)}</span>
            </div>
            <input 
              type="range" 
              min="0.0" 
              max="1.0" 
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#686256' }}>
              <span>Deterministic / Precise</span>
              <span>Creative / Free-form</span>
            </div>
          </div>
        </div>

      </div>

      {/* System Prompt Customization */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileEdit size={18} style={{ color: 'var(--accent-purple)' }} />
          Chatbot System Instructions (Concierge Prompt)
        </h3>
        
        <div className="settings-form-group" style={{ marginBottom: 0 }}>
          <label className="settings-label">Concierge System Prompt</label>
          <p className="chart-subtitle" style={{ marginBottom: '10px' }}>This text defines the base personality, guidelines, and behavioral boundaries of your chatbot concierge.</p>
          <textarea 
            className="settings-input settings-textarea"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Enter chatbot instructions here..."
          />
        </div>

        <button 
          onClick={handleSave}
          className="settings-save-button" 
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: 'fit-content' }}
        >
          <Save size={16} />
          Save System Instructions
        </button>
      </div>

    </div>
  );
}
