import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { Search, Loader2, Activity, Shield, TrendingUp, DollarSign, LineChart as LineChartIcon, Users, Building, MessageSquare, Briefcase, Sparkles, ChevronDown, ChevronUp, BarChart2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api/v1`;

const MODULES = [
  { id: 'business', title: 'Business Analysis', icon: Briefcase, color: 'bg-blue-500' },
  { id: 'valuation', title: 'Valuation & Multiples', icon: Activity, color: 'bg-purple-500' },
  { id: 'financials', title: 'Financials & Fundamentals', icon: DollarSign, color: 'bg-green-600' },
  { id: 'technical', title: 'Technical & Flow Analysis', icon: LineChartIcon, color: 'bg-red-500' },
  { id: 'moat', title: 'Moat & Competition', icon: Shield, color: 'bg-indigo-500' },
  { id: 'news', title: 'Latest News', icon: TrendingUp, color: 'bg-yellow-500' },
];

// ─── Financial Table Component ─────────────────────────────────────────────────
function FinancialTable({ title, rows, color = 'bg-green-600' }) {
  if (!rows || rows.length === 0) return null;

  // Get all period labels (skip Period and FiscalYear keys)
  const periods = rows.map(r => r.Period);
  // Get all metric keys (rows = array of period objects, we need to pivot)
  const metricKeys = Object.keys(rows[0]).filter(k => k !== 'Period' && k !== 'FiscalYear');

  // Check if any row for a metric has actual data
  const hasData = (key) => rows.some(r => r[key] !== null && r[key] !== undefined);

  const formatVal = (val) => {
    if (val === null || val === undefined) return <span className="text-stone-300">—</span>;
    const num = parseFloat(val);
    if (isNaN(num)) return val;
    // Color negative values red
    const cls = num < 0 ? 'text-red-500 font-bold' : '';
    return <span className={cls}>{num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>;
  };

  return (
    <div className="mb-6">
      <div className={`flex items-center gap-2 px-3 py-2 border-b-2 border-brutalist-dark mb-0 ${color}`}>
        <BarChart2 size={14} className="text-white" strokeWidth={3} />
        <span className="text-xs font-black uppercase tracking-widest text-white">{title}</span>
        <span className="text-xs font-mono text-white/70 ml-1">(₹ Cr)</span>
      </div>
      <div className="overflow-x-auto border-2 border-t-0 border-brutalist-dark">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="bg-stone-100 border-b-2 border-brutalist-dark">
              <th className="text-left px-3 py-2 font-black uppercase text-brutalist-dark sticky left-0 bg-stone-100 border-r-2 border-brutalist-dark min-w-[160px]">
                Metric
              </th>
              {periods.map(p => (
                <th key={p} className="px-3 py-2 text-right font-black text-brutalist-dark whitespace-nowrap min-w-[90px]">
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metricKeys.filter(hasData).map((key, idx) => (
              <tr key={key} className={`border-b border-stone-200 hover:bg-brutalist-orange/5 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-stone-50'}`}>
                <td className="px-3 py-1.5 font-bold text-brutalist-dark sticky left-0 bg-inherit border-r-2 border-stone-200 whitespace-nowrap">
                  {key}
                </td>
                {rows.map(r => (
                  <td key={r.Period} className="px-3 py-1.5 text-right text-brutalist-dark">
                    {formatVal(r[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Financials Module (special — shows tables + lazy LLM summary) ────────────
function FinancialsModule({ symbol }) {
  const [tablesData, setTablesData] = useState(null);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState(null);
  const [activeTab, setActiveTab] = useState('income'); // income | balance | cashflow
  const [showQuarterly, setShowQuarterly] = useState(false);

  // LLM summary state
  const [summaryData, setSummaryData] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [summaryVisible, setSummaryVisible] = useState(false);

  const loadTables = async () => {
    setTablesLoading(true);
    setTablesError(null);
    try {
      const res = await axios.get(`${API_BASE}/equity-research/financials-data/${symbol}`);
      setTablesData(res.data);
    } catch (err) {
      setTablesError('Failed to load financial data.');
    } finally {
      setTablesLoading(false);
    }
  };

  const runSummary = () => {
    if (summaryLoading) return;
    setSummaryData('');
    setSummaryError(null);
    setSummaryLoading(true);
    setSummaryVisible(true);

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${symbol}/financials`);
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        setSummaryLoading(false);
      } else {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.error) {
            setSummaryError(parsed.error);
            setSummaryLoading(false);
            eventSource.close();
          } else if (parsed.clear) {
            setSummaryData('');
          } else if (parsed.content) {
            setSummaryData(prev => prev + parsed.content);
          }
        } catch (e) {}
      }
    };
    eventSource.onerror = () => {
      setSummaryError('Connection lost during analysis.');
      setSummaryLoading(false);
      eventSource.close();
    };
  };

  const TABS = [
    { id: 'income', label: 'Income' },
    { id: 'balance', label: 'Balance Sheet' },
    { id: 'cashflow', label: 'Cash Flow' },
  ];

  const renderTable = () => {
    if (!tablesData) return null;
    if (activeTab === 'income') {
      const rows = showQuarterly
        ? tablesData.income_statement?.quarterly
        : tablesData.income_statement?.annual;
      return <FinancialTable title={`Income Statement — ${showQuarterly ? 'Quarterly' : 'Annual'}`} rows={rows} color="bg-green-600" />;
    }
    if (activeTab === 'balance') {
      return <FinancialTable title="Balance Sheet — Annual" rows={tablesData.balance_sheet?.annual} color="bg-blue-600" />;
    }
    if (activeTab === 'cashflow') {
      return <FinancialTable title="Cash Flow Statement — Annual" rows={tablesData.cash_flow?.annual} color="bg-indigo-600" />;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Initial load state */}
      {!tablesData && !tablesLoading && !tablesError && (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4">
          <DollarSign size={48} className="text-brutalist-dark/10 mb-4" />
          <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
          <button
            onClick={loadTables}
            className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
          >
            Load Financial Statements
          </button>
        </div>
      )}

      {tablesLoading && (
        <div className="h-40 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
          <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Fetching Data...</span>
        </div>
      )}

      {tablesError && (
        <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark m-4">
          ⚠️ {tablesError}
        </div>
      )}

      {tablesData && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Sub-tabs: Income / Balance / Cash Flow */}
          <div className="flex border-b-2 border-brutalist-dark bg-white shrink-0">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2 text-xs font-black uppercase tracking-widest border-r-2 border-brutalist-dark last:border-r-0 transition-colors ${
                  activeTab === tab.id
                    ? 'bg-brutalist-dark text-white'
                    : 'bg-white text-brutalist-dark hover:bg-stone-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Toggle Annual / Quarterly for Income tab */}
          {activeTab === 'income' && (
            <div className="flex border-b border-stone-200 bg-stone-50 shrink-0">
              <button
                onClick={() => setShowQuarterly(false)}
                className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-widest transition-colors ${!showQuarterly ? 'bg-brutalist-orange text-white' : 'text-brutalist-dark hover:bg-stone-200'}`}
              >
                Annual
              </button>
              <button
                onClick={() => setShowQuarterly(true)}
                className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-widest transition-colors ${showQuarterly ? 'bg-brutalist-orange text-white' : 'text-brutalist-dark hover:bg-stone-200'}`}
              >
                Quarterly
              </button>
            </div>
          )}

          {/* Table area */}
          <div className="flex-1 overflow-y-auto p-3 bg-[#F9F9F9]">
            {renderTable()}
          </div>

          {/* LLM Summary Section */}
          {summaryVisible && (
            <div className="border-t-2 border-brutalist-dark shrink-0 max-h-72 overflow-y-auto bg-white">
              <div className="flex items-center gap-2 px-3 py-2 bg-green-600 border-b-2 border-brutalist-dark">
                <Sparkles size={14} className="text-white" />
                <span className="text-xs font-black uppercase tracking-widest text-white">AI Summary</span>
                {summaryLoading && <Loader2 size={12} className="animate-spin text-white ml-1" />}
                <button
                  onClick={() => setSummaryVisible(false)}
                  className="ml-auto text-white/70 hover:text-white text-xs font-bold"
                >
                  ✕
                </button>
              </div>
              {summaryError && (
                <div className="p-3 text-red-600 font-bold text-xs">⚠️ {summaryError}</div>
              )}
              {summaryData && (
                <div className="p-3 prose prose-sm max-w-none">
                  <ReactMarkdown
                    rehypePlugins={[rehypeRaw]}
                    components={{
                      h3: ({ node, ...props }) => <h3 className="text-sm font-bold uppercase tracking-wider text-brutalist-dark mt-4 mb-2" {...props} />,
                      p: ({ node, ...props }) => <p className="mb-2 text-brutalist-dark leading-relaxed font-medium text-xs" {...props} />,
                      ul: ({ node, ...props }) => <ul className="list-square pl-4 mb-3 space-y-1 marker:text-brutalist-orange font-medium" {...props} />,
                      li: ({ node, ...props }) => <li className="text-brutalist-dark text-xs" {...props} />,
                      strong: ({ node, ...props }) => <strong className="font-black bg-stone-200 px-0.5" {...props} />,
                    }}
                  >
                    {summaryData}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Bottom action bar */}
      {tablesData && (
        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0 flex gap-2">
          <button
            onClick={loadTables}
            disabled={tablesLoading}
            className="flex-1 text-xs font-bold font-mono uppercase tracking-widest py-2 hover:bg-stone-100 disabled:opacity-50 transition-colors border-2 border-brutalist-dark"
          >
            ↺ Refresh
          </button>
          <button
            onClick={runSummary}
            disabled={summaryLoading}
            className={`flex items-center justify-center gap-1.5 flex-1 text-xs font-bold font-mono uppercase tracking-widest py-2 border-2 border-brutalist-dark transition-all disabled:opacity-50 ${
              summaryVisible && summaryData
                ? 'bg-brutalist-dark text-white'
                : 'bg-brutalist-orange text-white hover:bg-brutalist-orange/90'
            }`}
          >
            <Sparkles size={12} />
            {summaryLoading ? 'Summarising...' : summaryVisible && summaryData ? 'Re-summarise' : '✦ Summarise'}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ────────────────────────────────────────────────────────────
export default function ResearchDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);

  // module state: Record<string, { loading: boolean, data: string, error: string }>
  const [moduleStates, setModuleStates] = useState({});

  // Debounced search
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchTerm.length >= 2) {
        setIsSearching(true);
        try {
          const res = await axios.get(`${API_BASE}/equity-research/search?q=${searchTerm}`);
          setSearchResults(res.data);
          setShowDropdown(true);
        } catch (err) {
          console.error("Search failed", err);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]);

  const handleSelectCompany = (company) => {
    setSelectedCompany(company);
    setSearchTerm('');
    setShowDropdown(false);
    setModuleStates({});
  };

  const analyzeModule = (moduleId) => {
    if (!selectedCompany) return;

    setModuleStates(prev => ({
      ...prev,
      [moduleId]: { loading: true, data: '', error: null }
    }));

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${selectedCompany.symbol}/${moduleId}`);

    eventSource.onmessage = (event) => {
      if (event.data === "[DONE]") {
        eventSource.close();
        setModuleStates(prev => ({
          ...prev,
          [moduleId]: { ...prev[moduleId], loading: false }
        }));
      } else {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.error) {
            setModuleStates(prev => ({
              ...prev,
              [moduleId]: { loading: false, data: '', error: parsed.error }
            }));
            eventSource.close();
          } else if (parsed.clear) {
            setModuleStates(prev => ({
              ...prev,
              [moduleId]: {
                ...prev[moduleId],
                data: ''
              }
            }));
          } else if (parsed.content) {
            setModuleStates(prev => ({
              ...prev,
              [moduleId]: {
                ...prev[moduleId],
                data: prev[moduleId].data + parsed.content
              }
            }));
          }
        } catch (e) {
          console.error("Error parsing SSE data", e, event.data);
        }
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
      setModuleStates(prev => ({
        ...prev,
        [moduleId]: { ...prev[moduleId], loading: false, error: 'Connection lost or failed to load data.' }
      }));
    };
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

      {/* Search Header */}
      <div className="brutalist-panel p-8 text-center bg-[#F2EBE3]">
        <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter mb-4 leading-none">
          Perform Institutional level of Equity Research
        </h2>
        <p className="text-brutalist-dark font-mono text-sm max-w-2xl mx-auto mb-8 font-bold">
          Search for any NSE-listed company to perform deep-dive analysis across 6 specialized modules powered by real-time financial data.
        </p>

        <div className="max-w-xl mx-auto relative">
          <div className="relative flex items-center">
            <Search className="absolute left-4 text-brutalist-dark" size={24} strokeWidth={3} />
            <input
              type="text"
              placeholder="Search by Symbol or Company Name (e.g. RELIANCE)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-4 text-lg font-bold border-4 border-brutalist-dark bg-white focus:outline-none focus:ring-4 focus:ring-brutalist-orange transition-all shadow-[4px_4px_0px_0px_#1A1A1A] placeholder-brutalist-dark/50"
            />
            {isSearching && (
              <Loader2 className="absolute right-4 animate-spin text-brutalist-orange" size={24} />
            )}
          </div>

          {/* Dropdown */}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute top-full mt-2 left-0 w-full bg-white border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] z-50 max-h-80 overflow-y-auto">
              {searchResults.map((company) => (
                <div
                  key={company.symbol}
                  onClick={() => handleSelectCompany(company)}
                  className="p-4 border-b-2 border-brutalist-dark hover:bg-brutalist-orange hover:text-white cursor-pointer transition-colors text-left flex justify-between items-center group"
                >
                  <div>
                    <div className="font-black text-lg">{company.symbol}</div>
                    <div className="font-mono text-xs font-bold opacity-80">{company.name}</div>
                  </div>
                  <div className="text-xs font-bold border-2 border-current px-2 py-1 uppercase tracking-widest">
                    {company.industry || 'NSE'}
                  </div>
                </div>
              ))}
            </div>
          )}
          {showDropdown && searchResults.length === 0 && !isSearching && (
            <div className="absolute top-full mt-2 left-0 w-full bg-white border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] z-50 p-4 font-bold text-brutalist-orange text-left">
              No companies found.
            </div>
          )}
        </div>
      </div>

      {/* Selected Company Dashboard */}
      {selectedCompany && (
        <div className="space-y-8">
          <div className="brutalist-panel p-6 flex justify-between items-center bg-brutalist-dark text-white shadow-[8px_8px_0px_0px_#D95A2B]">
            <div>
              <h2 className="text-3xl font-black uppercase tracking-tight text-brutalist-orange">{selectedCompany.name}</h2>
              <div className="font-mono text-sm tracking-widest text-[#F2EBE3] flex items-center gap-4 mt-2">
                <span className="bg-white/20 px-2 py-1 text-brutalist-orange font-bold">NSE: {selectedCompany.symbol}</span>
                {selectedCompany.industry && <span>{selectedCompany.industry}</span>}
                {selectedCompany.isin && <span className="text-brutalist-orange font-bold">ISIN: {selectedCompany.isin}</span>}
              </div>
            </div>
            <Activity className="text-brutalist-orange" size={48} strokeWidth={2} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {MODULES.map((mod) => {
              const state = moduleStates[mod.id] || { loading: false, data: null, error: null };
              const Icon = mod.icon;
              const isFinancials = mod.id === 'financials';

              return (
                <div key={mod.id} className="brutalist-card flex flex-col bg-white overflow-hidden max-h-[620px]">
                  {/* Header */}
                  <div className="p-4 border-b-4 border-brutalist-dark flex justify-between items-center bg-stone-100 shrink-0">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 border-2 border-brutalist-dark flex items-center justify-center shadow-[2px_2px_0px_0px_#1A1A1A] ${mod.color}`}>
                        <Icon size={20} className="text-white" strokeWidth={3} />
                      </div>
                      <h3 className="font-black uppercase tracking-tight text-brutalist-dark">{mod.title}</h3>
                    </div>
                  </div>

                  {/* Content Area */}
                  {isFinancials ? (
                    // ── Special Financials module ──────────────────────────────
                    <FinancialsModule symbol={selectedCompany.symbol} />
                  ) : (
                    // ── Regular LLM-powered modules ────────────────────────────
                    <>
                      <div className="flex-1 p-4 overflow-y-auto bg-[#F9F9F9] relative group prose prose-sm max-w-none">
                        {!state.data && !state.loading && !state.error && (
                          <div className="h-40 flex flex-col items-center justify-center text-center p-4">
                            <Icon size={48} className="text-brutalist-dark/10 mb-4" />
                            <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
                            <button
                              onClick={() => analyzeModule(mod.id)}
                              className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
                            >
                              Run {mod.title}
                            </button>
                          </div>
                        )}

                        {state.loading && !state.data && (
                          <div className="h-40 flex flex-col items-center justify-center">
                            <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
                            <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Compiling Research...</span>
                          </div>
                        )}

                        {state.error && (
                          <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark">
                            ⚠️ Error: {state.error}
                          </div>
                        )}

                        {state.data && (
                          <div className="font-sans">
                            <ReactMarkdown
                              rehypePlugins={[rehypeRaw]}
                              components={{
                                h1: ({ node, ...props }) => <h1 className="text-xl font-black uppercase border-b-2 border-brutalist-dark pb-2 mb-4" {...props} />,
                                h2: ({ node, ...props }) => <h2 className="text-lg font-black uppercase text-brutalist-dark mt-6 mb-3" {...props} />,
                                h3: ({ node, ...props }) => <h3 className="text-base font-bold uppercase tracking-wider text-brutalist-dark mt-4 mb-2" {...props} />,
                                p: ({ node, ...props }) => <p className="mb-4 text-brutalist-dark leading-relaxed font-medium" {...props} />,
                                ul: ({ node, ...props }) => <ul className="list-square pl-5 mb-4 space-y-1 marker:text-brutalist-orange font-medium" {...props} />,
                                li: ({ node, ...props }) => <li className="text-brutalist-dark" {...props} />,
                                strong: ({ node, ...props }) => <strong className="font-black bg-stone-200 px-1" {...props} />,
                                blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-brutalist-orange pl-4 italic font-medium my-4 bg-stone-100 py-2" {...props} />,
                                a: ({ node, ...props }) => <a className="text-blue-600 underline hover:text-blue-800" target="_blank" rel="noopener noreferrer" {...props} />,
                              }}
                            >
                              {state.data}
                            </ReactMarkdown>
                            {state.loading && <Loader2 className="animate-spin text-brutalist-orange inline-block ml-2" size={16} />}
                          </div>
                        )}
                      </div>

                      {/* Action Bar (when data exists) */}
                      {state.data && (
                        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0">
                          <button
                            onClick={() => analyzeModule(mod.id)}
                            disabled={state.loading}
                            className="w-full text-xs font-bold font-mono uppercase tracking-widest py-2 hover:bg-stone-100 disabled:opacity-50 transition-colors"
                          >
                            {state.loading ? 'Generating...' : 'Regenerate Analysis'}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
