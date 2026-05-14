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

  useEffect(() => {
    let interval;
    if (documentId && (!statusData || statusData.status !== 'COMPLETED' && statusData.status !== 'FAILED')) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${documentId}`);
          setStatusData(res.data);
        } catch (e) {
          console.error("Polling error", e);
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
    let colorClass = "bg-slate-700 text-slate-300";
    if (verdict === "GOOD") colorClass = "bg-fintech-success text-white";
    if (verdict === "BAD") colorClass = "bg-fintech-danger text-white";
    if (verdict === "NEUTRAL") colorClass = "bg-fintech-warning text-white";

    return (
      <div className={`px-4 py-2 rounded-full font-bold shadow-lg flex items-center gap-2 ${colorClass}`}>
        {verdict === "GOOD" ? <TrendingUp size={20} /> : verdict === "BAD" ? <TrendingDown size={20} /> : <Activity size={20} />}
        {verdict} ({(confidence * 100).toFixed(0)}% Confidence)
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-fintech-dark text-slate-200 font-sans selection:bg-fintech-accent selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-fintech-accent to-blue-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Activity className="text-white" size={20} />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              AI Financial Results Analyzer
            </h1>
          </div>
          <div className="text-sm text-slate-500 font-medium tracking-wide">
            100% NON-LLM ARCHITECTURE
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        
        {/* Top Section: Upload & Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Upload Panel */}
          <div className="lg:col-span-1">
            <div className="glass-panel p-6 h-full flex flex-col">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <FileText className="text-fintech-accent" size={20} />
                Upload Results PDF
              </h2>
              
              <div 
                className={`flex-1 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-8 transition-all duration-300 ${
                  isDragging ? 'border-fintech-accent bg-blue-900/10' : 'border-slate-700 bg-slate-800/30 hover:border-slate-500 hover:bg-slate-800/50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <Upload className={`mb-4 ${isDragging ? 'text-fintech-accent' : 'text-slate-500'}`} size={40} />
                <p className="text-sm text-slate-400 text-center mb-2">
                  Drag and drop your CA-firm PDF here, or
                </p>
                <label className="cursor-pointer bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
                  Browse Files
                  <input type="file" className="hidden" accept="application/pdf" onChange={(e) => handleFileSelection(e.target.files[0])} />
                </label>
                {file && (
                  <div className="mt-4 text-sm font-medium text-fintech-accent bg-blue-900/20 px-3 py-1 rounded-full truncate max-w-full">
                    {file.name}
                  </div>
                )}
              </div>
              
              {error && <div className="mt-4 text-fintech-danger text-sm flex items-center gap-1"><AlertTriangle size={16}/> {error}</div>}
              
              <button 
                onClick={uploadFile}
                disabled={!file || (statusData && statusData.status !== 'FAILED')}
                className="mt-6 w-full py-3 px-4 bg-gradient-to-r from-fintech-accent to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-lg font-semibold shadow-lg shadow-blue-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {statusData && statusData.status !== 'FAILED' ? 'Processing...' : 'Analyze Document'}
              </button>
            </div>
          </div>

          {/* Processing Status & Quick Metrics */}
          <div className="lg:col-span-2">
            <div className="glass-panel p-6 h-full">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">Pipeline Status</h2>
                  <p className="text-sm text-slate-400 mt-1">Multi-agent extraction workflow</p>
                </div>
                {statusData?.verdict && renderVerdictBadge(statusData.verdict)}
              </div>

              {/* Status Tracker */}
              <div className="bg-slate-900/50 rounded-lg p-5 border border-slate-700/50 font-mono text-sm max-h-64 overflow-y-auto">
                {statusData?.error_message && (
                  <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-md text-red-400">
                    <strong className="block mb-1">Pipeline Error:</strong>
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
                    if (isFailed && currentIndex === -1) {
                        state = 'failed';
                    } else if (isFailed && currentIndex === idx) {
                        state = 'failed';
                    } else if (currentIndex > idx || currentStatus === 'COMPLETED') {
                        state = 'completed';
                    } else if (currentIndex === idx) {
                        state = 'running';
                    } else if (isFailed && currentIndex < idx) {
                        state = 'aborted';
                    }

                    if (state === 'waiting' && currentStatus !== 'WAITING_FOR_UPLOAD') return null; // hide future steps to keep it clean, or show them grayed out

                    return (
                      <div key={step.id} className="flex items-center gap-3">
                        <div className={`w-2.5 h-2.5 rounded-full ${
                          state === 'completed' ? 'bg-fintech-success' : 
                          state === 'running' ? 'bg-fintech-accent animate-pulse' : 
                          state === 'failed' ? 'bg-fintech-danger' : 
                          'bg-slate-700'
                        }`}></div>
                        <span className={`${
                          state === 'completed' ? 'text-slate-300' : 
                          state === 'running' ? 'text-white font-bold' : 
                          state === 'failed' ? 'text-fintech-danger font-bold' : 
                          'text-slate-600'
                        }`}>
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {statusData?.metadata && (
                  <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-slate-800 text-slate-400">
                    <div>Category: <span className="text-slate-200">{statusData.metadata.document_category || '...'}</span></div>
                    <div>PDF Type: <span className="text-slate-200">{statusData.metadata.pdf_type || '...'}</span></div>
                    <div>Pages: <span className="text-slate-200">{statusData.metadata.total_pages || '...'}</span></div>
                    <div>OCR Req: <span className="text-slate-200">{statusData.metadata.requires_ocr ? 'YES' : 'NO'}</span></div>
                  </div>
                )}
              </div>

              {/* Quick Metrics (Appears when completed) */}
              {statusData?.analysis_results && (
                <div className="grid grid-cols-3 gap-4 mt-6">
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
                    return (
                      <div key={key} className="metric-card bg-gradient-to-br from-slate-800 to-slate-900">
                        <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1 flex items-center gap-2">{icon} {label}</div>
                        <div className={`text-xl font-bold ${isNull ? 'text-slate-500' : isPositive ? 'text-fintech-success' : key === 'net_margin' || key === 'ebitda_margin' ? 'text-white' : 'text-fintech-danger'}`}>
                          {isNull ? 'N/A' : `${val}%`}
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
            <div className="glass-panel p-6 space-y-8">

              {/* Chart 1: Total Income Quarterly Trend */}
              <div>
                <h3 className="text-base font-semibold text-white mb-1">Total Income Trend <span className="text-slate-400 text-xs font-normal">(₹ crores)</span></h3>
                <p className="text-slate-500 text-xs mb-3">Revenue from operations + Other income</p>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={
                      (statusData.metadata?.charts_data?.revenue_trend?.labels || []).map((label, idx) => ({
                        name: label,
                        Income: statusData.metadata.charts_data.revenue_trend.datasets[0].data[idx]
                      }))
                    }>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="name" stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 12}} />
                      <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} width={75}
                        tickFormatter={v => `₹${(v/1000).toFixed(1)}k`} />
                      <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Total Income']} />
                      <Line type="monotone" dataKey="Income" stroke="#3b82f6" strokeWidth={3}
                        dot={{r: 5, fill: '#3b82f6', strokeWidth: 2}} activeDot={{r: 7}} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Net Profit Quarterly Trend */}
              <div>
                <h3 className="text-base font-semibold text-white mb-1">Net Profit (PAT) Trend <span className="text-slate-400 text-xs font-normal">(₹ crores)</span></h3>
                <p className="text-slate-500 text-xs mb-3">Profit after tax — quarterly comparison</p>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={
                      (statusData.metadata?.charts_data?.pat_trend?.labels || []).map((label, idx) => ({
                        name: label,
                        PAT: statusData.metadata.charts_data.pat_trend.datasets[0].data[idx]
                      }))
                    }>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="name" stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 12}} />
                      <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} width={75}
                        tickFormatter={v => `₹${(v/1000).toFixed(1)}k`} />
                      <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Net Profit']} />
                      <Line type="monotone" dataKey="PAT" stroke="#10b981" strokeWidth={3}
                        dot={{r: 5, fill: '#10b981', strokeWidth: 2}} activeDot={{r: 7}} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 3: Margin % Trend */}
              {(statusData.metadata?.charts_data?.margin_trend?.length > 0) && (
                <div>
                  <h3 className="text-base font-semibold text-white mb-1">Margin Trends <span className="text-slate-400 text-xs font-normal">(%)</span></h3>
                  <p className="text-slate-500 text-xs mb-3">Net Margin &amp; EBITDA Margin over quarters</p>
                  <div className="h-44">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={statusData.metadata.charts_data.margin_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis dataKey="name" stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 12}} />
                        <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} width={45}
                          tickFormatter={v => `${v}%`} />
                        <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                          itemStyle={{ color: '#fff' }} formatter={v => [`${v}%`, '']} />
                        <Legend wrapperStyle={{color: '#94a3b8', fontSize: '12px'}} />
                        <Line type="monotone" dataKey="Net Margin" stroke="#10b981" strokeWidth={2}
                          dot={{r: 4}} activeDot={{r: 6}} connectNulls />
                        <Line type="monotone" dataKey="EBITDA Margin" stroke="#f59e0b" strokeWidth={2}
                          strokeDasharray="5 5" dot={{r: 4}} activeDot={{r: 6}} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

            </div>

            {/* AI Summary */}
            <div className="glass-panel p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Analyst Summary</h3>
              {statusData?.nlp_summary && (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-slate-800/50 border-l-4 border-fintech-accent">
                    <h4 className="text-sm font-bold text-slate-300 mb-1 uppercase tracking-wider">Executive Overview</h4>
                    <p className="text-slate-200 leading-relaxed text-sm">{statusData.nlp_summary.executive_summary}</p>
                  </div>
                  
                  <div className="p-4 rounded-lg bg-slate-800/50 border-l-4 border-purple-500">
                    <h4 className="text-sm font-bold text-slate-300 mb-1 uppercase tracking-wider">Retail Investor Context</h4>
                    <p className="text-slate-200 leading-relaxed text-sm">{statusData.nlp_summary.investor_explanation}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div>
                      <h4 className="text-xs font-bold text-fintech-success mb-2 uppercase tracking-wider">Key Highlights</h4>
                      <ul className="space-y-1">
                        {(statusData.nlp_summary.highlights || []).map((h, i) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-1">
                            <CheckCircle size={14} className="text-fintech-success shrink-0 mt-0.5" />
                            <span>{h}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-fintech-danger mb-2 uppercase tracking-wider">Potential Risks</h4>
                      <ul className="space-y-1">
                        {(statusData.nlp_summary.risks || []).map((r, i) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-1">
                            <AlertTriangle size={14} className="text-fintech-danger shrink-0 mt-0.5" />
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

      </main>
    </div>
  );
}

export default App;
