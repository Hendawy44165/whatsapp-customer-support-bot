import React, { useState, useEffect, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  RefreshCw,
  Info
} from 'lucide-react';

export default function FileManager() {
  const [staticFiles, setStaticFiles] = useState(["brand_identity.md", "customer_service_sop.md"]);
  const [dynamicFiles, setDynamicFiles] = useState([
    "faq.md", 
    "product_specs.md", 
    "terms_of_conditions_and_policies.md",
    "icp.md",
    "meta_ad_strat.md"
  ]);
  
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }
  const [isConnected, setIsConnected] = useState(false);
  
  const fileInputRef = useRef(null);

  // Check connection and fetch actual backend files
  const fetchFiles = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        if (data.static_permanent_context) {
          setStaticFiles(data.static_permanent_context);
        }
        if (data.dynamic_rag_documents) {
          setDynamicFiles(data.dynamic_rag_documents);
        }
        setIsConnected(true);
      } else {
        setIsConnected(false);
      }
    } catch (err) {
      console.warn("Backend server not reached. Using mock document registry.");
      setIsConnected(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // Drag and Drop Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = async (e) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const onButtonClick = () => {
    fileInputRef.current.click();
  };

  // Upload Logic (Integrated with FastAPI endpoint with mock fallback)
  const uploadFile = async (file) => {
    // Validate file type
    const ext = file.name.substring(file.name.lastIndexOf('.'));
    if (ext !== '.md' && ext !== '.txt') {
      setFeedback({
        type: 'error',
        message: "Invalid file format. Only Markdown (.md) and text (.txt) files are supported."
      });
      return;
    }

    setUploading(true);
    setFeedback(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      if (isConnected) {
        // Real upload to FastAPI
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        
        if (response.ok) {
          setFeedback({
            type: 'success',
            message: `Successfully uploaded ${file.name}. Chatbot search index updated.`
          });
          if (data.available_documents) {
            setDynamicFiles(data.available_documents);
          } else {
            fetchFiles();
          }
        } else {
          setFeedback({
            type: 'error',
            message: data.detail || `Upload failed for ${file.name}.`
          });
        }
      } else {
        // Mock offline upload simulation
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        if (!dynamicFiles.includes(file.name.toLowerCase())) {
          setDynamicFiles(prev => [...prev, file.name.toLowerCase()]);
        }
        
        setFeedback({
          type: 'success',
          message: `Successfully uploaded ${file.name}. (Offline Simulation: Search Index reloaded)`
        });
      }
    } catch (error) {
      console.error("Upload error", error);
      setFeedback({
        type: 'error',
        message: `Network error. Could not upload ${file.name}.`
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-manager-grid fade-in">
      
      {/* Upload Column */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 className="chart-title">
            <UploadCloud size={18} style={{ color: "var(--accent-orange)" }} />
            Upload Help Guides & FAQs
          </h2>
          <p className="chart-subtitle">Upload customer policies, FAQs, and product sheets to update the chatbot's knowledge base.</p>
        </div>

        {feedback && (
          <div className={`ui-alert ${feedback.type}`}>
            {feedback.type === 'success' ? <CheckCircle /> : <AlertCircle />}
            <span>{feedback.message}</span>
          </div>
        )}

        <div 
          className={`dropzone-container ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={onButtonClick}
        >
          <input 
            type="file" 
            ref={fileInputRef}
            className="file-input-hidden" 
            accept=".md,.txt" 
            onChange={handleFileInput}
          />
          
          {uploading ? (
            <>
              <RefreshCw className="dropzone-icon spin-loader" style={{ color: 'var(--accent-cyan)' }} />
              <p className="dropzone-text" style={{ color: 'var(--accent-cyan)' }}>Uploading and indexing guide...</p>
              <p className="dropzone-subtext">Updating chatbot search index...</p>
            </>
          ) : (
            <>
              <UploadCloud className="dropzone-icon" />
              <p className="dropzone-text">Drag and drop file here, or click to browse</p>
              <p className="dropzone-subtext">Supports Markdown (.md) or text (.txt) files up to 5MB</p>
            </>
          )}
        </div>

        <div style={{ padding: '14px', background: '#FDFBF7', border: '1px dashed #E6E1D5', borderRadius: '10px', fontSize: '0.8rem', color: '#686256', display: 'flex', gap: '10px' }}>
          <Info size={16} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />
          <div>
            <span style={{ fontWeight: 'bold', color: '#191816' }}>Note on Chatbot Search:</span> Adding files updates the help registry immediately. The chatbot scans these files to answer specific questions.
          </div>
        </div>
      </div>

      {/* Database Registry Column */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
          <div>
            <h2 className="chart-title">
              <FileText size={18} style={{ color: "var(--accent-cyan)" }} />
              Active Help Library
            </h2>
            <p className="chart-subtitle">Loaded reference files available for chatbot replies</p>
          </div>
          <span className={`header-badge ${isConnected ? '' : 'offline'}`} style={{ color: isConnected ? 'var(--accent-emerald)' : 'var(--accent-red)' }}>
            {isConnected ? 'Sync Online' : 'Sync Simulated'}
          </span>
        </div>

        <div>
          <h4 className="metadata-section-title" style={{ fontSize: '0.75rem', marginBottom: '8px' }}>Standard Guidelines (Preloaded defaults)</h4>
          <div className="file-list" style={{ maxHeight: '140px', marginBottom: '16px' }}>
            {staticFiles.map((file, idx) => (
              <div key={idx} className="file-item" style={{ opacity: 0.85 }}>
                <div className="file-item-info">
                  <FileText size={16} style={{ color: 'var(--accent-purple)' }} />
                  <div>
                    <div className="file-item-name">{file}</div>
                    <span className="file-item-type" style={{ color: 'var(--accent-purple)', fontSize: '0.6rem' }}>Concierge rule set</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <h4 className="metadata-section-title" style={{ fontSize: '0.75rem', marginBottom: '8px' }}>Custom Reference Files</h4>
          <div className="file-list" style={{ maxHeight: '240px' }}>
            {dynamicFiles.length === 0 ? (
              <div className="empty-state">
                <FileText />
                <p>No custom help files uploaded yet</p>
              </div>
            ) : (
              dynamicFiles.map((file, idx) => (
                <div key={idx} className="file-item">
                  <div className="file-item-info">
                    <FileText size={16} style={{ color: 'var(--accent-cyan)' }} />
                    <div>
                      <div className="file-item-name">{file}</div>
                      <span className="file-item-type" style={{ color: 'var(--accent-cyan)', fontSize: '0.6rem' }}>Searchable guide</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
