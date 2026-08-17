import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle, XCircle, Clock, Activity, MessageSquare, Mic, Search, ChevronRight, BarChart2, Eye, EyeOff } from 'lucide-react';

const API_URL = '';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [patientId, setPatientId] = useState('PAT-001');
  const [policyId, setPolicyId] = useState('POL-AETNA-TKR');
  const [targetCpt, setTargetCpt] = useState('');
  
  // Data States
  const [patientEntities, setPatientEntities] = useState(null);
  const [policyEntities, setPolicyEntities] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  
  // UI States
  const [showPatientData, setShowPatientData] = useState(false);
  const [showPolicyData, setShowPolicyData] = useState(false);
  
  // Loading States
  const [loadingPatient, setLoadingPatient] = useState(false);
  const [loadingPolicy, setLoadingPolicy] = useState(false);
  const [loadingEval, setLoadingEval] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);

  // Voice State
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      setRecognition(rec);
    }
  }, []);

  const speak = (text) => {
    if ('speechSynthesis' in window) {
      // stop any currently playing speech
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      // Optional: change voice or rate here if needed
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleVoiceInput = (setInputState) => {
    if (!recognition) {
      alert("Voice recognition is not supported in your browser.");
      return;
    }
    setIsListening(true);
    recognition.start();
    
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInputState(prev => prev ? prev + ' ' + transcript : transcript);
      setIsListening(false);
    };
    
    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
    };
    
    recognition.onend = () => {
      setIsListening(false);
    };
  };

  // Handlers
  const handlePatientUpload = async (e) => {
    e.preventDefault();
    setLoadingPatient(true);
    const formData = new FormData(e.target);
    try {
      const res = await axios.post(`${API_URL}/upload/patient`, formData);
      setPatientEntities(res.data); // Shows processing
      
      // Poll for background completion
      const poll = setInterval(async () => {
        try {
          const pollRes = await axios.get(`${API_URL}/api/patients/${patientId}`);
          if (pollRes.data.status === "success" && pollRes.data.data.entities) {
             setPatientEntities(pollRes.data.data);
             setLoadingPatient(false);
             clearInterval(poll);
          }
        } catch (err) {
          // Still processing, ignore 404
        }
      }, 2000);

    } catch (err) {
      console.error(err);
      alert('Failed to upload patient data');
      setLoadingPatient(false);
    }
  };

  const handlePolicyUpload = async (e) => {
    e.preventDefault();
    setLoadingPolicy(true);
    const formData = new FormData(e.target);
    try {
      const res = await axios.post(`${API_URL}/upload/policy`, formData);
      setPolicyEntities(res.data);
      
      // Poll for background completion
      const poll = setInterval(async () => {
        try {
          const pollRes = await axios.get(`${API_URL}/api/policies/${policyId}`);
          if (pollRes.data.status === "success" && pollRes.data.data.entities) {
             setPolicyEntities(pollRes.data.data);
             setLoadingPolicy(false);
             clearInterval(poll);
          }
        } catch (err) {
          // Still processing, ignore 404
        }
      }, 2000);

    } catch (err) {
      console.error(err);
      alert('Failed to upload policy data');
      setLoadingPolicy(false);
    }
  };

  const handleEvaluate = async (humanFeedback = null) => {
    setLoadingEval(true);
    try {
      let url = `${API_URL}/evaluate?patient_id=${patientId}&policy_id=${policyId}&target_cpt=${targetCpt}`;
      if (humanFeedback) url += `&human_feedback=${encodeURIComponent(humanFeedback)}`;
      
      const res = await axios.post(url);
      setEvaluation(res.data.decision);
      setActiveTab('matrix');
    } catch (err) {
      console.error(err);
      alert('Evaluation failed');
    }
    setLoadingEval(false);
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput) return;
    
    const userMsg = { sender: 'user', text: chatInput };
    setChatHistory(prev => [...prev, userMsg]);
    setChatInput('');
    setLoadingChat(true);
    
    try {
      const res = await axios.post(`${API_URL}/chat`, {
        query: userMsg.text,
        patient_id: patientId,
        policy_id: policyId
      });
      const botResponse = res.data.response;
      setChatHistory(prev => [...prev, { sender: 'bot', text: botResponse }]);
      
      // Auto-read response aloud for voice bot functionality
      speak(botResponse);
    } catch (err) {
      console.error(err);
      setChatHistory(prev => [...prev, { sender: 'bot', text: 'Error communicating with AI.' }]);
    }
    setLoadingChat(false);
  };

  return (
    <div className="app-container">
      <nav className="top-nav">
        <div>
          <h1 className="gradient-text" style={{ fontSize: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity /> PulseMed AI
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Enterprise Prior Auth Engine</p>
        </div>
        <div className="tabs">
          <button className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            Dashboard
          </button>
          <button className={`tab ${activeTab === 'matrix' ? 'active' : ''}`} onClick={() => setActiveTab('matrix')}>
            Prior Auth Matrix
          </button>
          <button className={`tab ${activeTab === 'metrics' ? 'active' : ''}`} onClick={() => setActiveTab('metrics')}>
            Metrics & Logs
          </button>
          <button className={`tab ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            Chatbot
          </button>
        </div>
      </nav>

      {/* DASHBOARD TAB */}
      {activeTab === 'dashboard' && (
        <div className="grid-2">
          {/* Patient Upload */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Upload size={18} /> Patient Chart Upload
            </h3>
            <form onSubmit={handlePatientUpload} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input type="text" name="patient_id" className="input-field" value={patientId} onChange={e => setPatientId(e.target.value)} required />
              <input type="file" name="files" multiple className="input-field" required accept="application/pdf" />
              <button type="submit" className="btn btn-primary" disabled={loadingPatient}>
                {loadingPatient ? <div className="spinner spinner-white"></div> : 'Upload & Extract Data'}
              </button>
            </form>
            
            {patientEntities && (
              <div style={{ marginTop: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span className="badge success">Extraction Complete</span>
                  <button type="button" className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => setShowPatientData(!showPatientData)}>
                    {showPatientData ? <><EyeOff size={14}/> Hide Data</> : <><Eye size={14}/> View Extracted Evidence</>}
                  </button>
                </div>
                {showPatientData && (
                  <div style={{ background: '#f1f5f9', padding: '12px', borderRadius: '8px', maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)' }}>
                    <pre style={{ fontSize: '12px', color: 'var(--text-main)' }}>{JSON.stringify(patientEntities.entities || patientEntities, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Policy Upload */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} /> Medical Policy Upload
            </h3>
            <form onSubmit={handlePolicyUpload} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input type="text" name="policy_id" className="input-field" value={policyId} onChange={e => setPolicyId(e.target.value)} required />
              <input type="file" name="file" className="input-field" required accept="application/pdf" />
              <button type="submit" className="btn btn-primary" disabled={loadingPolicy}>
                {loadingPolicy ? <div className="spinner spinner-white"></div> : 'Upload & Extract Policy'}
              </button>
            </form>
            
            {policyEntities && (
              <div style={{ marginTop: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span className="badge success">Extraction Complete</span>
                  <button type="button" className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => setShowPolicyData(!showPolicyData)}>
                    {showPolicyData ? <><EyeOff size={14}/> Hide Data</> : <><Eye size={14}/> View Extracted Evidence</>}
                  </button>
                </div>
                {showPolicyData && (
                  <div style={{ background: '#f1f5f9', padding: '12px', borderRadius: '8px', maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)' }}>
                    <pre style={{ fontSize: '12px', color: 'var(--text-main)' }}>{JSON.stringify(policyEntities.entities || policyEntities, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Action Row */}
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center', marginTop: '16px' }}>
             <div className="glass-panel" style={{ width: '100%', textAlign: 'center' }}>
               <h3 style={{ marginBottom: '16px' }}>Run AI Decision Engine</h3>
               <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                 <input type="text" placeholder="Requested CPT (Optional, AI will auto-deduce if empty)" className="input-field" style={{ maxWidth: '400px' }} value={targetCpt} onChange={e => setTargetCpt(e.target.value)} />
                 <button className="btn btn-primary" onClick={() => handleEvaluate()} disabled={loadingEval}>
                   {loadingEval ? <div className="spinner spinner-white"></div> : 'Evaluate Medical Necessity'}
                 </button>
               </div>
             </div>
          </div>
        </div>
      )}

      {/* METRICS DASHBOARD TAB */}
      {activeTab === 'metrics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <h2 className="gradient-text"><BarChart2 /> System Telemetry & RAGAS Metrics</h2>
            
            <div className="glass-panel">
                <h3>Reasoning Engine RAGAS Scores</h3>
                {evaluation ? (
                    <div className="grid-4" style={{ marginTop: '16px' }}>
                        <div style={{ textAlign: 'center', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                            <p style={{ color: 'var(--text-muted)' }}>Faithfulness</p>
                            <h2>{evaluation.ragas_metrics?.faithfulness}%</h2>
                        </div>
                        <div style={{ textAlign: 'center', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                            <p style={{ color: 'var(--text-muted)' }}>Context Relevance</p>
                            <h2>{evaluation.ragas_metrics?.relevance}%</h2>
                        </div>
                        <div style={{ textAlign: 'center', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                            <p style={{ color: 'var(--text-muted)' }}>Precision</p>
                            <h2>{evaluation.ragas_metrics?.precision}%</h2>
                        </div>
                        <div style={{ textAlign: 'center', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                            <p style={{ color: 'var(--text-muted)' }}>Recall</p>
                            <h2>{evaluation.ragas_metrics?.recall}%</h2>
                        </div>
                    </div>
                ) : (
                    <p style={{ color: 'var(--text-muted)', marginTop: '16px' }}>Run an evaluation to view Reasoning Metrics.</p>
                )}
            </div>
        </div>
      )}

      {/* PRIOR AUTH MATRIX TAB */}
      {activeTab === 'matrix' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {!evaluation ? (
            <div className="glass-panel" style={{ textAlign: 'center', padding: '48px' }}>
              <p style={{ color: 'var(--text-muted)' }}>Run an evaluation in the Dashboard to see the Matrix.</p>
            </div>
          ) : (
            <>
              {/* Header Stats */}
              <div className="grid-4">
                <div className="glass-panel" style={{ textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Final Decision</p>
                  <h2 className={`gradient-text`} style={{ fontSize: '32px', margin: '8px 0' }}>{evaluation.decision}</h2>
                </div>
                <div className="glass-panel" style={{ textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>AI Confidence Score</p>
                  <h2 style={{ fontSize: '32px', margin: '8px 0', color: evaluation.confidence_score ? 'var(--success)' : 'var(--warning)' }}>
                    {evaluation.confidence_score || evaluation.audit_status}
                  </h2>
                </div>
                <div className="glass-panel" style={{ textAlign: 'center', gridColumn: 'span 2' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Medical Director Reasoning Summary</p>
                  <p style={{ fontSize: '14px', margin: '8px 0', textAlign: 'left', whiteSpace: 'pre-wrap' }}>{evaluation.reasoning}</p>
                </div>
              </div>
              
              {/* The Matrix */}
              <div className="glass-panel">
                <h3 style={{ marginBottom: '16px' }}>Line-by-Line Criteria Matrix</h3>
                <table className="matrix-table">
                  <thead>
                    <tr>
                      <th style={{ width: '30%' }}>Policy Criterion</th>
                      <th style={{ width: '40%' }}>Patient Evidence</th>
                      <th style={{ width: '10%' }}>Met?</th>
                      <th style={{ width: '20%' }}>Citation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.criteria_matrix?.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontSize: '14px' }}>{row.criterion}</td>
                        <td style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{row.evidence}</td>
                        <td>
                          {row.met?.toLowerCase().includes('yes') || row.met === true ? 
                            <span className="badge success"><CheckCircle size={12} style={{marginRight: '4px'}}/> Yes</span> : 
                            <span className="badge danger"><XCircle size={12} style={{marginRight: '4px'}}/> No</span>}
                        </td>
                        <td>
                          {row.citation && <span className="badge info">{row.citation}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Human Override */}
              <div className="glass-panel">
                <h3 style={{ marginBottom: '16px' }}>Human-in-the-Loop Override</h3>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <input type="text" id="humanFeedback" placeholder="e.g. 'State laws changed, approve bypassing step-therapy'" className="input-field" />
                  <button className={`btn ${isListening ? 'btn-primary' : 'btn-outline'}`} onClick={() => handleVoiceInput(val => document.getElementById('humanFeedback').value = val)} style={{ display: 'flex', alignItems: 'center' }}>
                    <Mic size={16} /> {isListening ? 'Listening...' : 'Voice'}
                  </button>
                  <button className="btn btn-primary" onClick={() => handleEvaluate(document.getElementById('humanFeedback').value)}>
                    Submit Override
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* CHATBOT TAB */}
      {activeTab === 'chat' && (
        <div className="glass-panel chat-window">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
            <MessageSquare size={18} /> Medical Assistant (Voice Bot)
          </h3>
          <div className="chat-messages">
            {chatHistory.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '40px' }}>
                Ask a question about Patient {patientId} or Policy {policyId}... (Audio response enabled)
              </div>
            )}
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`message ${msg.sender}`}>
                {msg.text}
              </div>
            ))}
            {loadingChat && <div className="message bot"><div className="spinner spinner-white" style={{ width: '16px', height: '16px', borderTopColor: 'var(--primary)' }}></div></div>}
          </div>
          <form className="chat-input-area" onSubmit={handleChatSubmit}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="Type or speak your medical query here..." 
              value={chatInput} 
              onChange={e => setChatInput(e.target.value)} 
            />
            <button type="button" className={`btn ${isListening ? 'btn-primary' : 'btn-outline'}`} onClick={() => handleVoiceInput(setChatInput)}>
                <Mic size={16}/>
            </button>
            <button type="submit" className="btn btn-primary">Send <ChevronRight size={16}/></button>
          </form>
        </div>
      )}
    </div>
  );
}

export default App;
