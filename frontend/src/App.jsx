import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle, AlertTriangle, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';

const API_BASE = 'http://localhost:8000/api/v1';

function App() {
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      if (currentScrollY > lastScrollY && currentScrollY > 50) {
        setIsHeaderVisible(false);
      } else {
        setIsHeaderVisible(true);
      }
      setLastScrollY(currentScrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  useEffect(() => {
    let interval;
    if (documentId && (!statusData || statusData.status !== 'COMPLETED' && statusData.status !== 'FAILED')) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${documentId}`);
          const data = res.data;

          // Browser console error reporting for DevTools debugging
          if (data.status === 'FAILED') {
            // Find which agent was active when failure occurred
            const AGENT_STAGES = {
              'UPLOADED': 'Agent 1: Ingestion',
              'CLASSIFYING_PDF': 'Agent 2: PDF Type Classifier',
              'OCR_EXTRACTION': 'Agent 3: OCR & Text Extraction',
              'DOCUMENT_CLASSIFICATION': 'Agent 4: Document Classifier',
              'TABLE_EXTRACTION': 'Agent 5: Table Extraction',
              'NORMALIZING_METRICS': 'Agent 6: Normalization',
              'FINANCIAL_ANALYSIS': 'Agent 7: Financial Analysis',
              'NLP_SUMMARIZATION': 'Agent 8: NLP Summary',
              'VERDICT_PREDICTION': 'Agent 9: Verdict',
              'VISUALIZATION_PREP': 'Agent 10: Visualization',
            };
            // The previous status (before FAILED) is the agent that was running
            const failedAtStage = statusData?.status ? (AGENT_STAGES[statusData.status] || statusData.status) : 'Unknown Stage';
            console.error("Pipeline Execution Failure:", data.error_message || '(no error_message returned by backend)');
            console.error(
              `%c[Pipeline FAILED] Stage: ${failedAtStage}`,
              'color: #ff4444; font-weight: bold; font-size: 14px;'
            );
            console.error('Backend error message:', data.error_message || '(no error message returned)');
            console.error('Full status payload:', data);
            console.error('Document ID:', documentId);
          }

          setStatusData(data);
        } catch (e) {
          const errMsg = e?.response?.data?.error_message || e?.response?.data?.detail || e?.message || String(e);
          console.error("Pipeline Execution Failure:", errMsg);
          console.error("Polling request failed:", e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [documentId, statusData]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelection = (selectedFile) => {
    setError(null);
    setStatusData(null);
    setDocumentId(null);
    if (selectedFile.type !== 'application/pdf') {
      setError("Please upload a valid PDF file.");
      return;
    }
    setFile(selectedFile);
  };

  const uploadFile = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setDocumentId(res.data.document_id);
      setStatusData({ status: res.data.status });
    } catch (e) {
      setError("Failed to upload document. Ensure backend is running.");
      console.error(e);
    }
  };

  const renderVerdictBadge = (verdictData) => {
    if (!verdictData) return null;
    const { verdict, confidence } = verdictData;
    let colorClass = "bg-brutalist-bg text-brutalist-dark";
    if (verdict === "GOOD") colorClass = "bg-brutalist-green text-white";
    if (verdict === "BAD") colorClass = "bg-brutalist-orange text-white";
    if (verdict === "NEUTRAL") colorClass = "bg-brutalist-bg text-brutalist-dark";

    return (
      <div className={`px-4 py-2 border-2 border-brutalist-dark rounded-none font-bold shadow-[4px_4px_0px_0px_#1A1A1A] flex items-center gap-2 ${colorClass}`}>
        {verdict === "GOOD" ? <TrendingUp size={20} /> : verdict === "BAD" ? <TrendingDown size={20} /> : <Activity size={20} />}
        {verdict} ({confidence != null ? (confidence * 100).toFixed(0) : 0}% Confidence)
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-brutalist-bg text-brutalist-dark font-sans selection:bg-brutalist-orange selection:text-white">
      {/* Header */}
      <header className={`fixed top-0 w-full z-50 transition-transform duration-300 bg-[#F2EBE3] border-b-4 border-[#1A1A1A] ${isHeaderVisible ? 'translate-y-0' : '-translate-y-full'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-none border-2 border-brutalist-dark bg-brutalist-orange flex items-center justify-center shadow-[2px_2px_0px_0px_#1A1A1A]">
              <Activity className="text-brutalist-dark" size={20} />
            </div>
            <h1 className="text-xl font-black tracking-tight uppercase">
              AI Financial Results <span className="font-serif italic text-brutalist-green lowercase capitalize">Analyzer.</span>
            </h1>
          </div>
          <div className="text-sm text-brutalist-dark font-mono uppercase tracking-widest font-bold">
            100% NON-LLM ARCHITECTURE
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-10 space-y-12">
        
        {/* Top Section: Upload & Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Upload Panel */}
          <div className="lg:col-span-1">
            <div className="brutalist-panel p-8 h-full flex flex-col">
              <h2 className="text-lg font-black uppercase tracking-tight text-brutalist-dark mb-4 flex items-center gap-2">
                <FileText className="text-brutalist-orange" size={24} strokeWidth={3} />
                Upload Results PDF
              </h2>
              
              <div 
                className={`flex-1 border-4 border-dashed border-brutalist-dark rounded-none flex flex-col items-center justify-center p-8 transition-all duration-300 ${
                  isDragging ? 'bg-brutalist-orange/20' : 'bg-white hover:bg-stone-50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <Upload className={`mb-4 ${isDragging ? 'text-brutalist-orange' : 'text-brutalist-dark'}`} size={40} strokeWidth={2} />
                <p className="text-sm text-brutalist-dark font-bold text-center mb-4 uppercase tracking-wider">
                  Drag and drop your CA-firm PDF here, or
                </p>
                <label className="cursor-pointer brutalist-button px-6 py-2 text-sm">
                  Browse Files
                  <input type="file" className="hidden" accept="application/pdf" onChange={(e) => handleFileSelection(e.target.files[0])} />
                </label>
                {file && (
                  <div className="mt-6 text-sm font-bold text-brutalist-green bg-brutalist-green/10 border-2 border-brutalist-green px-4 py-2 rounded-none truncate max-w-full">
                    {file.name}
                  </div>
                )}
              </div>
              
              {error && <div className="mt-4 text-brutalist-orange font-bold text-sm flex items-center gap-2 uppercase tracking-wide border-2 border-brutalist-orange p-2"><AlertTriangle size={20}/> {error}</div>}
              
              <button 
                onClick={uploadFile}
                disabled={!file || (statusData && !['FAILED', 'COMPLETED'].includes(statusData.status))}
                className="mt-6 w-full py-4 px-4 brutalist-button disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[4px_4px_0px_0px_#1A1A1A]"
              >
                {statusData && !['FAILED', 'COMPLETED'].includes(statusData.status) ? 'Processing...' : 'Analyze Document'}
              </button>
            </div>
          </div>

          {/* Processing Status & Quick Metrics */}
          <div className="lg:col-span-2">
            <div className="brutalist-panel p-8 h-full">
              <div className="flex justify-between items-start mb-6 border-b-4 border-brutalist-dark pb-4">
                <div>
                  <h2 className="text-xl font-black uppercase tracking-tight text-brutalist-dark">Pipeline Status</h2>
                  <p className="text-sm text-brutalist-dark font-bold font-mono mt-1 uppercase tracking-widest">Multi-agent extraction workflow</p>
                </div>
                {statusData?.verdict && renderVerdictBadge(statusData.verdict)}
              </div>

              {/* Status Tracker */}
              <div className="bg-white border-4 border-brutalist-dark p-5 font-mono text-sm max-h-64 overflow-y-auto shadow-inner">
                {statusData?.error_message && (
                  <div className="mb-4 p-3 bg-brutalist-orange/20 border-2 border-brutalist-orange text-brutalist-dark font-bold">
                    <strong className="block mb-1 uppercase tracking-wider text-brutalist-orange">Pipeline Error:</strong>
                    {statusData.error_message}
                  </div>
                )}
                
                <div className="space-y-3">
                  {[
                    { id: 'UPLOADED', label: 'Agent 1: Ingestion' },
                    { id: 'CLASSIFYING_PDF', label: 'Agent 2: PDF Type Classifier' },
                    { id: 'OCR_EXTRACTION', label: 'Agent 3: OCR & Extraction' },
                    { id: 'DOCUMENT_CLASSIFICATION', label: 'Agent 4: Financial Document Verification' },
                    { id: 'TABLE_EXTRACTION', label: 'Agent 5: Financial Metrics Table Extraction' },
                    { id: 'NORMALIZING_METRICS', label: 'Agent 6: Value Normalization (INR)' },
                    { id: 'FINANCIAL_ANALYSIS', label: 'Agent 7: Financial Ratio Analysis' },
                    { id: 'NLP_SUMMARIZATION', label: 'Agent 8: AI Summarization Generation' },
                    { id: 'VERDICT_PREDICTION', label: 'Agent 9: Earnings Verdict Prediction' },
                    { id: 'VISUALIZATION_PREP', label: 'Agent 10: JSON Dashboard Prep' },
                    { id: 'COMPLETED', label: 'Pipeline Execution Complete' }
                  ].map((step, idx, arr) => {
                    const currentStatus = statusData?.status || 'WAITING_FOR_UPLOAD';
                    const isFailed = currentStatus === 'FAILED';
                    const currentIndex = arr.findIndex(s => s.id === currentStatus);
                    
                    let state = 'waiting';
                    // Try to guess failed stage from error message if possible
                    let guessedFailedIndex = -1;
                    if (isFailed && statusData?.error_message) {
                        const err = statusData.error_message.toLowerCase();
                        if (err.includes('ingest') || err.includes('upload')) guessedFailedIndex = 0;
                        else if (err.includes('pdf_type') || err.includes('agent 2')) guessedFailedIndex = 1;
                        else if (err.includes('ocr') || err.includes('agent 3')) guessedFailedIndex = 2;
                        else if (err.includes('classif') || err.includes('agent 4')) guessedFailedIndex = 3;
                        else if (err.includes('table') || err.includes('agent 5') || err.includes('agent5')) guessedFailedIndex = 4;
                        else if (err.includes('normaliz') || err.includes('agent 6')) guessedFailedIndex = 5;
                        else if (err.includes('analys') || err.includes('agent 7')) guessedFailedIndex = 6;
                    }
                    
                    if (isFailed) {
                        if (currentIndex !== -1) {
                            if (idx < currentIndex) state = 'completed';
                            else if (idx === currentIndex) state = 'failed';
                            else state = 'aborted';
                        } else if (guessedFailedIndex !== -1) {
                            if (idx < guessedFailedIndex) state = 'completed';
                            else if (idx === guessedFailedIndex) state = 'failed';
                            else state = 'aborted';
                        } else {
                            state = 'aborted'; // If we don't know, just gray them out
                        }
                    } else if (currentStatus === 'COMPLETED') {
                        state = 'completed';
                    } else if (currentIndex > idx) {
                        state = 'completed';
                    } else if (currentIndex === idx) {
                        state = 'running';
                    }

                    if (state === 'waiting' && currentStatus !== 'WAITING_FOR_UPLOAD') return null; // hide future steps to keep it clean, or show them grayed out

                    return (
                      <div key={step.id} className="flex items-center gap-4">
                        <div className={`w-5 h-5 border-2 border-brutalist-dark flex items-center justify-center font-black text-sm ${
                          state === 'completed' ? 'bg-white text-brutalist-dark' : 
                          state === 'running' ? 'bg-brutalist-orange text-brutalist-dark' : 
                          state === 'failed' ? 'bg-brutalist-orange text-white' : 
                          'bg-transparent text-transparent'
                        }`}>
                          {state === 'completed' && '✅'}
                          {state === 'running' && '>'}
                          {state === 'failed' && '!'}
                        </div>
                        <span className={`uppercase tracking-wider text-xs font-bold ${
                          state === 'completed' ? 'text-brutalist-dark' : 
                          state === 'running' ? 'text-brutalist-orange text-sm' : 
                          state === 'failed' ? 'text-brutalist-orange line-through decoration-2' : 
                          'text-brutalist-dark/40'
                        }`}>
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {statusData?.metadata && (
                  <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t-4 border-brutalist-dark text-brutalist-dark font-mono text-xs uppercase tracking-widest font-bold bg-white p-4 border-x-4 border-b-4">
                    <div>Category: <span className="text-brutalist-green">{statusData.metadata.document_category || '...'}</span></div>
                    <div>PDF Type: <span className="text-brutalist-green">{statusData.metadata.pdf_type || '...'}</span></div>
                    <div>Pages: <span className="text-brutalist-green">{statusData.metadata.total_pages || '...'}</span></div>
                    <div>OCR Req: <span className="text-brutalist-orange">{statusData.metadata.requires_ocr ? 'YES' : 'NO'}</span></div>
                  </div>
                )}
              </div>

              {/* Quick Metrics (Appears when completed) */}
              {statusData?.analysis_results && (
                <div className="grid grid-cols-3 gap-8 mt-6">
                  {[
                    { label: 'Rev QoQ', key: 'qoq_growth', icon: <TrendingUp size={14}/> },
                    { label: 'Rev YoY', key: 'yoy_growth', icon: <TrendingUp size={14}/> },
                    { label: 'Net Margin', key: 'net_margin', icon: <DollarSign size={14}/> },
                    { label: 'PAT QoQ', key: 'pat_qoq', icon: <Activity size={14}/> },
                    { label: 'PAT YoY', key: 'pat_yoy', icon: <Activity size={14}/> },
                    { label: 'EBITDA Margin', key: 'ebitda_margin', icon: <DollarSign size={14}/> },
                  ].map(({ label, key, icon }) => {
                    const val = statusData.analysis_results[key];
                    const isNull = val === null || val === undefined;
                    const isPositive = val > 0;
                    const isNegative = val < 0;
                    return (
                      <div key={key} className="brutalist-card p-4">
                        <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 flex items-center gap-2 border-b-2 border-brutalist-dark pb-2 mb-2">{icon} {label}</div>
                        <div className={`text-2xl font-black tracking-tighter ${isNull ? 'text-brutalist-dark/40' : isPositive ? 'text-[#2E6F40]' : isNegative ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                          {isNull ? 'N/A' : `${val}%${isPositive ? ' ↑' : isNegative ? ' ↓' : ''}`}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Section: Analytics & Summaries */}
        {statusData?.status === 'COMPLETED' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            
            {/* Chart Area — 3 focused financial charts */}
            <div className="brutalist-panel p-8 space-y-8">

              {/* Chart 1: Total Income Quarterly Trend */}
              <div>
                <h3 className="text-lg font-black tracking-tight uppercase text-brutalist-dark mb-1">Total Income Trend <span className="font-mono text-xs font-bold tracking-widest">(₹ crores)</span></h3>
                <p className="text-brutalist-dark text-xs mb-3 font-mono">Revenue from operations + Other income</p>
                <div className="h-44 border-4 border-brutalist-dark p-2 bg-white">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={
                      (statusData.metadata?.charts_data?.revenue_trend?.labels || []).map((label, idx) => ({
                        name: label,
                        Income: statusData.metadata.charts_data.revenue_trend.datasets[0].data[idx]
                      }))
                    }>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" vertical={false} />
                      <XAxis dataKey="name" stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace'}} />
                      <YAxis stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace'}} width={75}
                        tickFormatter={v => `₹${(v/1000).toFixed(1)}k`} />
                      <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                        itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Total Income']} />
                      <Line type="monotone" dataKey="Income" stroke="#D95A2B" strokeWidth={4}
                        dot={{r: 6, fill: '#D95A2B', strokeWidth: 2}} activeDot={{r: 8}} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Net Profit Quarterly Trend */}
              <div>
                <h3 className="text-lg font-black tracking-tight uppercase text-brutalist-dark mb-1">Net Profit (PAT) Trend <span className="font-mono text-xs font-bold tracking-widest">(₹ crores)</span></h3>
                <p className="text-brutalist-dark text-xs mb-3 font-mono">Profit after tax — quarterly comparison</p>
                <div className="h-44 border-4 border-brutalist-dark p-2 bg-white">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={
                      (statusData.metadata?.charts_data?.pat_trend?.labels || []).map((label, idx) => ({
                        name: label,
                        PAT: statusData.metadata.charts_data.pat_trend.datasets[0].data[idx]
                      }))
                    }>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" vertical={false} />
                      <XAxis dataKey="name" stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace'}} />
                      <YAxis stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace'}} width={75}
                        tickFormatter={v => `₹${(v/1000).toFixed(1)}k`} />
                      <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                        itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Net Profit']} />
                      <Line type="monotone" dataKey="PAT" stroke="#2E6F40" strokeWidth={4}
                        dot={{r: 6, fill: '#2E6F40', strokeWidth: 2}} activeDot={{r: 8}} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 3: Margin % Trend */}
              {(statusData.metadata?.charts_data?.margin_trend?.length > 0) && (
                <div>
                  <h3 className="text-lg font-black tracking-tight uppercase text-brutalist-dark mb-1">Margin Trends <span className="font-mono text-xs font-bold tracking-widest">(%)</span></h3>
                  <p className="text-brutalist-dark text-xs mb-3 font-mono">Net Margin &amp; EBITDA Margin over quarters</p>
                  <div className="h-44 border-4 border-brutalist-dark p-2 bg-white">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={statusData.metadata.charts_data.margin_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" vertical={false} />
                        <XAxis dataKey="name" stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace'}} />
                        <YAxis stroke="#1A1A1A" tick={{fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace'}} width={45}
                          tickFormatter={v => `${v}%`} />
                        <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                          itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`${v}%`, '']} />
                        <Legend wrapperStyle={{color: '#1A1A1A', fontSize: '12px', fontWeight: 'bold', fontFamily: 'monospace'}} />
                        <Line type="monotone" dataKey="Net Margin" stroke="#2E6F40" strokeWidth={3}
                          dot={{r: 5}} activeDot={{r: 7}} connectNulls />
                        <Line type="monotone" dataKey="EBITDA Margin" stroke="#D95A2B" strokeWidth={3}
                          strokeDasharray="5 5" dot={{r: 5}} activeDot={{r: 7}} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

            </div>

            {/* AI Summary */}
            <div className="brutalist-panel p-8">
              <h3 className="text-xl font-black uppercase tracking-tight text-brutalist-dark mb-6 border-b-4 border-brutalist-dark pb-4">Analyst Summary</h3>
              {statusData?.nlp_summary && (
                <div className="space-y-6">
                  <div className="p-4 border-4 border-brutalist-dark bg-white shadow-[4px_4px_0px_0px_#1A1A1A]">
                    <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest bg-brutalist-orange text-white inline-block px-2 py-1">Executive Overview</h4>
                    <p className="text-brutalist-dark font-medium leading-relaxed">{statusData.nlp_summary.executive_summary}</p>
                  </div>
                  
                  <div className="p-4 border-4 border-brutalist-dark bg-white shadow-[4px_4px_0px_0px_#1A1A1A]">
                    <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest bg-brutalist-green text-white inline-block px-2 py-1">Retail Investor Context</h4>
                    <p className="text-brutalist-dark font-medium leading-relaxed">{statusData.nlp_summary.investor_explanation}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-6 mt-4">
                    <div className="border-t-4 border-brutalist-dark pt-4">
                      <h4 className="text-sm font-black text-brutalist-green mb-3 uppercase tracking-widest">Key Highlights</h4>
                      <ul className="space-y-2">
                        {(statusData.nlp_summary.highlights || []).map((h, i) => (
                          <li key={i} className="text-sm font-medium text-brutalist-dark flex items-start gap-2">
                            <CheckCircle size={18} className="text-brutalist-green shrink-0 mt-0.5" strokeWidth={3} />
                            <span>{h}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="border-t-4 border-brutalist-dark pt-4">
                      <h4 className="text-sm font-black text-brutalist-orange mb-3 uppercase tracking-widest">Potential Risks</h4>
                      <ul className="space-y-2">
                        {(statusData.nlp_summary.risks || []).map((r, i) => (
                          <li key={i} className="text-sm font-medium text-brutalist-dark flex items-start gap-2">
                            <AlertTriangle size={18} className="text-brutalist-orange shrink-0 mt-0.5" strokeWidth={3} />
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
        )}

        {/* Balance Sheet Profile */}
        {statusData?.status === 'COMPLETED' && statusData?.analysis_results && (
          <div className="brutalist-panel p-8 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-150">
            <h3 className="text-xl font-black uppercase tracking-tight text-brutalist-dark mb-6 border-b-4 border-brutalist-dark pb-4">Balance Sheet Profile</h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Column A: Solvency & Expansion Risk */}
              <div className="bg-[#F2EBE3] border-4 border-brutalist-dark p-6 shadow-[4px_4px_0px_0px_#1A1A1A]">
                <h4 className="text-sm font-black text-brutalist-dark mb-4 uppercase tracking-widest bg-brutalist-dark text-white inline-block px-3 py-1">Solvency & Expansion Risk</h4>
                
                <div className="space-y-6">
                  <div>
                    <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                      Total Borrowings
                      <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                        Calculated as: Non-Current Borrowings + Current Borrowings
                      </div>
                    </div>
                    <div className="text-3xl font-black tracking-tighter text-brutalist-dark">
                      {statusData.analysis_results.total_borrowings_cr != null ? `₹${Number(statusData.analysis_results.total_borrowings_cr).toFixed(2)} cr` : 'N/A'}
                    </div>
                    {statusData.analysis_results.total_borrowings_cr_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                        vs. ₹{Number(statusData.analysis_results.total_borrowings_cr_prev).toFixed(2)} cr (LY) 
                        {statusData.analysis_results.total_borrowings_cr < statusData.analysis_results.total_borrowings_cr_prev ? ' [↓ Deleveraging]' : ' [↑ Leveraging]'}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                      Net Debt (Debt Minus Cash)
                      <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                        Calculated as: Total Borrowings - (Cash Equivalents + Bank Balances)
                      </div>
                    </div>
                    <div className="text-3xl font-black tracking-tighter text-brutalist-dark">
                      {statusData.analysis_results.net_debt_cr != null ? `₹${Number(statusData.analysis_results.net_debt_cr).toFixed(2)} cr` : 'N/A'}
                    </div>
                    {statusData.analysis_results.net_debt_cr_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                        vs. ₹{Number(statusData.analysis_results.net_debt_cr_prev).toFixed(2)} cr (LY)
                      </div>
                    )}
                  </div>

                  <div className="pt-4 border-t-2 border-brutalist-dark border-dashed">
                    <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1">Capital Work-In-Progress (CWIP)</div>
                    <div className="text-2xl font-black tracking-tighter text-brutalist-dark mb-1">
                      {statusData.analysis_results.cwip_cr != null ? `₹${Number(statusData.analysis_results.cwip_cr).toFixed(2)} cr` : 'N/A'}
                    </div>
                    {statusData.analysis_results.cwip_cr_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 mb-2 font-mono font-bold">
                        vs. ₹{Number(statusData.analysis_results.cwip_cr_prev).toFixed(2)} cr (LY)
                      </div>
                    )}
                    <p className="text-xs font-medium text-brutalist-dark/70 uppercase tracking-wider">
                      {statusData.analysis_results.cwip_cr_prev != null 
                        ? (statusData.analysis_results.cwip_cr < statusData.analysis_results.cwip_cr_prev ? 'Status: Assets Entering Production Phase' : 'Status: Factory/Capacity Expansion Ongoing')
                        : 'Asset Deployment Health'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Column B: Liquidity & Efficiency Profile */}
              <div className="bg-[#F2EBE3] border-4 border-brutalist-dark p-6 shadow-[4px_4px_0px_0px_#1A1A1A]">
                <h4 className="text-sm font-black text-brutalist-dark mb-4 uppercase tracking-widest bg-brutalist-dark text-white inline-block px-3 py-1">Liquidity & Efficiency Profile</h4>
                
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest group relative cursor-help flex w-max items-center">
                        Liquidity Ratio (Current Ratio)
                        <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                          Calculated as: Total Current Assets / Total Current Liabilities
                        </div>
                      </div>
                      {statusData.analysis_results.current_ratio != null && statusData.analysis_results.current_ratio < 1.0 && (
                        <div className="bg-[#D95A2B] text-white text-[10px] font-black px-2 py-0.5 uppercase tracking-widest border-2 border-brutalist-dark">
                          [!] Liquidity Risk
                        </div>
                      )}
                    </div>
                    <div className={`text-3xl font-black tracking-tighter ${statusData.analysis_results.current_ratio != null ? (statusData.analysis_results.current_ratio < 1.0 ? 'text-[#D95A2B]' : 'text-[#2E6F40]') : 'text-brutalist-dark'}`}>
                      {statusData.analysis_results.current_ratio != null ? `${Number(statusData.analysis_results.current_ratio).toFixed(2)}x` : 'N/A'}
                    </div>
                    {statusData.analysis_results.current_ratio_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                        vs. {Number(statusData.analysis_results.current_ratio_prev).toFixed(2)}x (LY)
                      </div>
                    )}
                  </div>
                  
                  <div className="pt-4 border-t-2 border-brutalist-dark border-dashed">
                    <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1">Trade Receivables</div>
                    <div className="text-2xl font-black tracking-tighter text-brutalist-dark">
                      {statusData.analysis_results.trade_receivables_cr != null ? `₹${Number(statusData.analysis_results.trade_receivables_cr).toFixed(2)} cr` : 'N/A'}
                    </div>
                    {statusData.analysis_results.trade_receivables_cr_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                        vs. ₹{Number(statusData.analysis_results.trade_receivables_cr_prev).toFixed(2)} cr (LY)
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1">Inventories</div>
                    <div className="text-2xl font-black tracking-tighter text-brutalist-dark">
                      {statusData.analysis_results.inventories_cr != null ? `₹${Number(statusData.analysis_results.inventories_cr).toFixed(2)} cr` : 'N/A'}
                    </div>
                    {statusData.analysis_results.inventories_cr_prev != null && (
                      <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                        vs. ₹{Number(statusData.analysis_results.inventories_cr_prev).toFixed(2)} cr (LY)
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Cash Conversion Speed Panel */}
            <div className="mt-8 bg-[#F2EBE3] border-4 border-brutalist-dark p-6 shadow-[4px_4px_0px_0px_#1A1A1A]">
              <h4 className="text-lg font-black text-brutalist-dark mb-6 uppercase tracking-widest border-b-4 border-brutalist-dark pb-2">Operational Cash Conversion Speed</h4>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-6">
                <div>
                  <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                    Inventory Days
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                      Calculated as: (Inventories / Revenue from Operations) * 365
                    </div>
                  </div>
                  <div className="text-3xl font-black tracking-tighter text-brutalist-dark">
                    {statusData.analysis_results.inventory_days != null ? `${Number(statusData.analysis_results.inventory_days).toFixed(0)} DAYS` : 'N/A'}
                  </div>
                  {statusData.analysis_results.inventory_days_ly != null && (
                    <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. {Number(statusData.analysis_results.inventory_days_ly).toFixed(0)} DAYS (LY)
                      {statusData.analysis_results.inventory_days > statusData.analysis_results.inventory_days_ly ? ' [↑ Slowing Demand / Piling Stock]' : ' [↓ Faster Product Turnover]'}
                    </div>
                  )}
                </div>
                
                <div>
                  <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                    Debtor Days
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                      Calculated as: (Trade Receivables / Revenue from Operations) * 365
                    </div>
                  </div>
                  <div className="text-3xl font-black tracking-tighter text-brutalist-dark">
                    {statusData.analysis_results.debtor_days != null ? `${Number(statusData.analysis_results.debtor_days).toFixed(0)} DAYS` : 'N/A'}
                  </div>
                  {statusData.analysis_results.debtor_days_ly != null && (
                    <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. {Number(statusData.analysis_results.debtor_days_ly).toFixed(0)} DAYS (LY)
                      {statusData.analysis_results.debtor_days > statusData.analysis_results.debtor_days_ly ? ' [↑ Collection Delay / Easy Credit]' : ' [↓ Faster Cash Collection]'}
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t-4 border-brutalist-dark">
                <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest">Efficiency Verdict</h4>
                <p className="text-brutalist-dark font-medium leading-relaxed">
                  {(() => {
                    const id_curr = statusData.analysis_results.inventory_days;
                    const dd_curr = statusData.analysis_results.debtor_days;
                    const id_prev = statusData.analysis_results.inventory_days_ly;
                    const dd_prev = statusData.analysis_results.debtor_days_ly;

                    if (id_curr != null && dd_curr != null && id_prev != null && dd_prev != null) {
                      const curr_cycle = id_curr + dd_curr;
                      const prev_cycle = id_prev + dd_prev;
                      if (curr_cycle > prev_cycle) {
                        return 'Verdict: Cash flow is taking longer to cycle back into the bank account compared to last year. This directly drives the current liquidity constraints.';
                      } else {
                        return 'Verdict: Operational cash cycle is highly efficient, optimizing cash generation despite macro liquidity indicators.';
                      }
                    }
                    return 'Verdict: Insufficient data to calculate YoY cash cycle efficiency.';
                  })()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Cash Flow Statement */}
        {statusData?.status === 'COMPLETED' && statusData?.analysis_results && (
          <div className="brutalist-panel p-8 mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-300">
            <h3 className="text-xl font-black uppercase tracking-tight text-brutalist-dark mb-6 border-b-4 border-brutalist-dark pb-4">Statement of Cash Flows</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {/* Section A: OCF */}
              <div className="bg-white border-4 border-brutalist-dark p-5 shadow-[4px_4px_0px_0px_#1A1A1A] flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest bg-brutalist-dark text-white inline-block px-2 py-1">Operating</h4>
                  <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                    Operating Cash Flow
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                      Calculated as: Net Cash Flow from Operating Activities
                    </div>
                  </div>
                  <div className={`text-2xl font-black tracking-tighter ${statusData.analysis_results.operating_cash_flow_cr < 0 ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                    {statusData.analysis_results.operating_cash_flow_cr != null ? `₹${Number(statusData.analysis_results.operating_cash_flow_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                  {statusData.analysis_results.operating_cash_flow_cr_prev != null && (
                    <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. ₹{Number(statusData.analysis_results.operating_cash_flow_cr_prev).toFixed(2)} cr (LY)
                      {statusData.analysis_results.operating_cash_flow_cr > statusData.analysis_results.operating_cash_flow_cr_prev ? ' [↑ Strong Cash Gen]' : ''}
                    </div>
                  )}
                </div>
                <div className="mt-4 pt-3 border-t-2 border-dashed border-brutalist-dark">
                  <div className="text-xs font-medium text-brutalist-dark uppercase tracking-wider">
                    ↳ Pre-Working Capital: {statusData.analysis_results.operating_profit_pre_wc_cr != null ? `₹${Number(statusData.analysis_results.operating_profit_pre_wc_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                </div>
              </div>

              {/* Section B: ICF */}
              <div className="bg-white border-4 border-brutalist-dark p-5 shadow-[4px_4px_0px_0px_#1A1A1A] flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest bg-brutalist-dark text-white inline-block px-2 py-1">Investing</h4>
                  <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                    Investing Cash Flow
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                      Calculated as: Net Cash Flow used in/from Investing Activities
                    </div>
                  </div>
                  <div className={`text-2xl font-black tracking-tighter ${statusData.analysis_results.investing_cash_flow_cr < 0 ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                    {statusData.analysis_results.investing_cash_flow_cr != null ? `₹${Number(statusData.analysis_results.investing_cash_flow_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                  {statusData.analysis_results.investing_cash_flow_cr_prev != null && (
                    <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. ₹{Number(statusData.analysis_results.investing_cash_flow_cr_prev).toFixed(2)} cr (LY)
                    </div>
                  )}
                </div>
                <div className="mt-4 pt-3 border-t-2 border-dashed border-brutalist-dark">
                  <div className="text-xs font-medium text-brutalist-dark uppercase tracking-wider">
                    ↳ CapEx: {statusData.analysis_results.capex_cr != null ? `₹${Number(statusData.analysis_results.capex_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                </div>
              </div>

              {/* Section C: FCF */}
              <div className="bg-white border-4 border-brutalist-dark p-5 shadow-[4px_4px_0px_0px_#1A1A1A] flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-black text-brutalist-dark mb-2 uppercase tracking-widest bg-brutalist-dark text-white inline-block px-2 py-1">Financing</h4>
                  <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 group relative cursor-help flex w-max items-center">
                    Financing Cash Flow
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
                      Calculated as: Net Cash Flow from/used in Financing Activities
                    </div>
                  </div>
                  <div className={`text-2xl font-black tracking-tighter ${statusData.analysis_results.financing_cash_flow_cr < 0 ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                    {statusData.analysis_results.financing_cash_flow_cr != null ? `₹${Number(statusData.analysis_results.financing_cash_flow_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                  {statusData.analysis_results.financing_cash_flow_cr_prev != null && (
                    <div className="text-xs text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. ₹{Number(statusData.analysis_results.financing_cash_flow_cr_prev).toFixed(2)} cr (LY)
                    </div>
                  )}
                </div>
                <div className="mt-4 pt-3 border-t-2 border-dashed border-brutalist-dark">
                  <div className="text-xs font-medium text-brutalist-dark uppercase tracking-wider">
                    ↳ Debt: {statusData.analysis_results.proceeds_borrowings_cr != null ? `₹${Number(statusData.analysis_results.proceeds_borrowings_cr).toFixed(2)}` : 'N/A'} In / {statusData.analysis_results.repayment_borrowings_cr != null ? `₹${Number(statusData.analysis_results.repayment_borrowings_cr).toFixed(2)}` : 'N/A'} Out
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Line Highlight Block */}
            <div className="bg-[#F2EBE3] border-4 border-brutalist-dark p-6 shadow-inner">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                <div>
                  <h4 className="text-sm font-black text-brutalist-dark mb-1 uppercase tracking-widest">Free Cash Flow (FCF)</h4>
                  <p className="text-xs font-bold font-mono text-stone-500">Operating Cash Flow - Absolute CapEx</p>
                </div>
                <div className="text-right">
                  <div className={`text-5xl font-black tracking-tighter ${statusData.analysis_results.free_cash_flow_cr > 0 ? 'text-[#2E6F40]' : statusData.analysis_results.free_cash_flow_cr < 0 ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                    {statusData.analysis_results.free_cash_flow_cr != null ? `₹${Number(statusData.analysis_results.free_cash_flow_cr).toFixed(2)} cr` : 'N/A'}
                  </div>
                  {statusData.analysis_results.free_cash_flow_cr_prev != null && (
                    <div className="text-sm text-stone-500 uppercase tracking-wider mt-1 font-mono font-bold">
                      vs. ₹{Number(statusData.analysis_results.free_cash_flow_cr_prev).toFixed(2)} cr (LY)
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-6 pt-4 border-t-4 border-brutalist-dark">
                <p className="text-brutalist-dark font-black text-sm uppercase tracking-widest leading-relaxed">
                  {statusData.analysis_results.free_cash_flow_cr != null ? (
                    statusData.analysis_results.free_cash_flow_cr > 0 
                      ? 'Verdict: Core operations comfortably generate real cash surplus after supporting expansion needs.'
                      : 'Verdict: Heavy reinvestment cycle or operational cash gap requiring external financing fallback.'
                  ) : 'Verdict: Insufficient data to calculate Free Cash Flow.'}
                </p>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
