import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle, XCircle, Activity, MessageSquare, Mic, Search, ChevronRight, BarChart2, Eye, EyeOff, Database } from 'lucide-react';

const API_URL = '';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Available DB IDs
  const [dbPatients, setDbPatients] = useState([]);
  const [dbPolicies, setDbPolicies] = useState([]);

  // Selection state
  const [patientMode, setPatientMode] = useState('upload'); // 'upload' or 'db'
  const [policyMode, setPolicyMode] = useState('upload'); // 'upload' or 'db'
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
  const [loading, setLoading] = useState(false);
  const [loadingEval, setLoadingEval] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);

  // Voice State
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);

  useEffect(() => {
    // Fetch available DB items
    const fetchDB = async () => {
      try {
        const patRes = await axios.get(`${API_URL}/api/patients`);
        setDbPatients(patRes.data.data);
        const polRes = await axios.get(`${API_URL}/api/policies`);
        setDbPolicies(polRes.data.data);
      } catch (err) {
        console.error("Failed to fetch DB lists", err);
      }
    };
    fetchDB();

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
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
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

  // Helper to wait for DB processing
  const pollForData = async (endpoint, id, setter) => {
    return new Promise((resolve) => {
      const poll = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}${endpoint}/${id}`);
          if (res.data.status === "success" && res.data.data.entities) {
             setter(res.data.data);
             clearInterval(poll);
             resolve();
          }
        } catch (err) {
          // keep polling
        }
      }, 2000);
    });
  };

  // Unified Document Analysis Submit
  const handleAnalyzeSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData(e.target);
    const patId = formData.get('patient_id');
    const polId = formData.get('policy_id');
    setPatientId(patId);
    setPolicyId(polId);

    try {
      let waitPromises = [];

      // Handle Patient
      if (patientMode === 'upload') {
        const patFormData = new FormData();
        patFormData.append('patient_id', patId);
        for(let file of formData.getAll('patient_files')) {
          if(file.size > 0) patFormData.append('files', file);
        }
        if(patFormData.getAll('files').length > 0) {
           await axios.post(`${API_URL}/upload/patient`, patFormData);
           setPatientEntities({status: "processing"});
           waitPromises.push(pollForData('/api/patients', patId, setPatientEntities));
        }
      } else {
        // Fetch existing
        const res = await axios.get(`${API_URL}/api/patients/${patId}`);
        setPatientEntities(res.data.data);
      }

      // Handle Policy
      if (policyMode === 'upload') {
        const polFormData = new FormData();
        polFormData.append('policy_id', polId);
        const pfile = formData.get('policy_file');
        if(pfile && pfile.size > 0) {
           polFormData.append('file', pfile);
           await axios.post(`${API_URL}/upload/policy`, polFormData);
           setPolicyEntities({status: "processing"});
           waitPromises.push(pollForData('/api/policies', polId, setPolicyEntities));
        }
      } else {
        // Fetch existing
        const res = await axios.get(`${API_URL}/api/policies/${polId}`);
        setPolicyEntities(res.data.data);
      }

      await Promise.all(waitPromises);
    } catch (err) {
      console.error(err);
      alert('Failed to analyze documents. Did you select a file?');
    }
    setLoading(false);
  };

  const handleEvaluate = async (humanFeedback = null) => {
    setLoadingEval(true);
    try {
      let url = `${API_URL}/evaluate?patient_id=${patientId}&policy_id=${policyId}&target_cpt=${targetCpt}`;
      if (humanFeedback) url += `&human_feedback=${encodeURIComponent(humanFeedback)}`;
      
      const res = await axios.post(url);
      setEvaluation(res.data.decision);
      setActiveTab('matrix');
      
      // Read decision aloud via Voice Bot
      speak(`Evaluation complete. The decision is ${res.data.decision.decision}.`);
      
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
      speak(botResponse);
    } catch (err) {
      console.error(err);
      setChatHistory(prev => [...prev, { sender: 'bot', text: 'Error communicating with AI.' }]);
    }
    setLoadingChat(false);
  };

  const renderFormattedEntities = (entities) => {
    if(!entities) return null;
    if(entities.status === "processing") return <div>Processing document in background... please wait.</div>;
    
    // Some basic formatting to prevent raw JSON
    return (
      <div style={{ fontSize: '13px', lineHeight: '1.6' }}>
        {entities.diagnoses && entities.diagnoses.length > 0 && (
          <div style={{marginBottom: '12px'}}>
            <strong>Diagnoses Found:</strong>
            <ul style={{marginLeft: '20px'}}>
              {entities.diagnoses.map((d, i) => (
                <li key={i}>{d.diagnosis} <span className="badge info" style={{fontSize:'10px'}}>{d.citations?.join(', ')}</span></li>
              ))}
            </ul>
          </div>
        )}
        {entities.procedures && entities.procedures.length > 0 && (
          <div style={{marginBottom: '12px'}}>
            <strong>Procedures Requested:</strong>
            <ul style={{marginLeft: '20px'}}>
              {entities.procedures.map((p, i) => (
                <li key={i}>{p.procedure_name} (CPT: {p.cpt_code || 'N/A'}) <span className="badge info" style={{fontSize:'10px'}}>{p.citations?.join(', ')}</span></li>
              ))}
            </ul>
          </div>
        )}
        {/* Render anything else dynamically */}
        {!entities.diagnoses && !entities.procedures && (
           <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
             {JSON.stringify(entities, null, 2)}
           </pre>
        )}
      </div>
    );
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
          
          {/* Unified Upload Form */}
          <div className="glass-panel" style={{ gridColumn: 'span 2' }}>
            <h3 style={{ marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
              Select Documents for Review
            </h3>
            <form onSubmit={handleAnalyzeSubmit}>
              <div className="grid-2">
                
                {/* Patient Section */}
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}><Upload size={16}/> Patient Medical Record</h4>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                     <button type="button" className={`btn ${patientMode==='upload' ? 'btn-primary' : 'btn-outline'}`} onClick={()=>setPatientMode('upload')} style={{flex: 1}}>Upload New</button>
                     <button type="button" className={`btn ${patientMode==='db' ? 'btn-primary' : 'btn-outline'}`} onClick={()=>setPatientMode('db')} style={{flex: 1}}><Database size={14}/> From Database</button>
                  </div>
                  
                  {patientMode === 'upload' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <input type="text" name="patient_id" placeholder="Enter new Patient ID" className="input-field" defaultValue="PAT-001" required />
                      <input type="file" name="patient_files" multiple className="input-field" accept="application/pdf" />
                    </div>
                  ) : (
                    <select name="patient_id" className="input-field" required>
                      {dbPatients.map(id => <option key={id} value={id}>{id}</option>)}
                      {dbPatients.length === 0 && <option value="">No patients found in DB</option>}
                    </select>
                  )}
                  
                  {patientEntities && (
                    <div style={{ marginTop: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span className="badge success">Ready</span>
                        <button type="button" className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => setShowPatientData(!showPatientData)}>
                          {showPatientData ? <><EyeOff size={14}/> Hide</> : <><Eye size={14}/> View</>}
                        </button>
                      </div>
                      {showPatientData && (
                        <div style={{ background: '#ffffff', padding: '12px', borderRadius: '8px', maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)' }}>
                          {renderFormattedEntities(patientEntities.entities || patientEntities)}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Policy Section */}
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}><FileText size={16}/> Medical Policy Document</h4>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                     <button type="button" className={`btn ${policyMode==='upload' ? 'btn-primary' : 'btn-outline'}`} onClick={()=>setPolicyMode('upload')} style={{flex: 1}}>Upload New</button>
                     <button type="button" className={`btn ${policyMode==='db' ? 'btn-primary' : 'btn-outline'}`} onClick={()=>setPolicyMode('db')} style={{flex: 1}}><Database size={14}/> From Database</button>
                  </div>
                  
                  {policyMode === 'upload' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <input type="text" name="policy_id" placeholder="Enter new Policy ID" className="input-field" defaultValue="POL-AETNA-TKR" required />
                      <input type="file" name="policy_file" className="input-field" accept="application/pdf" />
                    </div>
                  ) : (
                    <select name="policy_id" className="input-field" required>
                      {dbPolicies.map(id => <option key={id} value={id}>{id}</option>)}
                      {dbPolicies.length === 0 && <option value="">No policies found in DB</option>}
                    </select>
                  )}

                  {policyEntities && (
                    <div style={{ marginTop: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span className="badge success">Ready</span>
                        <button type="button" className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => setShowPolicyData(!showPolicyData)}>
                          {showPolicyData ? <><EyeOff size={14}/> Hide</> : <><Eye size={14}/> View</>}
                        </button>
                      </div>
                      {showPolicyData && (
                        <div style={{ background: '#ffffff', padding: '12px', borderRadius: '8px', maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)' }}>
                          {renderFormattedEntities(policyEntities.entities || policyEntities)}
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>

              <div style={{ marginTop: '24px', textAlign: 'center' }}>
                <button type="submit" className="btn btn-primary" style={{ padding: '12px 32px', fontSize: '16px' }} disabled={loading}>
                  {loading ? <div className="spinner spinner-white"></div> : 'Analyze Documents'}
                </button>
              </div>
            </form>
          </div>
          
          {/* Action Row */}
          {patientEntities && policyEntities && !loading && (
            <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center' }}>
               <div className="glass-panel" style={{ width: '100%', textAlign: 'center', background: 'var(--primary)', color: 'white' }}>
                 <h3 style={{ marginBottom: '16px' }}>Run AI Decision Engine</h3>
                 <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                   <input type="text" placeholder="Requested CPT (Optional, AI will auto-deduce if empty)" className="input-field" style={{ maxWidth: '400px', color: 'black' }} value={targetCpt} onChange={e => setTargetCpt(e.target.value)} />
                   <button className="btn" style={{ background: 'white', color: 'var(--primary)', fontWeight: 'bold' }} onClick={() => handleEvaluate()} disabled={loadingEval}>
                     {loadingEval ? <div className="spinner" style={{ borderTopColor: 'var(--primary)' }}></div> : 'Evaluate Medical Necessity'}
                   </button>
                 </div>
               </div>
            </div>
          )}
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
                <div style={{ overflowX: 'auto' }}>
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
              </div>
              
              {/* Human Override */}
              <div className="glass-panel">
                <h3 style={{ marginBottom: '16px' }}>Provide Feedback</h3>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <input type="text" id="humanFeedback" placeholder="e.g. 'State laws changed, approve bypassing step-therapy'" className="input-field" />
                  <button className={`btn ${isListening ? 'btn-primary' : 'btn-outline'}`} onClick={() => handleVoiceInput(val => document.getElementById('humanFeedback').value = val)} style={{ display: 'flex', alignItems: 'center' }}>
                    <Mic size={16} /> {isListening ? 'Listening...' : 'Voice'}
                  </button>
                  <button className="btn btn-primary" onClick={() => handleEvaluate(document.getElementById('humanFeedback').value)}>
                    Submit Feedback
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
          
          <form className="chat-input-area" onSubmit={handleChatSubmit} style={{ borderTop: 'none', borderBottom: '1px solid var(--border)', paddingTop: 0, paddingBottom: '16px', marginBottom: '16px' }}>
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

          <div className="chat-messages" style={{ display: 'flex', flexDirection: 'column-reverse' }}>
            {loadingChat && <div className="message bot"><div className="spinner spinner-white" style={{ width: '16px', height: '16px', borderTopColor: 'var(--primary)' }}></div></div>}
            
            {/* Render in reverse because of column-reverse layout to keep input at top */}
            {[...chatHistory].reverse().map((msg, idx) => (
              <div key={idx} className={`message ${msg.sender}`}>
                {msg.text}
              </div>
            ))}

            {chatHistory.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '40px' }}>
                Ask a question about Patient {patientId} or Policy {policyId}... (Audio response enabled)
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
