import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, FileText, Upload, AlertTriangle, TrendingUp, BarChart3, Database, FileDigit, Calendar, CheckCircle, DollarSign, TrendingDown, Menu, X, Star, MessageSquare, Loader2, Sparkles } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';
import GlobalAssistant from './components/GlobalAssistant';
import ResearchDashboard from './components/ResearchDashboard';
import ReactMarkdown from 'react-markdown';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api/v1`;

// Extracts a human-readable error message from an axios error.
// Priority: backend detail message → HTTP status meaning → network error → fallback
function parseApiError(e, fallback = "Something went wrong. Please try again.") {
  if (!e) return fallback;

  // Backend returned a structured error response
  const detail = e?.response?.data?.detail || e?.response?.data?.error_message || e?.response?.data?.message;
  if (detail) return String(detail);

  // Map common HTTP status codes to plain messages
  const status = e?.response?.status;
  if (status) {
    if (status === 400) return "Bad request — check your inputs and try again.";
    if (status === 401) return "Unauthorized — please check your credentials.";
    if (status === 403) return "Access denied.";
    if (status === 404) return "Resource not found on the server.";
    if (status === 413) return "File is too large. Please upload a smaller PDF.";
    if (status === 422) return "Invalid data sent — please fill all required fields correctly.";
    if (status === 429) return "Too many requests. Please wait a moment and try again.";
    if (status >= 500) return `Server error (${status}) — the backend encountered an issue. Check Render logs.`;
  }

  // Network-level error (no response received at all)
  if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error') {
    return "Cannot reach the server — check that the backend is deployed and the API URL is correct.";
  }
  if (e?.code === 'ECONNABORTED' || e?.code === 'ERR_CANCELED') {
    return "Request timed out — the server took too long to respond.";
  }

  // Axios or JS error message as last resort
  if (e?.message) return e.message;

  return fallback;
}

// Automatically formats and highlights financial metrics, numbers, and drivers
function formatSummaryText(text) {
  if (!text) return "";

  // Regex to split on metrics, numbers, percentages, currencies and causality indicators
  const regex = new RegExp(
    '(' +
      // Percentages and basis points (e.g., +8%, -5%, 150 bps)
      '(?:[+-]?\\d+(?:\\.\\d+)?%|[+-]?\\d+\\s*(?:bps|basis points))' +
      '|' +
      // Currencies and scale units (e.g., INR 4.2k Cr, Rs. 150 Cr, USD 10M, 500 Cr)
      '(?:(?:INR|Rs\\.?|USD|\\$)\\s*\\d+(?:\\.\\d+)?\\s*[kKmMbB]?(?:\\s*(?:Cr|Crore|Lakh|Mn|Bn|Billion|Million))?|\\b\\d+(?:\\.\\d+)?\\s*(?:Cr|Crore|Lakh|Mn|Bn|Billion|Million)\\b)' +
      '|' +
      // Financial metrics (whole words, case-insensitive/specific)
      '\\b(?:Rev|Revenue|EBITDA|PAT|PBT|EPS|YoY|QoQ|CapEx|Margins?|Vol|Volume|Mgmt|Management|FY\\d{2}|Q[1-4])\\b' +
      '|' +
      // Causality words (whole phrases, case-insensitive)
      '\\b(?:driven by|due to|on account of|led by|offset by|cushioned by|supported by|impacted by|owing to|primarily because)\\b' +
    ')',
    'gi'
  );

  const testRegex = new RegExp(
    '^(?:' +
      '(?:[+-]?\\d+(?:\\.\\d+)?%|[+-]?\\d+\\s*(?:bps|basis points))' +
      '|' +
      '(?:(?:INR|Rs\\.?|USD|\\$)\\s*\\d+(?:\\.\\d+)?\\s*[kKmMbB]?(?:\\s*(?:Cr|Crore|Lakh|Mn|Bn|Billion|Million))?|\\b\\d+(?:\\.\\d+)?\\s*(?:Cr|Crore|Lakh|Mn|Bn|Billion|Million)\\b)' +
      '|' +
      '\\b(?:Rev|Revenue|EBITDA|PAT|PBT|EPS|YoY|QoQ|CapEx|Margins?|Vol|Volume|Mgmt|Management|FY\\d{2}|Q[1-4])\\b' +
      '|' +
      '\\b(?:driven by|due to|on account of|led by|offset by|cushioned by|supported by|impacted by|owing to|primarily because)\\b' +
    ')$',
    'i'
  );

  const parts = text.split(regex);
  if (parts.length === 1) return text;

  return parts.map((part, index) => {
    if (testRegex.test(part)) {
      const lower = part.toLowerCase();
      
      // 1. Causality drivers -> styled slate/gray and underlined decoration
      if (/driven by|due to|on account of|led by|offset by|cushioned by|supported by|impacted by|owing to|primarily because/.test(lower)) {
        return (
          <span key={index} className="font-semibold text-stone-600 underline decoration-dotted decoration-stone-400">
            {part}
          </span>
        );
      }
      
      // 2. Metrics & timeframes -> bold and slate-dark highlight
      if (/^(rev|revenue|ebitda|pat|pbt|eps|yoy|qoq|capex|margins?|vol|volume|mgmt|management|fy\d{2}|q[1-4])$/.test(lower)) {
        return (
          <strong key={index} className="font-extrabold text-[#1a1a1a] tracking-tight bg-stone-100 px-1 rounded border border-stone-200">
            {part}
          </strong>
        );
      }
      
      // 3. Numbers, percentages, currencies -> color-coded based on direction
      const isNegative = lower.includes('-') || lower.includes('down');
      const isPositive = lower.includes('+') || lower.includes('up');
      
      let badgeClass = "font-black";
      if (isPositive) badgeClass += " text-[#2E6F40] bg-[#E8F5E9] px-1 rounded border border-[#C8E6C9]";
      else if (isNegative) badgeClass += " text-[#D32F2F] bg-[#FFEBEE] px-1 rounded border border-[#FFCDD2]";
      else badgeClass += " text-brutalist-dark bg-[#FFFDF0] px-1 rounded border border-yellow-200";
      
      return (
        <span key={index} className={badgeClass}>
          {part}
        </span>
      );
    }
    
    return part;
  });
}

function App() {
  const [file, setFile] = useState(null);
  const [financialUrl, setFinancialUrl] = useState("");
  const [financialUploadType, setFinancialUploadType] = useState("file");
  const [documentId, setDocumentId] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  // Concall Ingestion States
  const [concallFile, setConcallFile] = useState(null);
  const [concallUrl, setConcallUrl] = useState("");
  const [concallUploadType, setConcallUploadType] = useState("file");
  const [concallCompanyName, setConcallCompanyName] = useState("");
  const [concallSector, setConcallSector] = useState("");
  const [customSector, setCustomSector] = useState("");
  const [concallQuarter, setConcallQuarter] = useState("Q4");
  const [concallFiscalYear, setConcallFiscalYear] = useState("FY26");
  const [concallDocumentId, setConcallDocumentId] = useState(null);
  const [concallStatusData, setConcallStatusData] = useState(null);
  const [concallError, setConcallError] = useState(null);
  const [isConcallUploading, setIsConcallUploading] = useState(false);
  const [isConcallCached, setIsConcallCached] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [currentQuery, setCurrentQuery] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);

  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [chatMessages, isChatLoading]);

  // New Interactive Loader States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [activePhaseText, setActivePhaseText] = useState("");
  const [activeTab, setActiveTab] = useState("CONCALL");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeSummaryTab, setActiveSummaryTab] = useState("SUMMARY");
  const [isBackendWakingUp, setIsBackendWakingUp] = useState(false);
  const [coldStartCountdown, setColdStartCountdown] = useState(90);

  const ensureBackendActive = async () => {
    try {
      // Fast check with 2s timeout
      await axios.get(`${API_BASE}/health`, { timeout: 2000 });
      return true;
    } catch (err) {
      setIsBackendWakingUp(true);
      setColdStartCountdown(90);
      
      return new Promise((resolve) => {
        let countdown = 90;
        const countdownInterval = setInterval(() => {
          countdown = Math.max(1, countdown - 1);
          setColdStartCountdown(countdown);
        }, 1000);

        const pollInterval = setInterval(async () => {
          try {
            await axios.get(`${API_BASE}/health`, { timeout: 3000 });
            clearInterval(countdownInterval);
            clearInterval(pollInterval);
            setIsBackendWakingUp(false);
            resolve(true);
          } catch (pollErr) {
            // still down
          }
        }, 4000);
      });
    }
  };

  const [isConcallAnalyzing, setIsConcallAnalyzing] = useState(false);
  const [concallProgress, setConcallProgress] = useState(0);
  const [concallPhaseText, setConcallPhaseText] = useState("");

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
    let timeoutId;
    let isCancelled = false;

    if (statusData?.status === 'TABLE_EXTRACTION') {
      setIsAnalyzing(true);
      setLoadingProgress(0);
      setActivePhaseText("COMPILING FOCUS PAGES...");

      const runProgress = (current) => {
        if (isCancelled) return;
        let nextProgress = current;
        let delay = 300;

        if (current < 45) {
          nextProgress = current + 5;
          delay = 300;
          setActivePhaseText("PARSING TABULAR STRATEGY...");
        } else if (current < 88) {
          nextProgress = current + 2;
          delay = 500;
          setActivePhaseText("MAPPING SEMANTIC SCHEMA OBJECTS...");
        } else if (current < 95) {
          nextProgress = current + 1;
          delay = 1500;
          setActivePhaseText("EXECUTING INFERENCE VERIFICATION...");
        } else {
          nextProgress = current;
          delay = 1000;
        }

        setLoadingProgress(nextProgress);
        timeoutId = setTimeout(() => runProgress(nextProgress), delay);
      };

      runProgress(0);
    } else if (isAnalyzing) {
      isCancelled = true;
      clearTimeout(timeoutId);
      if (statusData?.status === 'NORMALIZING_METRICS' || statusData?.status === 'FINANCIAL_ANALYSIS' || statusData?.status === 'COMPLETED') {
        setLoadingProgress(100);
        setActivePhaseText("HANDING OFF TO CALCULATOR CORE...");
        setTimeout(() => setIsAnalyzing(false), 800);
      } else {
        setIsAnalyzing(false);
      }
    }

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
    };
  }, [statusData?.status, isAnalyzing]);

  useEffect(() => {
    let timeoutId;
    let isCancelled = false;

    if (concallStatusData?.status === 'PENDING') {
      setIsConcallAnalyzing(true);

      const runProgress = (current) => {
        if (isCancelled) return;
        let nextProgress = current;
        let delay = 300;

        if (current < 25) {
          nextProgress = current + 3;
          delay = 400;
          setConcallPhaseText("EXTRACTING TRANSCRIPT TEXT...");
        } else if (current < 55) {
          nextProgress = current + 2;
          delay = 500;
          setConcallPhaseText("UPSERTING TO PINECONE CLUSTER...");
        } else if (current < 80) {
          nextProgress = current + 1;
          delay = 1000;
          setConcallPhaseText("SYNTHESIZING EXECUTIVE SUMMARY & GUIDANCE...");
        } else if (current < 95) {
          nextProgress = current + 1;
          delay = 2000;
          setConcallPhaseText("FINALIZING TAKEAWAYS & RISK MATRIX...");
        } else {
          nextProgress = 95;
          delay = 2000;
          setConcallPhaseText("FINALIZING DASHBOARD INSIGHTS...");
        }

        setConcallProgress(nextProgress);
        timeoutId = setTimeout(() => runProgress(nextProgress), delay);
      };

      runProgress(0);
    } else if (concallStatusData?.status === 'COMPLETED') {
      isCancelled = true;
      clearTimeout(timeoutId);
      setConcallProgress(100);
      setConcallPhaseText("PROCESSING COMPLETE!");
      setTimeout(() => setIsConcallAnalyzing(false), 500);
    } else if (concallStatusData?.status === 'FAILED') {
      isCancelled = true;
      clearTimeout(timeoutId);
      setIsConcallAnalyzing(false);
    }

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
    };
  }, [concallStatusData?.status]);

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
              'CLASSIFYING_PDF': 'Agent 2: PDF Text Extraction',
              'OCR_EXTRACTION': 'Agent 3: OCR Text or Hybrid Check',
              'DOCUMENT_CLASSIFICATION': 'Agent 4: Page Identification (Regex Scoring)',
              'TABLE_EXTRACTION': 'Agent 5: Structured JSON Generation (LLM)',
              'NORMALIZING_METRICS': 'Agent 6: Normalization and Error Handling',
              'FINANCIAL_ANALYSIS': 'Agent 7: Financial Metrics Calculation',
              'NLP_SUMMARIZATION': 'Agent 8: AI Summary Generation',
              'VERDICT_PREDICTION': 'Agent 9: Frontend Visualization',
              'VISUALIZATION_PREP': 'Agent 9: Frontend Visualization',
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

  // Concall Polling
  useEffect(() => {
    let interval;
    if (concallDocumentId && (!concallStatusData || concallStatusData.status !== 'COMPLETED' && concallStatusData.status !== 'FAILED')) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/concall/status/${concallDocumentId}`);
          setConcallStatusData(res.data);
        } catch (e) {
          console.error("Concall polling failed:", e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [concallDocumentId, concallStatusData]);

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
    if (financialUploadType === "file" && !file) return;
    if (financialUploadType === "url" && !financialUrl) return;

    await ensureBackendActive();

    const formData = new FormData();
    if (financialUploadType === "file") {
      formData.append("file", file);
    } else {
      formData.append("url", financialUrl);
    }

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setDocumentId(res.data.document_id);
      setStatusData({ status: res.data.status });
    } catch (e) {
      setError(parseApiError(e, "Upload failed. Ensure backend is running."));
      console.error(e);
    }
  };

  const uploadConcall = async (e) => {
    e.preventDefault();
    if (concallUploadType === "file" && !concallFile) {
      setConcallError("Please select a file.");
      return;
    }
    if (concallUploadType === "url" && !concallUrl) {
      setConcallError("Please provide a URL.");
      return;
    }
    setConcallError(null);
    setIsConcallUploading(true);

    await ensureBackendActive();

    const formData = new FormData();
    if (concallUploadType === "file") {
      formData.append("file", concallFile);
    } else {
      formData.append("url", concallUrl);
    }
    formData.append("company_name", concallCompanyName || "Unknown");
    
    const finalSector = concallSector === "Other" ? (customSector.trim() || "General Corporate") : (concallSector || "General Corporate");
    formData.append("sector", finalSector);
    
    formData.append("quarter", concallQuarter || "Q4");
    formData.append("fiscal_year", concallFiscalYear || "FY26");

    try {
      const res = await axios.post(`${API_BASE}/concall/upload-and-process`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setConcallDocumentId(res.data.document_id);
      // If the backend returned COMPLETED (dedup hit), set status directly
      // so the summary renders immediately without polling.
      if (res.data.status === 'COMPLETED') {
        setIsConcallCached(true);
        const statusRes = await axios.get(`${API_BASE}/concall/status/${res.data.document_id}`);
        setConcallStatusData(statusRes.data);
      } else {
        setIsConcallCached(false);
        setConcallStatusData({ status: res.data.status });
      }
    } catch (e) {
      setConcallError(parseApiError(e, "Upload failed. Please try again."));
      console.error(e);
    } finally {
      setIsConcallUploading(false);
    }
  };

  const sendChatMessage = async (e, directQuery = null) => {
    if (e && e.preventDefault) e.preventDefault();
    const queryText = directQuery || currentQuery;
    if (!queryText.trim() || !concallDocumentId) return;

    const userMsg = { role: "user", content: queryText };
    setChatMessages(prev => [...prev, userMsg]);
    setCurrentQuery("");
    setIsChatLoading(true);

    await ensureBackendActive();

    try {
      const res = await axios.post(`${API_BASE}/concall/chat`, {
        document_id: concallDocumentId,
        query: userMsg.content
      });
      const aiMsg = { role: "ai", content: res.data.answer, sources: res.data.sources };
      setChatMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      console.error(e);
      const errMsg = parseApiError(e, "Failed to get a response. Please try again.");
      setChatMessages(prev => [...prev, { role: "ai", content: `Error: ${errMsg}` }]);
    } finally {
      setIsChatLoading(false);
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
        {verdict}
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
            <h1 className="text-xl sm:text-2xl font-black tracking-tight uppercase flex items-center gap-1.5 leading-none">
              <span>Hitman</span>
              <span className="font-serif italic text-brutalist-green lowercase capitalize mt-1 sm:mt-0">Finance.</span>
            </h1>
          </div>
          {/* Desktop Nav (Replaces the subtitle) */}
          <div className="hidden md:flex items-center gap-8 text-sm text-brutalist-dark font-mono uppercase tracking-widest font-black">
            <button onClick={() => setActiveTab('CONCALL')} className={`transition-colors hover:text-brutalist-orange ${activeTab === 'CONCALL' ? 'text-[#991B1B] underline decoration-4 underline-offset-4' : ''}`}>Earnings Calls</button>
            <button onClick={() => setActiveTab('RESULTS')} className={`transition-colors hover:text-brutalist-orange ${activeTab === 'RESULTS' ? 'text-brutalist-orange underline decoration-4 underline-offset-4' : ''}`}>Results Analysis</button>
            <button onClick={() => setActiveTab('RESEARCH')} className={`transition-colors hover:text-brutalist-orange ${activeTab === 'RESEARCH' ? 'text-[#2E6F40] underline decoration-4 underline-offset-4' : ''}`}>Equity Research</button>
          </div>

          {/* Mobile Hamburger Toggle */}
          <div className="md:hidden flex items-center">
            <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="text-brutalist-dark p-2">
              {isMobileMenuOpen ? <X size={28} /> : <Menu size={28} />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu (Compact Floating Box) */}
        {isMobileMenuOpen && (
          <div className="md:hidden bg-[#F2EBE3] border-4 border-brutalist-dark absolute top-full right-4 mt-2 w-56 flex flex-col shadow-[4px_4px_0px_0px_#1A1A1A]">
            <button onClick={() => { setActiveTab('CONCALL'); setIsMobileMenuOpen(false); }} className={`px-4 py-3 text-sm font-black uppercase tracking-widest border-b-4 border-brutalist-dark text-left ${activeTab === 'CONCALL' ? 'bg-[#991B1B] text-white' : 'text-brutalist-dark hover:bg-stone-200'}`}>Earnings Calls</button>
            <button onClick={() => { setActiveTab('RESULTS'); setIsMobileMenuOpen(false); }} className={`px-4 py-3 text-sm font-black uppercase tracking-widest border-b-4 border-brutalist-dark text-left ${activeTab === 'RESULTS' ? 'bg-brutalist-orange text-brutalist-dark' : 'text-brutalist-dark hover:bg-stone-200'}`}>Results Analysis</button>
            <button onClick={() => { setActiveTab('RESEARCH'); setIsMobileMenuOpen(false); }} className={`px-4 py-3 text-sm font-black uppercase tracking-widest text-left ${activeTab === 'RESEARCH' ? 'bg-[#2E6F40] text-white' : 'text-brutalist-dark hover:bg-stone-200'}`}>Equity Research</button>
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-10 space-y-12">

        {activeTab === 'RESEARCH' && <ResearchDashboard ensureBackendActive={ensureBackendActive} />}



        {activeTab === 'RESULTS' && (
          <div className="space-y-12">
            
            {/* Results Header */}
            <div className="brutalist-panel p-8 text-center bg-[#F2EBE3]">
              <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter mb-4 leading-none text-brutalist-orange">
                AI Financial Results Analysis
              </h2>
              <p className="text-brutalist-dark font-mono text-sm max-w-2xl mx-auto font-bold">
                Upload any company's quarterly or annual financial results PDF. Our AI agents will instantly extract metrics, normalize data, and generate an institutional-grade summary.
              </p>
            </div>


            {/* Top Section: Upload & Status */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

              {/* Upload Panel */}
              <div className="lg:col-span-1">
                <div className="brutalist-panel p-8 h-full flex flex-col">
                  <h2 className="text-lg font-black uppercase tracking-tight text-brutalist-dark mb-4 flex items-center gap-2">
                    <FileText className="text-brutalist-orange" size={24} strokeWidth={3} />
                    Provide Results PDF
                  </h2>
                  
                  <div className="flex gap-2 mb-4">
                    <button
                      onClick={() => setFinancialUploadType("file")}
                      className={`flex-1 py-2 text-xs font-bold font-mono uppercase border-2 border-brutalist-dark ${financialUploadType === "file" ? "bg-brutalist-dark text-white" : "bg-white text-brutalist-dark hover:bg-stone-100"}`}
                    >
                      Upload File
                    </button>
                    <button
                      onClick={() => setFinancialUploadType("url")}
                      className={`flex-1 py-2 text-xs font-bold font-mono uppercase border-2 border-brutalist-dark ${financialUploadType === "url" ? "bg-brutalist-dark text-white" : "bg-white text-brutalist-dark hover:bg-stone-100"}`}
                    >
                      Enter URL
                    </button>
                  </div>

                  {financialUploadType === "file" ? (
                    <div
                      className={`flex-1 border-4 border-dashed border-brutalist-dark rounded-none flex flex-col items-center justify-center p-8 transition-all duration-300 ${isDragging ? 'bg-brutalist-orange/20' : 'bg-white hover:bg-stone-50'
                        }`}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                    >
                      <Upload className={`mb-4 ${isDragging ? 'text-brutalist-orange' : 'text-brutalist-dark'}`} size={40} strokeWidth={2} />
                      <label className="cursor-pointer brutalist-button px-6 py-2 text-sm">
                        Upload Financial Results PDF here
                        <input type="file" className="hidden" accept="application/pdf" onChange={(e) => handleFileSelection(e.target.files[0])} />
                      </label>
                      {file && (
                        <div className="mt-6 text-sm font-bold text-brutalist-green bg-brutalist-green/10 border-2 border-brutalist-green px-4 py-2 rounded-none truncate max-w-full">
                          {file.name}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex-1 border-4 border-dashed border-brutalist-dark rounded-none flex flex-col items-center justify-center p-8 bg-white">
                      <input
                        type="url"
                        placeholder="https://example.com/results.pdf"
                        value={financialUrl}
                        onChange={(e) => setFinancialUrl(e.target.value)}
                        className="w-full p-4 border-2 border-brutalist-dark focus:outline-none focus:ring-2 focus:ring-brutalist-orange font-mono text-sm"
                      />
                    </div>
                  )}

                  {error && <div className="mt-4 text-brutalist-orange font-bold text-sm flex items-center gap-2 uppercase tracking-wide border-2 border-brutalist-orange p-2"><AlertTriangle size={20} /> {error}</div>}

                  <button
                    onClick={uploadFile}
                    disabled={(financialUploadType === 'file' ? !file : !financialUrl) || (statusData && !['FAILED', 'COMPLETED'].includes(statusData.status))}
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
                        { id: 'CLASSIFYING_PDF', label: 'Agent 2: PDF Text Extraction' },
                        { id: 'OCR_EXTRACTION', label: 'Agent 3: OCR Text or Hybrid Check' },
                        { id: 'DOCUMENT_CLASSIFICATION', label: 'Agent 4: Page Identification (Regex Scoring)' },
                        { id: 'TABLE_EXTRACTION', label: 'Agent 5: Structured JSON Generation (LLM)' },
                        { id: 'NORMALIZING_METRICS', label: 'Agent 6: Normalization and Error Handling' },
                        { id: 'FINANCIAL_ANALYSIS', label: 'Agent 7: Financial Metrics Calculation' },
                        { id: 'NLP_SUMMARIZATION', label: 'Agent 8: AI Summary Generation' },
                        { id: 'VERDICT_PREDICTION', label: 'Agent 9: Frontend Visualization', hidden: true },
                        { id: 'VISUALIZATION_PREP', label: 'Agent 9: Frontend Visualization' },
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
                        if (step.hidden) return null;

                        return (
                          <div key={step.id} className="flex flex-col gap-2">
                            <div className="flex items-center gap-4">
                              <div className={`w-5 h-5 border-2 border-brutalist-dark flex items-center justify-center font-black text-sm ${state === 'completed' ? 'bg-white text-brutalist-dark' :
                                state === 'running' ? 'bg-brutalist-orange text-brutalist-dark' :
                                  state === 'failed' ? 'bg-brutalist-orange text-white' :
                                    'bg-transparent text-transparent'
                                }`}>
                                {state === 'completed' && '✅'}
                                {state === 'running' && '>'}
                                {state === 'failed' && '!'}
                              </div>
                              <span className={`uppercase tracking-wider text-xs font-bold ${state === 'completed' ? 'text-brutalist-dark' :
                                state === 'running' ? 'text-brutalist-orange text-sm' :
                                  state === 'failed' ? 'text-brutalist-orange line-through decoration-2' :
                                    'text-brutalist-dark/40'
                                }`}>
                                {step.label}
                              </span>
                            </div>

                            {/* Inline Agent 5 Loader */}
                            {step.id === 'TABLE_EXTRACTION' && state === 'running' && (
                              <div className="ml-9 p-3 border-2 border-brutalist-dark bg-stone-50 font-mono text-[10px] sm:text-xs max-w-sm">
                                <div className="flex justify-end mb-1">
                                  <span className="font-bold">{loadingProgress}%</span>
                                </div>
                                <div className="w-full h-3 border-2 border-brutalist-dark bg-white relative overflow-hidden">
                                  <div className="absolute top-0 left-0 h-full bg-brutalist-orange transition-all duration-300" style={{ width: `${loadingProgress}%` }}>
                                    <div className="w-full h-full opacity-20 bg-[repeating-linear-gradient(45deg,transparent,transparent_5px,#000_5px,#000_10px)]"></div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {statusData?.metadata && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 pt-4 border-t-4 border-brutalist-dark text-brutalist-dark font-mono text-xs uppercase tracking-widest font-bold bg-white p-4 border-x-4 border-b-4">
                        <div>Category: <span className="text-brutalist-green">{statusData.metadata.document_category || '...'}</span></div>
                        <div>PDF Type: <span className="text-brutalist-green">{statusData.metadata.pdf_type || '...'}</span></div>
                        <div>Pages: <span className="text-brutalist-green">{statusData.metadata.total_pages || '...'}</span></div>
                        <div>OCR Req: <span className="text-brutalist-orange">{statusData.metadata.requires_ocr ? 'YES' : 'NO'}</span></div>
                      </div>
                    )}
                  </div>

                  {/* Quick Metrics (Appears when completed) */}
                  {statusData?.analysis_results && (
                    <div className="mt-6">


                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-8">
                      {[
                        {
                          label: 'REV YOY',
                          value: statusData.analysis_results.yoy_growth,
                          unit: '%',
                          isPercent: true,
                          subtitle: statusData.analysis_results.qoq_growth != null 
                            ? `QoQ: ${statusData.analysis_results.qoq_growth > 0 ? '+' : ''}${statusData.analysis_results.qoq_growth}%`
                            : 'Top-line Growth',
                          icon: <TrendingUp size={14} />
                        },
                        {
                          label: 'PAT YOY',
                          value: statusData.analysis_results.pat_yoy,
                          unit: '%',
                          isPercent: true,
                          subtitle: statusData.analysis_results.pat_qoq != null
                            ? `QoQ: ${statusData.analysis_results.pat_qoq > 0 ? '+' : ''}${statusData.analysis_results.pat_qoq}%`
                            : 'Net Profit Growth',
                          icon: <Activity size={14} />
                        },
                        {
                          label: 'EBITDA MARGIN',
                          value: statusData.analysis_results.ebitda_margin,
                          unit: '%',
                          isPercent: false,
                          subtitle: 'Core Operational Margin',
                          icon: <BarChart3 size={14} />
                        },
                        {
                          label: 'NET MARGIN',
                          value: statusData.analysis_results.net_margin,
                          unit: '%',
                          isPercent: false,
                          subtitle: 'PAT / Total Income',
                          icon: <DollarSign size={14} />
                        },
                        {
                          label: 'EPS YOY',
                          value: statusData.analysis_results.eps_yoy,
                          unit: '%',
                          isPercent: true,
                          subtitle: statusData.analysis_results.basic_eps != null
                            ? `Basic EPS: ₹${statusData.analysis_results.basic_eps}`
                            : 'Per-Share Growth',
                          icon: <TrendingUp size={14} />
                        },
                        {
                          label: 'REVENUE (Q)',
                          value: statusData.analysis_results.total_income_q_cr,
                          unit: ' Cr',
                          prefix: '₹',
                          isPercent: false,
                          subtitle: statusData.analysis_results.pat_q_current_cr != null
                            ? `PAT: ₹${typeof statusData.analysis_results.pat_q_current_cr === 'number' ? statusData.analysis_results.pat_q_current_cr.toFixed(2) : statusData.analysis_results.pat_q_current_cr} Cr`
                            : 'Quarterly Scale',
                          icon: <FileDigit size={14} />
                        },
                      ].map(({ label, value, unit, prefix, isPercent, subtitle, icon }) => {
                        const isNull = value === null || value === undefined;
                        const isPositive = isPercent && value > 0;
                        const isNegative = isPercent && value < 0;
                        const formattedVal = typeof value === 'number' ? Number(value.toFixed(2)).toLocaleString() : value;
                        return (
                          <div key={label} className="brutalist-card p-4 flex flex-col justify-between">
                            <div>
                              <div className="text-brutalist-dark text-xs font-bold font-mono uppercase tracking-widest mb-1 flex items-center gap-2 border-b-2 border-brutalist-dark pb-2 mb-2">
                                {icon} {label}
                              </div>
                              <div className={`text-2xl font-black tracking-tighter ${isNull ? 'text-brutalist-dark/40' : isPositive ? 'text-[#2E6F40]' : isNegative ? 'text-[#D95A2B]' : 'text-brutalist-dark'}`}>
                                {isNull 
                                  ? 'N/A' 
                                  : `${prefix || ''}${formattedVal}${unit || ''}${isPositive ? ' ↑' : isNegative ? ' ↓' : ''}`
                                }
                              </div>
                            </div>
                            <div className="text-sm font-mono font-bold text-brutalist-dark/90 tracking-tight mt-2 border-t border-brutalist-dark/20 pt-1.5">
                              {subtitle}
                            </div>
                          </div>
                        );
                      })}
                    </div>
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
                          <XAxis dataKey="name" stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace' }} />
                          <YAxis stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace' }} width={75}
                            tickFormatter={v => `₹${(v / 1000).toFixed(1)}k`} />
                          <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                            itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Total Income']} />
                          <Line type="monotone" dataKey="Income" stroke="#D95A2B" strokeWidth={4}
                            dot={{ r: 6, fill: '#D95A2B', strokeWidth: 2 }} activeDot={{ r: 8 }} />
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
                          <XAxis dataKey="name" stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace' }} />
                          <YAxis stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace' }} width={75}
                            tickFormatter={v => `₹${(v / 1000).toFixed(1)}k`} />
                          <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                            itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`₹${v.toLocaleString()} cr`, 'Net Profit']} />
                          <Line type="monotone" dataKey="PAT" stroke="#2E6F40" strokeWidth={4}
                            dot={{ r: 6, fill: '#2E6F40', strokeWidth: 2 }} activeDot={{ r: 8 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Chart 3: Margin % Trend */}
                  {(statusData.metadata?.charts_data?.margin_trend?.length > 0) && (
                    <div>
                  <h3 className="text-lg font-black tracking-tight uppercase text-brutalist-dark mb-1">Margin Trends <span className="font-mono text-xs font-bold tracking-widest">(%)</span></h3>
                  <p className="text-brutalist-dark text-xs mb-3 font-mono">OPM (Operating Profit Margin) over quarters</p>
                  <div className="h-44 border-4 border-brutalist-dark p-2 bg-white">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={statusData.metadata.charts_data.margin_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" vertical={false} />
                        <XAxis dataKey="name" stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace' }} />
                        <YAxis stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace' }} width={45}
                          tickFormatter={v => `${v}%`} />
                        <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                          itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`${v}%`, '']} />
                        <Legend wrapperStyle={{ color: '#1A1A1A', fontSize: '12px', fontWeight: 'bold', fontFamily: 'monospace' }} />
                        <Line type="monotone" dataKey="OPM" stroke="#D95A2B" strokeWidth={4}
                          dot={{ r: 6, fill: '#D95A2B', strokeWidth: 2 }} activeDot={{ r: 8 }} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Chart 4: EPS Trend */}
              {(statusData.metadata?.charts_data?.eps_trend?.labels?.length > 0) && (
                <div>
                  <h3 className="text-lg font-black tracking-tight uppercase text-brutalist-dark mb-1">Basic EPS Trend <span className="font-mono text-xs font-bold tracking-widest">(₹)</span></h3>
                  <p className="text-brutalist-dark text-xs mb-3 font-mono">Earnings Per Share over quarters</p>
                  <div className="h-44 border-4 border-brutalist-dark p-2 bg-white">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={
                        (statusData.metadata.charts_data.eps_trend.labels || []).map((label, idx) => ({
                          name: label,
                          EPS: statusData.metadata.charts_data.eps_trend.datasets[0].data[idx]
                        }))
                      }>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" vertical={false} />
                        <XAxis dataKey="name" stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace' }} />
                        <YAxis stroke="#1A1A1A" tick={{ fill: '#1A1A1A', fontSize: 11, fontWeight: 'bold', fontFamily: 'monospace' }} width={45}
                          tickFormatter={v => `₹${v.toFixed(1)}`} />
                        <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#1A1A1A', borderWidth: '4px', borderRadius: '0' }}
                          itemStyle={{ color: '#1A1A1A', fontWeight: 'bold' }} formatter={v => [`₹${v}`, 'Basic EPS']} />
                        <Line type="monotone" dataKey="EPS" stroke="#1A1A1A" strokeWidth={4}
                          dot={{ r: 6, fill: '#1A1A1A', strokeWidth: 2 }} activeDot={{ r: 8 }} connectNulls />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

                </div>

                {/* AI Summary */}
                <div className="brutalist-panel p-8">
                  <h3 className="text-xl font-black uppercase tracking-tight text-brutalist-dark mb-6 border-b-4 border-brutalist-dark pb-4 flex items-center gap-2">
                    <Sparkles size={24} className="text-brutalist-orange" /> Key Financial Takeaways
                  </h3>
                  {statusData?.nlp_summary && (
                    <div className="p-6 border-4 border-brutalist-dark bg-white shadow-[4px_4px_0px_0px_#1A1A1A]">
                      {Array.isArray(statusData.nlp_summary.executive_summary) && statusData.nlp_summary.executive_summary.length > 0 ? (
                        <ul className="space-y-3">
                          {statusData.nlp_summary.executive_summary.map((pt, i) => (
                            <li key={i} className="text-brutalist-dark font-medium leading-relaxed flex items-start gap-3">
                              <span className="bg-brutalist-dark text-white font-black text-xs px-2 py-0.5 mt-0.5 rounded-none shrink-0">{i + 1}</span>
                              <span>{pt}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-brutalist-dark font-medium leading-relaxed">{statusData.nlp_summary.executive_summary || "No summary available."}</p>
                      )}

                      {/* Render legacy secondary fields if present for older processed docs */}
                      {(statusData.nlp_summary.highlights?.length > 0 || statusData.nlp_summary.risks?.length > 0) && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-6 border-t-4 border-brutalist-dark pt-6">
                          {statusData.nlp_summary.highlights?.length > 0 && (
                            <div>
                              <h4 className="text-sm font-black text-brutalist-green mb-3 uppercase tracking-widest">Key Highlights</h4>
                              <ul className="space-y-2">
                                {statusData.nlp_summary.highlights.map((h, i) => (
                                  <li key={i} className="text-sm font-medium text-brutalist-dark flex items-start gap-2">
                                    <CheckCircle size={18} className="text-brutalist-green shrink-0 mt-0.5" strokeWidth={3} />
                                    <span>{h}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {statusData.nlp_summary.risks?.length > 0 && (
                            <div>
                              <h4 className="text-sm font-black text-brutalist-orange mb-3 uppercase tracking-widest">Potential Risks</h4>
                              <ul className="space-y-2">
                                {statusData.nlp_summary.risks.map((r, i) => (
                                  <li key={i} className="text-sm font-medium text-brutalist-dark flex items-start gap-2">
                                    <AlertTriangle size={18} className="text-brutalist-orange shrink-0 mt-0.5" strokeWidth={3} />
                                    <span>{r}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
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
                          <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-56 sm:w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
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
                          <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-56 sm:w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
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
                            <div className="pointer-events-none absolute left-0 bottom-full mb-1 w-56 sm:w-64 opacity-0 transition-opacity group-hover:opacity-100 bg-brutalist-dark text-white text-[10px] p-2 z-50 normal-case shadow-[2px_2px_0px_0px_#D95A2B] border-2 border-brutalist-dark">
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

          </div>
        )}

            {activeTab === 'CONCALL' && (
              <div className={`${concallStatusData?.status === 'COMPLETED' ? 'max-w-7xl' : 'max-w-3xl'} mx-auto w-full space-y-8`}>
                {/* Concall Header */}
                <div className="brutalist-panel p-8 text-center bg-[#F2EBE3]">
                  <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter mb-4 leading-none text-[#991B1B]">
                    Earnings Call Intelligence
                  </h2>
                  <p className="text-brutalist-dark font-mono text-sm max-w-2xl mx-auto font-bold">
                    Upload earnings call transcripts. Our vector database maps the semantic context, allowing you to instantly interrogate management's commentary and uncover hidden risks.
                  </p>
                </div>
            <div className="border-t-4 border-black my-8"></div>

            {concallStatusData?.status === 'COMPLETED' ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start animate-in fade-in duration-700">
                {isConcallCached && (
                  <div className="lg:col-span-12 bg-brutalist-green text-white border-4 border-brutalist-dark p-3 text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-[4px_4px_0px_0px_#1A1A1A]">
                    <Database size={20} />
                    Instant Load: Summary retrieved from cache
                  </div>
                )}
                
                {/* Left Column: Chat Interface */}
                <div className="lg:col-span-5">
                  <div className="brutalist-panel flex flex-col border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] bg-[#FDFBF7] h-[550px]">
                    <div className="bg-[#1A1A1A] text-white p-3 sm:p-4 font-black uppercase tracking-widest border-b-4 border-brutalist-dark flex justify-between items-center gap-2">
                      <span className="truncate pr-4 text-xs sm:text-sm">Chat: {concallFile ? concallFile.name : 'Transcript'}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button 
                          onClick={() => { setChatMessages([]); setCurrentQuery(""); }} 
                          className="text-[9px] sm:text-[10px] uppercase font-black bg-white text-black px-2 py-0.5 border border-black hover:bg-stone-100 transition-colors"
                        >
                          [ Reset Chat ]
                        </button>
                        <button 
                          onClick={() => { setConcallStatusData(null); setConcallDocumentId(null); setChatMessages([]); setConcallFile(null) }} 
                          className="text-[9px] sm:text-[10px] uppercase font-black bg-white text-black px-2 py-0.5 border border-black hover:bg-[#991B1B] hover:text-white transition-colors"
                        >
                          [ New Session ]
                        </button>
                      </div>
                    </div>

                    <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-6">
                      {chatMessages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-4 my-auto">
                          <div className="p-3 bg-[#991B1B]/10 rounded-full text-[#991B1B] border-2 border-[#991B1B]">
                            <MessageSquare size={28} />
                          </div>
                          
                          {/* Big Company Heading */}
                          <div>
                            <h3 className="text-2xl font-black uppercase tracking-tighter text-brutalist-dark leading-none">
                              {concallCompanyName || 'Loaded Company'}
                            </h3>
                            <p className="text-[10px] font-mono font-black uppercase text-[#991B1B] tracking-widest mt-1">
                              Start your investigation
                            </p>
                          </div>

                          <p className="text-xs sm:text-sm font-black uppercase tracking-wider text-stone-700 font-mono max-w-xs leading-normal">
                            Select a quick query below or type your own question in the input bar.
                          </p>
                          <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
                            {[
                              "What is the revenue and margin guidance?",
                              "What are the key growth drivers and collaborations?",
                              "What are the major risks and segment headwinds?",
                            ].map((prompt, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => sendChatMessage(null, prompt)}
                                className="text-left bg-white hover:bg-stone-50 border-2 border-black p-2.5 font-mono text-[10px] text-brutalist-dark hover:shadow-[2px_2px_0px_0px_#000000] hover:-translate-y-0.5 hover:-translate-x-0.5 transition-all leading-normal"
                              >
                                💬 {prompt}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {chatMessages.map((msg, idx) => (
                        <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                          {/* Speaker Badge */}
                          <span className={`text-[9px] font-mono font-black uppercase mb-1 px-1.5 py-0.5 border border-black shadow-[1px_1px_0px_0px_#000000] ${msg.role === 'user' ? 'bg-[#991B1B] text-white' : 'bg-stone-200 text-black'}`}>
                            {msg.role === 'user' ? 'User' : 'AI Assistant'}
                          </span>
                          
                          <div className={`p-3 max-w-[85%] border-2 border-black font-mono text-xs sm:text-sm shadow-[2px_2px_0px_0px_#000000] ${msg.role === 'user' ? 'bg-[#991B1B] text-white' : 'bg-white text-black'}`}>
                            {msg.role === 'user' ? (
                              msg.content
                            ) : (
                              <ReactMarkdown
                                components={{
                                  p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                  ul:     ({ children }) => <ul className="list-disc list-outside pl-4 mb-2 space-y-1">{children}</ul>,
                                  ol:     ({ children }) => <ol className="list-decimal list-outside pl-4 mb-2 space-y-1">{children}</ol>,
                                  li:     ({ children }) => <li className="leading-snug">{children}</li>,
                                  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                                  h3:     ({ children }) => <p className="font-bold mt-2 mb-1">{children}</p>,
                                  h4:     ({ children }) => <p className="font-bold mt-2 mb-1">{children}</p>,
                                }}
                              >
                                {msg.content}
                              </ReactMarkdown>
                            )}
                          </div>
                        </div>
                      ))}
                      {isChatLoading && (
                        <div className="flex justify-start flex-col items-start">
                          <span className="text-[9px] font-mono font-black uppercase mb-1 px-1.5 py-0.5 border border-black shadow-[1px_1px_0px_0px_#000000] bg-stone-200 text-black">
                            AI Assistant
                          </span>
                          <div className="p-3 border-2 border-black font-mono text-xs sm:text-sm shadow-[2px_2px_0px_0px_#000000] bg-white text-black animate-pulse flex items-center gap-2">
                            <Loader2 size={14} className="animate-spin text-[#991B1B]" />
                            Analyzing semantic context...
                          </div>
                        </div>
                      )}
                    </div>

                    <form onSubmit={sendChatMessage} className="border-t-4 border-black p-4 bg-white flex gap-2">
                      <input
                        type="text"
                        value={currentQuery}
                        onChange={(e) => setCurrentQuery(e.target.value)}
                        placeholder="Ask a question..."
                        className="flex-1 border-2 border-black p-3 font-mono text-sm outline-none focus:bg-stone-100"
                      />
                      <button
                        type="submit"
                        disabled={isChatLoading || !currentQuery.trim()}
                        className="px-6 bg-[#991B1B] text-white border-2 border-black font-black uppercase tracking-widest hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0px_0px_#000000] transition-all disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                      >
                        Send
                      </button>
                    </form>
                  </div>
                </div>

                {/* Right Column: Summaries & Insights Dashboard */}
                <div className="lg:col-span-7 space-y-6">
                  {concallStatusData.summary_data && (
                    <div className="brutalist-panel border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] bg-[#FDFBF7] flex flex-col overflow-hidden">
                      {/* Tabs Bar */}
                      <div className="flex border-b-4 border-brutalist-dark font-mono text-xs sm:text-sm uppercase tracking-wider font-black bg-[#1A1A1A]">
                        <button 
                          onClick={() => setActiveSummaryTab('SUMMARY')} 
                          className={`flex-1 px-4 py-3 text-center transition-all flex items-center justify-center gap-2 ${activeSummaryTab === 'SUMMARY' ? 'bg-[#991B1B] text-white font-black' : 'bg-white text-black hover:bg-stone-100'}`}
                        >
                          <Star size={16} className={activeSummaryTab === 'SUMMARY' ? 'text-yellow-300 fill-yellow-300' : 'text-stone-500'} />
                          <span>takeaways</span>
                        </button>
                        <button 
                          onClick={() => setActiveSummaryTab('SENTIMENT')} 
                          className={`flex-1 px-4 py-3 text-center border-l-4 border-r-4 border-brutalist-dark transition-all flex items-center justify-center gap-2 ${activeSummaryTab === 'SENTIMENT' ? 'bg-[#991B1B] text-white font-black' : 'bg-white text-black hover:bg-stone-100'}`}
                        >
                          <TrendingUp size={16} className={activeSummaryTab === 'SENTIMENT' ? 'text-white' : 'text-stone-500'} />
                          <span>sentiment</span>
                        </button>
                        <button 
                          onClick={() => setActiveSummaryTab('RISKS')} 
                          className={`flex-1 px-4 py-3 text-center transition-all flex items-center justify-center gap-2 ${activeSummaryTab === 'RISKS' ? 'bg-[#991B1B] text-white font-black' : 'bg-white text-black hover:bg-stone-100'}`}
                        >
                          <AlertTriangle size={16} className={activeSummaryTab === 'RISKS' ? 'text-white' : 'text-stone-500'} />
                          <span>risks & capex</span>
                        </button>
                      </div>

                      {/* Tab Contents */}
                      <div className="p-6 space-y-6 overflow-y-auto max-h-[500px]">
                        {activeSummaryTab === 'SUMMARY' && (
                          <div className="space-y-6">
                            {/* Executive Takeaways */}
                            {concallStatusData.summary_data.key_takeaways && concallStatusData.summary_data.key_takeaways.length > 0 && (
                              <div className="space-y-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-black text-xs sm:text-sm text-white bg-[#8338EC] inline-block px-3 py-1 uppercase tracking-widest border-2 border-brutalist-dark shadow-[2px_2px_0px_0px_#000000] flex items-center gap-2">
                                    <Star className="text-yellow-300 animate-pulse fill-yellow-300" size={16} strokeWidth={2.5} />
                                    Executive Takeaways
                                  </span>
                                </div>
                                <div className="grid grid-cols-1 gap-4">
                                  {concallStatusData.summary_data.key_takeaways.map((item, idx) => (
                                    <div key={idx} className="bg-white border-2 border-brutalist-dark p-4 rounded shadow-[3px_3px_0px_0px_#1A1A1A] relative flex flex-col pt-6">
                                      <span className="absolute -top-3 right-3 bg-[#8338EC] text-white font-black text-[10px] px-2 py-0.5 rounded-full border-2 border-brutalist-dark shadow-[1px_1px_0px_0px_#000000]">
                                        0{idx + 1}
                                      </span>
                                      <p className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">
                                        {formatSummaryText(item)}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Guidance */}
                            <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                              <h3 className="font-black text-sm text-brutalist-dark bg-[#F2EBE3] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Forward Guidance & Commitments</h3>
                              <ul className="space-y-3">
                                {(concallStatusData.summary_data.guidance || []).map((item, idx) => (
                                  <li key={idx} className="flex items-start gap-3">
                                    <TrendingUp className="text-brutalist-dark shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                    <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}

                        {activeSummaryTab === 'SENTIMENT' && (
                          <div className="grid grid-cols-1 gap-6">
                            {/* Positive News */}
                            <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                              <h3 className="font-black text-sm text-white bg-[#2E6F40] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Positive Signals</h3>
                              <ul className="space-y-3">
                                {(concallStatusData.summary_data.positive || []).map((item, idx) => (
                                  <li key={idx} className="flex items-start gap-3">
                                    <CheckCircle className="text-[#2E6F40] shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                    <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            {/* Negative News */}
                            <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                              <h3 className="font-black text-sm text-white bg-[#991B1B] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Negative Signals</h3>
                              <ul className="space-y-3">
                                {(concallStatusData.summary_data.negative || []).map((item, idx) => (
                                  <li key={idx} className="flex items-start gap-3">
                                    <AlertTriangle className="text-[#991B1B] shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                    <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}

                        {activeSummaryTab === 'RISKS' && (
                          <div className="space-y-6">
                            {/* Risks */}
                            <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                              <h3 className="font-black text-sm text-white bg-[#D95A2B] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Key Risks to Watch</h3>
                              <ul className="space-y-3">
                                {(concallStatusData.summary_data.key_risks_to_watch || []).map((item, idx) => (
                                  <li key={idx} className="flex items-start gap-3">
                                    <AlertTriangle className="text-[#D95A2B] shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                    <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            {/* Capital Allocation & CapEx */}
                            {concallStatusData.summary_data.capital_allocation && concallStatusData.summary_data.capital_allocation.length > 0 && (
                              <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                                <h3 className="font-black text-sm text-white bg-[#1A1A1A] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Capital Allocation & Balance Sheet</h3>
                                <ul className="space-y-3">
                                  {concallStatusData.summary_data.capital_allocation.map((item, idx) => (
                                    <li key={idx} className="flex items-start gap-3">
                                      <Activity className="text-[#1A1A1A] shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                      <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Strategic Initiatives */}
                            {concallStatusData.summary_data.strategic_initiatives && concallStatusData.summary_data.strategic_initiatives.length > 0 && (
                              <div className="border-2 border-brutalist-dark p-4 bg-white shadow-[3px_3px_0px_0px_#1A1A1A]">
                                <h3 className="font-black text-sm text-white bg-[#5C4033] inline-block px-3 py-1 mb-4 uppercase tracking-widest border-2 border-brutalist-dark">Strategic Initiatives & Macro Comments</h3>
                                <ul className="space-y-3">
                                  {concallStatusData.summary_data.strategic_initiatives.map((item, idx) => (
                                    <li key={idx} className="flex items-start gap-3">
                                      <CheckCircle className="text-[#5C4033] shrink-0 mt-0.5" size={18} strokeWidth={2.5} />
                                      <span className="text-sm font-medium font-mono text-brutalist-dark leading-relaxed">{formatSummaryText(item)}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="brutalist-panel p-4 sm:p-8 flex flex-col border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] bg-[#FDFBF7]">
                <h2 className="text-base sm:text-lg font-black uppercase tracking-tight text-brutalist-dark mb-4 flex items-center gap-2">
                  <FileText className="text-[#991B1B]" size={24} strokeWidth={3} />
                  Analyze Earnings Call Transcript
                </h2>

                <form onSubmit={uploadConcall} className="flex flex-col gap-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <input type="text" placeholder="Company Name (e.g. HDFC Bank)" value={concallCompanyName} onChange={e => setConcallCompanyName(e.target.value)} className="border-2 border-black p-3 font-mono text-sm outline-none focus:bg-stone-100" required />
                    <div className="flex flex-col gap-2">
                      <select
                        value={concallSector}
                        onChange={e => {
                          setConcallSector(e.target.value);
                          if (e.target.value !== "Other") {
                            setCustomSector("");
                          }
                        }}
                        className="border-2 border-black p-3 font-mono text-sm outline-none focus:bg-stone-100 w-full"
                        required
                      >
                        <option value="" disabled>Select sector</option>
                        <option value="Banking & Finance">Banking & Finance</option>
                        <option value="Information Technology">Information Technology</option>
                        <option value="Pharmaceuticals & Healthcare">Pharmaceuticals & Healthcare</option>
                        <option value="Automobile & Auto Ancillaries">Automobile & Auto Ancillaries</option>
                        <option value="Fast Moving Consumer Goods">Fast Moving Consumer Goods</option>
                        <option value="Defence & Aerospace">Defence & Aerospace</option>
                        <option value="Railways & Transport">Railways & Transport</option>
                        <option value="Power & Utilities">Power & Utilities</option>
                        <option value="Infrastructure & Construction">Infrastructure & Construction</option>
                        <option value="Chemicals & Specialty Chemicals">Chemicals & Specialty Chemicals</option>
                        <option value="Metals & Mining">Metals & Mining</option>
                        <option value="Renewable Energy">Renewable Energy</option>
                        <option value="Oil & Gas">Oil & Gas</option>
                        <option value="Electronic Manufacturing Services">Electronic Manufacturing Services</option>
                        <option value="Agriculture & Fertilizers">Agriculture & Fertilizers</option>
                        <option value="Other">Other (Type custom sector)</option>
                      </select>

                      {concallSector === "Other" && (
                        <input
                          type="text"
                          placeholder="Type custom sector (e.g. Defense)"
                          value={customSector}
                          onChange={e => setCustomSector(e.target.value)}
                          className="border-2 border-black p-3 font-mono text-sm outline-none bg-yellow-50 focus:bg-yellow-100 transition-colors animate-in slide-in-from-top-2 duration-300"
                          required
                        />
                      )}
                    </div>
                    <select value={concallQuarter} onChange={e => setConcallQuarter(e.target.value)} className="border-2 border-black p-3 font-mono text-sm outline-none focus:bg-stone-100" required>
                      <option value="Q1">Q1</option>
                      <option value="Q2">Q2</option>
                      <option value="Q3">Q3</option>
                      <option value="Q4">Q4</option>
                    </select>
                    <input type="text" placeholder="Financial Year (e.g. FY26)" value={concallFiscalYear} onChange={e => setConcallFiscalYear(e.target.value)} className="border-2 border-black p-3 font-mono text-sm outline-none focus:bg-stone-100" required />
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setConcallUploadType("file")}
                      className={`flex-1 py-2 text-xs font-bold font-mono uppercase border-2 border-black ${concallUploadType === "file" ? "bg-black text-white" : "bg-white text-black hover:bg-black/5"}`}
                    >
                      Upload File
                    </button>
                    <button
                      type="button"
                      onClick={() => setConcallUploadType("url")}
                      className={`flex-1 py-2 text-xs font-bold font-mono uppercase border-2 border-black ${concallUploadType === "url" ? "bg-black text-white" : "bg-white text-black hover:bg-black/5"}`}
                    >
                      Enter URL
                    </button>
                  </div>

                  {concallUploadType === "file" ? (
                    <label className="cursor-pointer border-2 border-dashed border-black p-4 text-center font-bold uppercase font-mono text-sm hover:bg-black/5 transition-colors">
                      {concallFile ? concallFile.name : "DROP EARNINGS CALL PDF HERE OR CLICK TO UPLOAD"}
                      <input
                        type="file"
                        className="hidden"
                        accept="application/pdf, text/plain"
                        onChange={(e) => setConcallFile(e.target.files[0])}
                      />
                    </label>
                  ) : (
                    <div className="border-2 border-dashed border-black p-4 bg-white flex items-center justify-center">
                      <input
                        type="url"
                        placeholder="https://example.com/concall.pdf"
                        value={concallUrl}
                        onChange={(e) => setConcallUrl(e.target.value)}
                        className="w-full p-2 border-2 border-black focus:outline-none focus:bg-stone-100 font-mono text-sm"
                      />
                    </div>
                  )}

                  {concallError && (
                    <div className="text-[#991B1B] font-bold text-xs uppercase flex items-center gap-2 mt-2">
                      <AlertTriangle size={16} /> {concallError}
                    </div>
                  )}

                  {concallStatusData && concallStatusData.status === 'PENDING' && (
                    <div className="mt-4 p-3 sm:p-4 border-2 border-brutalist-dark bg-stone-50 font-mono text-[10px] sm:text-xs">
                      <div className="flex justify-between mb-2">
                        <span className="font-bold text-[#991B1B] uppercase">{concallPhaseText}</span>
                        <span className="font-bold">{concallProgress}%</span>
                      </div>
                      <div className="w-full h-3 sm:h-4 border-2 border-brutalist-dark bg-white relative overflow-hidden">
                        <div className="absolute top-0 left-0 h-full bg-[#991B1B] transition-all duration-300" style={{ width: `${concallProgress}%` }}>
                          <div className="w-full h-full opacity-20 bg-[repeating-linear-gradient(45deg,transparent,transparent_5px,#000_5px,#000_10px)]"></div>
                        </div>
                      </div>
                    </div>
                  )}

                  {concallStatusData?.error_message && (
                    <div className="text-[#991B1B] font-bold text-xs flex flex-col gap-1 mt-4 p-3 border-2 border-[#991B1B] bg-[#991B1B]/10 break-words">
                      <span className="uppercase flex items-center gap-2"><AlertTriangle size={16} /> Error Details:</span>
                      <span className="font-mono">{concallStatusData.error_message}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isConcallUploading || (concallStatusData && !['FAILED', 'COMPLETED'].includes(concallStatusData.status))}
                    className="mt-4 w-full py-4 px-4 bg-[#991B1B] text-white border-2 border-black font-black uppercase tracking-widest hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0px_0px_#000000] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                  >
                    {isConcallUploading || (concallStatusData && !['FAILED', 'COMPLETED'].includes(concallStatusData.status)) ? 'Processing...' : '[ Ask Questions from this Concall ]'}
                  </button>
                </form>
              </div>
            )}
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="mt-auto py-8 px-4 border-t-4 border-brutalist-dark bg-[#F2EBE3]">
        <div className="max-w-7xl mx-auto flex flex-col items-center text-center gap-4">
          <div className="bg-brutalist-orange/10 border-2 border-brutalist-orange p-3 max-w-2xl">
            <p className="text-brutalist-orange font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2">
              <AlertTriangle size={16} /> Disclaimer
            </p>
            <p className="text-brutalist-dark text-xs font-medium mt-1">
              This AI project can make mistakes. Do not rely on it completely before taking any financial decisions.
            </p>
          </div>
          <p className="text-brutalist-dark font-black uppercase tracking-widest text-sm mt-4">
            Made with <span className="text-[#991B1B]">❤️</span> by{' '}
            <a href="https://www.linkedin.com/in/meetmmodi45" target="_blank" rel="noopener noreferrer" className="hover:text-brutalist-orange hover:underline decoration-2 underline-offset-4 transition-colors">
              Meet Modi
            </a>
          </p>
        </div>
      </footer>

      {isBackendWakingUp && (
        <div className="fixed inset-0 bg-[#F2EBE3]/90 backdrop-blur-sm z-[200] flex items-center justify-center p-4">
          <div className="brutalist-panel max-w-md w-full p-8 bg-white border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] text-center space-y-6 animate-in zoom-in-95 duration-300">
            <div className="p-4 bg-[#991B1B]/10 rounded-full text-[#991B1B] border-2 border-[#991B1B] w-16 h-16 flex items-center justify-center mx-auto animate-pulse">
              <Database size={32} />
            </div>
            
            <div className="space-y-2">
              <h3 className="text-2xl font-black uppercase tracking-tighter text-brutalist-dark">
                Waking up the server
              </h3>
              <p className="text-xs font-mono font-black text-[#991B1B] uppercase tracking-widest">
                Initializing Backend Services
              </p>
            </div>

            <p className="text-xs text-stone-600 font-mono leading-relaxed bg-[#F2EBE3] p-4 border-2 border-black">
              {coldStartCountdown <= 1 
                ? "Still waiting... The server is taking a bit longer than expected to boot up. We are continuously retrying connection."
                : "Our core backend servers sleep during periods of inactivity to save costs. It takes up to 90 seconds to boot up on your first visit. Thank you for your patience!"
              }
            </p>

            {/* Countdown Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between font-mono text-xs font-bold uppercase">
                <span>{coldStartCountdown <= 1 ? "Still retrying connection..." : "Booting servers..."}</span>
                <span>{coldStartCountdown}s remaining</span>
              </div>
              <div className="w-full h-4 border-2 border-black bg-stone-100 relative overflow-hidden">
                <div 
                  className="absolute top-0 left-0 h-full bg-[#991B1B] transition-all duration-1000" 
                  style={{ width: `${((90 - coldStartCountdown) / 90) * 100}%` }}
                >
                  <div className="w-full h-full opacity-20 bg-[repeating-linear-gradient(45deg,transparent,transparent_5px,#000_5px,#000_10px)]"></div>
                </div>
              </div>
            </div>

            <div className="text-[10px] text-stone-500 font-mono flex items-center justify-center gap-2 animate-pulse">
              <Loader2 size={12} className="animate-spin text-[#991B1B]" />
              Retrying connection to backend...
            </div>
          </div>
        </div>
      )}

      <GlobalAssistant />
    </div>
  );
}

export default App;
