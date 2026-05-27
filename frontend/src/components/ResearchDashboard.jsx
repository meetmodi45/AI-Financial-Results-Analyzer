import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { Search, Loader2, Activity, Shield, TrendingUp, DollarSign, LineChart as LineChartIcon, Users, Building, MessageSquare, Briefcase, Sparkles, ChevronDown, ChevronUp, BarChart2, Maximize2 } from 'lucide-react';

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

  const [isModalOpen, setIsModalOpen] = React.useState(false);

  // Reverse rows array so columns render newest date first
  const reversedRows = React.useMemo(() => [...rows].reverse(), [rows]);

  // Get all period labels (skip Period and FiscalYear keys)
  const periods = reversedRows.map(r => r.Period);
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
        <button
          onClick={() => setIsModalOpen(true)}
          className="ml-auto text-white hover:text-stone-200 transition-colors p-0.5 border border-transparent hover:border-white shrink-0 flex items-center justify-center"
          title="Expand Table"
        >
          <Maximize2 size={12} strokeWidth={3} />
        </button>
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
                {reversedRows.map(r => (
                  <td key={r.Period} className="px-3 py-1.5 text-right text-brutalist-dark">
                    {formatVal(r[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Expanded fullscreen modal overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-brutalist-dark/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className={`flex items-center justify-between px-4 py-3 border-b-4 border-brutalist-dark shrink-0 ${color}`}>
              <div className="flex items-center gap-2">
                <BarChart2 size={18} className="text-white" strokeWidth={3} />
                <span className="text-sm font-black uppercase tracking-widest text-white">{title}</span>
                <span className="text-xs font-mono text-white/70 ml-1">(₹ Cr)</span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-white hover:text-stone-200 border-2 border-white px-3 py-1 font-black font-mono text-xs uppercase bg-brutalist-dark hover:bg-brutalist-orange hover:border-brutalist-dark transition-all"
              >
                Close ✕
              </button>
            </div>
            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-2 md:p-6 bg-[#F9F9F9]">
              <div className="border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] overflow-x-auto bg-white">
                <table className="w-full text-[10px] md:text-xs font-mono">
                  <thead>
                    <tr className="bg-stone-100 border-b-4 border-brutalist-dark">
                      <th className="text-left px-2 py-2 md:px-4 md:py-3 font-black uppercase text-brutalist-dark sticky left-0 bg-stone-100 border-r-4 border-brutalist-dark min-w-[120px] md:min-w-[200px]">
                        Metric
                      </th>
                      {periods.map(p => (
                        <th key={p} className="px-2 py-2 md:px-4 md:py-3 text-right font-black text-brutalist-dark whitespace-nowrap min-w-[80px] md:min-w-[120px] border-r-2 border-stone-200 last:border-r-0">
                          {p}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {metricKeys.filter(hasData).map((key, idx) => (
                      <tr key={key} className={`border-b-2 border-stone-200 hover:bg-brutalist-orange/5 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-stone-50'}`}>
                        <td className="px-2 py-2 md:px-4 md:py-2.5 font-bold text-brutalist-dark sticky left-0 bg-inherit border-r-4 border-brutalist-dark whitespace-nowrap">
                          {key}
                        </td>
                        {reversedRows.map(r => (
                          <td key={r.Period} className="px-2 py-2 md:px-4 md:py-2.5 text-right text-brutalist-dark border-r-2 border-stone-100 last:border-r-0">
                            {formatVal(r[key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
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
    <div className="flex flex-col flex-1 min-h-0">
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

// ─── Technical Module (special — shows metrics + lazy LLM summary) ─────────────
function TechnicalModule({ symbol }) {
  const [techData, setTechData] = useState(null);
  const [techLoading, setTechLoading] = useState(false);
  const [techError, setTechError] = useState(null);

  // LLM summary state
  const [summaryData, setSummaryData] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [summaryVisible, setSummaryVisible] = useState(false);

  const loadTech = async () => {
    setTechLoading(true);
    setTechError(null);
    try {
      const res = await axios.get(`${API_BASE}/equity-research/technical-data/${symbol}`);
      setTechData(res.data);
    } catch (err) {
      setTechError('Failed to load technical data.');
    } finally {
      setTechLoading(false);
    }
  };

  const runSummary = () => {
    if (summaryLoading) return;
    setSummaryData('');
    setSummaryError(null);
    setSummaryLoading(true);
    setSummaryVisible(true);

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${symbol}/technical`);
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

  const formatPrice = (val) => {
    if (val === null || val === undefined) return '—';
    return typeof val === 'number' ? val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : val;
  };

  // Calculations for display
  let dist50 = null;
  let dist200 = null;
  let volSurge = null;
  if (techData) {
    const price = techData.currentPrice;
    if (price) {
      if (techData.fiftyDayAverage) {
        dist50 = (((price - techData.fiftyDayAverage) / techData.fiftyDayAverage) * 100).toFixed(2);
      }
      if (techData.twoHundredDayAverage) {
        dist200 = (((price - techData.twoHundredDayAverage) / techData.twoHundredDayAverage) * 100).toFixed(2);
      }
    }
    if (techData.regularMarketVolume && techData.averageVolume) {
      volSurge = (techData.regularMarketVolume / techData.averageVolume).toFixed(2);
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Initial load state */}
      {!techData && !techLoading && !techError && (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4">
          <LineChartIcon size={48} className="text-brutalist-dark/10 mb-4" />
          <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
          <button
            onClick={loadTech}
            className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
          >
            Load Technical Metrics
          </button>
        </div>
      )}

      {techLoading && (
        <div className="h-40 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
          <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Fetching Data...</span>
        </div>
      )}

      {techError && (
        <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark m-4">
          ⚠️ {techError}
        </div>
      )}

      {techData && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Technical Info Area */}
          <div className="flex-1 overflow-y-auto p-4 bg-[#F9F9F9] space-y-4">
            
            {/* Metric Row: Price */}
            <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A] flex justify-between items-center">
              <div>
                <span className="font-mono text-[10px] font-black uppercase text-stone-400 block">Current Price</span>
                <span className="text-2xl font-black text-brutalist-dark">₹{formatPrice(techData.currentPrice)}</span>
              </div>
              {techData.percentChange && (
                <div className={`text-xs font-mono font-black border-2 border-brutalist-dark px-2 py-1 shadow-[1px_1px_0px_0px_#1A1A1A] ${parseFloat(techData.percentChange) >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {parseFloat(techData.percentChange) >= 0 ? '+' : ''}{techData.percentChange}%
                </div>
              )}
            </div>

            {/* Metric Grid */}
            <div className="grid grid-cols-2 gap-3">
              {/* 50 DMA */}
              <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                <span className="font-mono text-[10px] font-black uppercase text-stone-400 block">50-Day Avg (DMA)</span>
                <span className="text-lg font-black text-brutalist-dark">₹{formatPrice(techData.fiftyDayAverage)}</span>
                {dist50 !== null && (
                  <span className={`block font-mono text-[10px] font-bold mt-1 ${parseFloat(dist50) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {parseFloat(dist50) >= 0 ? '▲' : '▼'} {Math.abs(parseFloat(dist50))}% vs price
                  </span>
                )}
              </div>

              {/* 200 DMA */}
              <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                <span className="font-mono text-[10px] font-black uppercase text-stone-400 block">200-Day Avg (DMA)</span>
                <span className="text-lg font-black text-brutalist-dark">₹{formatPrice(techData.twoHundredDayAverage)}</span>
                {dist200 !== null && (
                  <span className={`block font-mono text-[10px] font-bold mt-1 ${parseFloat(dist200) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {parseFloat(dist200) >= 0 ? '▲' : '▼'} {Math.abs(parseFloat(dist200))}% vs price
                  </span>
                )}
              </div>
            </div>

            {/* 52 Week extremes */}
            <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
              <span className="font-mono text-[10px] font-black uppercase text-stone-400 block mb-2">52-Week Range</span>
              <div className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-red-600">Low: ₹{formatPrice(techData.fiftyTwoWeekLow)}</span>
                <div className="flex-1 mx-3 h-2 bg-stone-200 border border-brutalist-dark relative">
                  {techData.currentPrice && techData.fiftyTwoWeekLow && techData.fiftyTwoWeekHigh && (() => {
                    const low = parseFloat(techData.fiftyTwoWeekLow);
                    const high = parseFloat(techData.fiftyTwoWeekHigh);
                    const current = techData.currentPrice;
                    if (high > low && current >= low && current <= high) {
                      const percentage = ((current - low) / (high - low)) * 100;
                      return <div className="absolute top-0 bottom-0 w-2 bg-brutalist-orange border-x border-brutalist-dark" style={{ left: `${percentage}%`, transform: 'translateX(-50%)' }}></div>;
                    }
                  })()}
                </div>
                <span className="text-green-600">High: ₹{formatPrice(techData.fiftyTwoWeekHigh)}</span>
              </div>
            </div>

            {/* Volume Surge / Flow */}
            <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A] flex justify-between items-center">
              <div>
                <span className="font-mono text-[10px] font-black uppercase text-stone-400 block">Trading Volume (10D vs 3M)</span>
                <div className="text-xs font-bold mt-1">
                  10D Avg: <span className="font-mono">{techData.regularMarketVolume || '—'}M</span>
                  <span className="mx-2 text-stone-300">|</span>
                  3M Avg: <span className="font-mono">{techData.averageVolume || '—'}M</span>
                </div>
              </div>
              {volSurge !== null && (
                <div className={`text-right ${parseFloat(volSurge) >= 1 ? 'text-green-600' : 'text-stone-500'}`}>
                  <span className="font-mono text-[10px] font-black uppercase text-stone-400 block">Surge Ratio</span>
                  <span className="text-lg font-black">{volSurge}x</span>
                </div>
              )}
            </div>

          </div>

          {/* LLM Summary Section */}
          {summaryVisible && (
            <div className="border-t-2 border-brutalist-dark shrink-0 max-h-60 overflow-y-auto bg-white">
              <div className="flex items-center gap-2 px-3 py-2 bg-red-600 border-b-2 border-brutalist-dark">
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
      {techData && (
        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0 flex gap-2">
          <button
            onClick={loadTech}
            disabled={techLoading}
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

// ─── Business Module (shows company profile + management + shareholding; lazy LLM deep-dive) ─
function BusinessModule({ symbol }) {
  const [bizData, setBizData] = useState(null);
  const [bizLoading, setBizLoading] = useState(false);
  const [bizError, setBizError] = useState(null);

  // LLM summary state
  const [summaryData, setSummaryData] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [summaryVisible, setSummaryVisible] = useState(false);

  const loadBiz = async () => {
    setBizLoading(true);
    setBizError(null);
    try {
      const res = await axios.get(`${API_BASE}/equity-research/business-data/${symbol}`);
      setBizData(res.data);
    } catch (err) {
      setBizError('Failed to load business profile.');
    } finally {
      setBizLoading(false);
    }
  };

  const runSummary = () => {
    if (summaryLoading) return;
    setSummaryData('');
    setSummaryError(null);
    setSummaryLoading(true);
    setSummaryVisible(true);

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${symbol}/business`);
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

  // Compact shareholding bar colours
  const shColours = ['bg-blue-500', 'bg-indigo-400', 'bg-green-500', 'bg-yellow-400', 'bg-orange-400', 'bg-red-400'];

  return (
    <div className="flex flex-col flex-1 min-h-0">

      {/* Initial state */}
      {!bizData && !bizLoading && !bizError && (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4">
          <Briefcase size={48} className="text-brutalist-dark/10 mb-4" />
          <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
          <button
            onClick={loadBiz}
            className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
          >
            Load Business Profile
          </button>
        </div>
      )}

      {bizLoading && (
        <div className="h-40 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
          <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Fetching Profile...</span>
        </div>
      )}

      {bizError && (
        <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark m-4">
          ⚠️ {bizError}
        </div>
      )}

      {bizData && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Scrollable info area */}
          <div className="flex-1 overflow-y-auto p-4 bg-[#F9F9F9] space-y-4">

            {/* Company Identity */}
            <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
              <span className="font-mono text-[10px] font-black uppercase text-stone-400 block mb-1">Company Identity</span>
              <div className="text-base font-black text-brutalist-dark leading-tight">{bizData.companyName || symbol}</div>
              <div className="flex flex-wrap gap-2 mt-2">
                {bizData.industry && (
                  <span className="text-[9px] font-black uppercase tracking-widest bg-blue-100 text-blue-700 border border-blue-200 px-1.5 py-0.5">
                    {bizData.industry}
                  </span>
                )}
                {bizData.mgIndustry && bizData.mgIndustry !== bizData.industry && (
                  <span className="text-[9px] font-black uppercase tracking-widest bg-indigo-100 text-indigo-700 border border-indigo-200 px-1.5 py-0.5">
                    {bizData.mgIndustry}
                  </span>
                )}
              </div>
            </div>

            {/* Business Description — split into bullet points per sentence */}
            {bizData.description && (() => {
              const sentences = bizData.description
                .replace(/([.!?])\s+/g, '$1\n')
                .split('\n')
                .map(s => s.trim())
                .filter(s => s.length > 10);
              return (
                <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                  <span className="font-mono text-[10px] font-black uppercase text-stone-400 block mb-2">What They Do</span>
                  <ul className="space-y-1.5">
                    {sentences.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-brutalist-dark font-medium leading-snug">
                        <span className="text-brutalist-orange font-black mt-0.5 shrink-0">▸</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 pt-2 border-t border-stone-200">
                    <span className="text-[9px] font-mono font-black text-blue-600 bg-blue-50 border border-blue-200 px-2 py-1 inline-block">
                      💡 Click ✦ Summarise for full deep dive: GTM, TAM, moat, management &amp; risks.
                    </span>
                  </div>
                </div>
              );
            })()}

            {/* Management Team */}
            {bizData.officers && bizData.officers.length > 0 && (
              <div>
                <span className="font-mono text-[10px] font-black uppercase text-stone-400 block mb-2">Key Management</span>
                <div className="space-y-1.5">
                  {bizData.officers.map((o, i) => (
                    <div key={i} className="flex items-start gap-2 p-2 bg-white border-2 border-brutalist-dark shadow-[1px_1px_0px_0px_#1A1A1A]">
                      <div className="w-7 h-7 border-2 border-brutalist-dark bg-stone-800 flex items-center justify-center shrink-0">
                        <span className="text-[10px] font-black text-white">{(o.name || '?')[0]}</span>
                      </div>
                      <div className="min-w-0">
                        <div className="font-black text-xs text-brutalist-dark truncate">{o.name}</div>
                        <div className="font-mono text-[9px] text-stone-500 leading-tight">{o.title}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Shareholding Pattern */}
            {bizData.shareholding && bizData.shareholding.length > 0 && (() => {
              const validSh = bizData.shareholding.filter(s => s.percentage !== null && s.percentage !== undefined);
              const asOf = validSh[0]?.asOf || '';
              return (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] font-black uppercase text-stone-400">Shareholding Pattern</span>
                    {asOf && <span className="font-mono text-[9px] text-stone-400">As of {asOf}</span>}
                  </div>
                  {/* Stacked bar */}
                  <div className="flex h-4 w-full border-2 border-brutalist-dark overflow-hidden mb-2">
                    {validSh.map((s, i) => (
                      <div
                        key={i}
                        className={`${shColours[i % shColours.length]} h-full`}
                        style={{ width: `${parseFloat(s.percentage) || 0}%` }}
                        title={`${s.name}: ${s.percentage}%`}
                      />
                    ))}
                  </div>
                  {/* Legend */}
                  <div className="grid grid-cols-2 gap-1">
                    {validSh.map((s, i) => (
                      <div key={i} className="flex items-center gap-1.5">
                        <div className={`w-2.5 h-2.5 border border-brutalist-dark shrink-0 ${shColours[i % shColours.length]}`} />
                        <span className="font-mono text-[9px] text-stone-600 truncate">{s.name}</span>
                        <span className="font-mono text-[9px] font-black text-brutalist-dark ml-auto">{s.percentage}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

          </div>

          {/* LLM Summary Section */}
          {summaryVisible && (
            <div className="border-t-2 border-brutalist-dark shrink-0 max-h-72 overflow-y-auto bg-white">
              <div className="flex items-center gap-2 px-3 py-2 bg-blue-600 border-b-2 border-brutalist-dark">
                <Sparkles size={14} className="text-white" />
                <span className="text-xs font-black uppercase tracking-widest text-white">AI Business Deep Dive</span>
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
      {bizData && (
        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0 flex gap-2">
          <button
            onClick={loadBiz}
            disabled={bizLoading}
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
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            <Sparkles size={12} />
            {summaryLoading ? 'Analysing...' : summaryVisible && summaryData ? 'Re-analyse' : '✦ Summarise'}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Moat Module (special — shows core metrics, peers + lazy LLM summary) ──────
function MoatModule({ symbol }) {
  const [moatData, setMoatData] = useState(null);
  const [moatLoading, setMoatLoading] = useState(false);
  const [moatError, setMoatError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // LLM summary state
  const [summaryData, setSummaryData] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [summaryVisible, setSummaryVisible] = useState(false);

  const loadMoat = async () => {
    setMoatLoading(true);
    setMoatError(null);
    try {
      const res = await axios.get(`${API_BASE}/equity-research/moat-data/${symbol}`);
      setMoatData(res.data);
    } catch (err) {
      setMoatError('Failed to load moat data.');
    } finally {
      setMoatLoading(false);
    }
  };

  const runSummary = () => {
    if (summaryLoading) return;
    setSummaryData('');
    setSummaryError(null);
    setSummaryLoading(true);
    setSummaryVisible(true);

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${symbol}/moat`);
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

  const formatPct = (val) => {
    if (val === null || val === undefined) return '—';
    const parsedVal = parseFloat(val);
    if (isNaN(parsedVal)) return val;
    // If it's a decimal, e.g. 0.245 -> 24.50%, but check if it's already a percentage > 1
    const finalVal = Math.abs(parsedVal) < 1.0 ? parsedVal * 100 : parsedVal;
    return `${finalVal.toFixed(2)}%`;
  };

  const formatVal = (val) => {
    if (val === null || val === undefined) return '—';
    return typeof val === 'number' ? val.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : val;
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Initial load state */}
      {!moatData && !moatLoading && !moatError && (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4">
          <Shield size={48} className="text-brutalist-dark/10 mb-4" />
          <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
          <button
            onClick={loadMoat}
            className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
          >
            Load Moat & Peers
          </button>
        </div>
      )}

      {moatLoading && (
        <div className="h-40 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
          <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Fetching Data...</span>
        </div>
      )}

      {moatError && (
        <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark m-4">
          ⚠️ {moatError}
        </div>
      )}

      {moatData && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Info area */}
          <div className="flex-1 overflow-y-auto p-4 bg-[#F9F9F9] space-y-4">
            
            {/* Margins, Returns & Growth grid */}
            <div>
              <span className="font-mono text-[10px] font-black uppercase text-stone-400 block mb-2">Margins, Returns & Growth</span>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                  <span className="font-mono text-[10px] font-black text-stone-400 block">ROCE (Return on Capital)</span>
                  <span className="text-base font-black text-brutalist-dark">{formatPct(moatData.metrics?.returnOnAssets)}</span>
                </div>
                <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                  <span className="font-mono text-[10px] font-black text-stone-400 block">Operating Margin (OPM)</span>
                  <span className="text-base font-black text-brutalist-dark">{formatPct(moatData.metrics?.operatingMargin)}</span>
                </div>
                <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                  <span className="font-mono text-[10px] font-black text-stone-400 block">Revenue Growth (YoY TTM)</span>
                  <span className={`text-base font-black ${parseFloat(moatData.metrics?.revenueGrowth) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPct(moatData.metrics?.revenueGrowth)}
                  </span>
                </div>
                <div className="p-3 border-2 border-brutalist-dark bg-white shadow-[2px_2px_0px_0px_#1A1A1A]">
                  <span className="font-mono text-[10px] font-black text-stone-400 block">Earnings Growth (YoY TTM)</span>
                  <span className={`text-base font-black ${parseFloat(moatData.metrics?.earningsGrowth) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPct(moatData.metrics?.earningsGrowth)}
                  </span>
                </div>
              </div>
            </div>

            {/* Peer Comparison Table */}
            {moatData.peers && moatData.peers.length > 0 && (
              <div className="space-y-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[10px] font-black uppercase text-stone-400">Peer Comparison</span>
                  <button
                    onClick={() => setIsModalOpen(true)}
                    className="text-stone-400 hover:text-brutalist-dark transition-colors p-0.5 border border-transparent hover:border-brutalist-dark shrink-0 flex items-center justify-center"
                    title="Expand Table"
                  >
                    <Maximize2 size={12} strokeWidth={3} />
                  </button>
                </div>
                <div className="overflow-x-auto border-2 border-brutalist-dark">
                  <table className="w-full text-[10px] font-mono bg-white">
                    <thead>
                      <tr className="bg-stone-100 border-b-2 border-brutalist-dark">
                        <th className="text-left px-2 py-1.5 font-black uppercase border-r border-stone-300">Peer</th>
                        <th className="text-right px-2 py-1.5 font-black uppercase border-r border-stone-300">P/E</th>
                        <th className="text-right px-2 py-1.5 font-black uppercase border-r border-stone-300">P/B</th>
                        <th className="text-right px-2 py-1.5 font-black uppercase border-r border-stone-300">ROE</th>
                        <th className="text-right px-2 py-1.5 font-black uppercase border-r border-stone-300">NPM</th>
                        <th className="text-right px-2 py-1.5 font-black uppercase">M.Cap (Cr)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b-2 border-brutalist-dark bg-brutalist-orange/10 font-bold hover:bg-brutalist-orange/20">
                        <td className="px-2 py-1.5 font-black border-r border-stone-300 truncate max-w-[100px] text-brutalist-orange" title={`${symbol} (Target)`}>
                          {symbol} *
                        </td>
                        <td className="px-2 py-1.5 text-right border-r border-stone-300 font-black">
                          {formatVal(moatData.metrics?.trailingPE)}
                        </td>
                        <td className="px-2 py-1.5 text-right border-r border-stone-300">
                          {formatVal(moatData.metrics?.priceToBook)}
                        </td>
                        <td className="px-2 py-1.5 text-right border-r border-stone-300 font-black">
                          {formatPct(moatData.metrics?.returnOnEquity)}
                        </td>
                        <td className="px-2 py-1.5 text-right border-r border-stone-300">
                          {formatPct(moatData.metrics?.profitMargin)}
                        </td>
                        <td className="px-2 py-1.5 text-right font-black">
                          ₹{formatVal(moatData.metrics?.marketCap)}
                        </td>
                      </tr>
                      {moatData.peers.map((peer, idx) => (
                        <tr key={idx} className="border-b border-stone-200 last:border-b-0 hover:bg-stone-50">
                          <td className="px-2 py-1.5 font-bold border-r border-stone-200 truncate max-w-[100px]" title={peer.companyName}>
                            {peer.companyName}
                          </td>
                          <td className="px-2 py-1.5 text-right border-r border-stone-200 font-bold">
                            {formatVal(peer.priceToEarningsValueRatio)}
                          </td>
                          <td className="px-2 py-1.5 text-right border-r border-stone-200">
                            {formatVal(peer.priceToBookValueRatio)}
                          </td>
                          <td className="px-2 py-1.5 text-right border-r border-stone-200 font-bold">
                            {formatPct(peer.returnOnAverageEquityTrailing12Month ?? peer.returnOnAverageEquity5YearAverage)}
                          </td>
                          <td className="px-2 py-1.5 text-right border-r border-stone-350">
                            {formatPct(peer.netProfitMarginPercentTrailing12Month ?? peer.netProfitMargin5YearAverage)}
                          </td>
                          <td className="px-2 py-1.5 text-right font-bold">
                            ₹{formatVal(peer.marketCap)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="p-2.5 bg-blue-50/50 border border-blue-200 rounded font-mono text-[9px] text-stone-600 leading-normal space-y-1">
                  <div>* Target company ({symbol}) highlighted at the top.</div>
                  <div className="flex items-center gap-1 font-semibold text-blue-700">
                    <span>💡 Looking for competitor qualitative dynamics, economic moats, and major threats? Click <b>✦ Summarise</b> below to stream a deep institutional report.</span>
                  </div>
                </div>
              </div>
            )}

            {/* Expanded fullscreen modal overlay for Peer Comparison */}
            {isModalOpen && (
              <div className="fixed inset-0 bg-brutalist-dark/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
                <div className="bg-white border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                  {/* Modal Header */}
                  <div className="flex items-center justify-between px-4 py-3 border-b-4 border-brutalist-dark shrink-0 bg-indigo-600">
                    <div className="flex items-center gap-2">
                      <Shield size={18} className="text-white" strokeWidth={3} />
                      <span className="text-sm font-black uppercase tracking-widest text-white">Peer Comparison Matrix</span>
                    </div>
                    <button
                      onClick={() => setIsModalOpen(false)}
                      className="text-white hover:text-stone-200 border-2 border-white px-3 py-1 font-black font-mono text-xs uppercase bg-brutalist-dark hover:bg-brutalist-orange hover:border-brutalist-dark transition-all"
                    >
                      Close ✕
                    </button>
                  </div>
                  {/* Modal Content */}
                  <div className="flex-1 overflow-auto p-2 md:p-6 bg-[#F9F9F9]">
                    <div className="border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] overflow-x-auto bg-white">
                      <table className="w-full text-[10px] md:text-xs font-mono">
                        <thead>
                          <tr className="bg-stone-100 border-b-4 border-brutalist-dark">
                            <th className="text-left px-2 py-2 md:px-4 md:py-3 font-black uppercase border-r-4 border-brutalist-dark sticky left-0 bg-stone-100 min-w-[120px] md:min-w-[200px]">Peer Company</th>
                            <th className="text-right px-2 py-2 md:px-4 md:py-3 font-black uppercase border-r-2 border-stone-200">P/E Ratio</th>
                            <th className="text-right px-2 py-2 md:px-4 md:py-3 font-black uppercase border-r-2 border-stone-200">P/B Ratio</th>
                            <th className="text-right px-2 py-2 md:px-4 md:py-3 font-black uppercase border-r-2 border-stone-200">Return on Equity (ROE)</th>
                            <th className="text-right px-2 py-2 md:px-4 md:py-3 font-black uppercase border-r-2 border-stone-200">Net Profit Margin (NPM)</th>
                            <th className="text-right px-2 py-2 md:px-4 md:py-3 font-black uppercase">Market Capitalization (Cr)</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b-4 border-brutalist-dark bg-brutalist-orange/10 font-bold hover:bg-brutalist-orange/20">
                            <td className="px-2 py-2 md:px-4 md:py-3 font-black border-r-4 border-brutalist-dark text-brutalist-orange sticky left-0 bg-[#FFF5F0]" title={`${symbol} (Target)`}>
                              {symbol} *
                            </td>
                            <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200 font-black">
                              {formatVal(moatData.metrics?.trailingPE)}
                            </td>
                            <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200">
                              {formatVal(moatData.metrics?.priceToBook)}
                            </td>
                            <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200 font-black">
                              {formatPct(moatData.metrics?.returnOnEquity)}
                            </td>
                            <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200">
                              {formatPct(moatData.metrics?.profitMargin)}
                            </td>
                            <td className="px-2 py-2 md:px-4 md:py-3 text-right font-black">
                              ₹{formatVal(moatData.metrics?.marketCap)}
                            </td>
                          </tr>
                          {moatData.peers.map((peer, idx) => (
                            <tr key={idx} className="border-b border-stone-200 last:border-b-0 hover:bg-stone-50">
                              <td className="px-2 py-2 md:px-4 md:py-3 font-bold border-r-4 border-brutalist-dark truncate max-w-[200px]" title={peer.companyName}>
                                {peer.companyName}
                              </td>
                              <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200 font-bold">
                                {formatVal(peer.priceToEarningsValueRatio)}
                              </td>
                              <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200">
                                {formatVal(peer.priceToBookValueRatio)}
                              </td>
                              <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200 font-bold">
                                {formatPct(peer.returnOnAverageEquityTrailing12Month ?? peer.returnOnAverageEquity5YearAverage)}
                              </td>
                              <td className="px-2 py-2 md:px-4 md:py-3 text-right border-r-2 border-stone-200">
                                {formatPct(peer.netProfitMarginPercentTrailing12Month ?? peer.netProfitMargin5YearAverage)}
                              </td>
                              <td className="px-2 py-2 md:px-4 md:py-3 text-right font-bold">
                                ₹{formatVal(peer.marketCap)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* LLM Summary Section */}
          {summaryVisible && (
            <div className="border-t-2 border-brutalist-dark shrink-0 max-h-60 overflow-y-auto bg-white">
              <div className="flex items-center gap-2 px-3 py-2 bg-indigo-600 border-b-2 border-brutalist-dark">
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
      {moatData && (
        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0 flex gap-2">
          <button
            onClick={loadMoat}
            disabled={moatLoading}
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


// ─── News Module (special — shows raw articles list + lazy LLM summary) ────────
function NewsModule({ symbol }) {
  const [newsData, setNewsData] = useState(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsError, setNewsError] = useState(null);

  // Individual article summary states
  const [articleSummaries, setArticleSummaries] = useState({});
  const [summarizingIdx, setSummarizingIdx] = useState(null);
  const [articleErrors, setArticleErrors] = useState({});

  // LLM summary state
  const [summaryData, setSummaryData] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [summaryVisible, setSummaryVisible] = useState(false);

  const loadNews = async () => {
    setNewsLoading(true);
    setNewsError(null);
    setArticleSummaries({});
    setArticleErrors({});
    try {
      const res = await axios.get(`${API_BASE}/equity-research/news-data/${symbol}`);
      setNewsData(res.data);
    } catch (err) {
      setNewsError('Failed to load recent news.');
    } finally {
      setNewsLoading(false);
    }
  };

  const runSummary = () => {
    if (summaryLoading) return;
    setSummaryData('');
    setSummaryError(null);
    setSummaryLoading(true);
    setSummaryVisible(true);

    const eventSource = new EventSource(`${API_BASE}/equity-research/analyze/${symbol}/news`);
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

  const summarizeIndividualArticle = async (item, idx) => {
    if (summarizingIdx !== null) return;
    setSummarizingIdx(idx);
    setArticleErrors(prev => ({ ...prev, [idx]: null }));
    try {
      const res = await axios.post(`${API_BASE}/equity-research/summarize-article`, {
        title: item.title,
        symbol: symbol
      });
      setArticleSummaries(prev => ({ ...prev, [idx]: res.data.summary }));
    } catch (err) {
      setArticleErrors(prev => ({ ...prev, [idx]: 'Failed to generate summary.' }));
    } finally {
      setSummarizingIdx(null);
    }
  };

  const formatNewsDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Initial load state */}
      {!newsData && !newsLoading && !newsError && (
        <div className="h-40 flex flex-col items-center justify-center text-center p-4">
          <TrendingUp size={48} className="text-brutalist-dark/10 mb-4" />
          <p className="font-mono text-xs font-bold text-brutalist-dark/50 uppercase tracking-widest mb-4">Ready for Analysis</p>
          <button
            onClick={loadNews}
            className="brutalist-button px-6 py-2 text-sm bg-brutalist-orange text-brutalist-dark w-full"
          >
            Load Recent News
          </button>
        </div>
      )}

      {newsLoading && (
        <div className="h-40 flex flex-col items-center justify-center">
          <Loader2 className="animate-spin text-brutalist-orange mb-4" size={40} />
          <span className="font-mono text-xs font-bold uppercase tracking-widest animate-pulse">Fetching News...</span>
        </div>
      )}

      {newsError && (
        <div className="p-4 bg-brutalist-orange/20 border-2 border-brutalist-orange font-bold text-sm text-brutalist-dark m-4">
          ⚠️ {newsError}
        </div>
      )}

      {newsData && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Articles list */}
          <div className="flex-1 overflow-y-auto p-4 bg-[#F9F9F9] space-y-3">
            {newsData.length === 0 ? (
              <p className="font-mono text-xs font-bold text-stone-400 text-center py-8">No recent news articles found.</p>
            ) : (
              newsData.map((item, idx) => (
                <div key={idx} className="p-3 border-2 border-brutalist-dark bg-white hover:bg-stone-50/50 transition-colors shadow-[2px_2px_0px_0px_#1A1A1A] flex flex-col">
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-brutalist-dark hover:text-brutalist-orange transition-colors text-xs leading-snug block mb-2"
                  >
                    {item.title}
                  </a>
                  <div className="flex items-center justify-between font-mono text-[9px] font-black text-stone-400 uppercase">
                    <div className="flex items-center gap-2">
                      <span className="bg-stone-100 border border-stone-300 px-1.5 py-0.5">{item.source || 'News'}</span>
                      <span>•</span>
                      <span>{formatNewsDate(item.date)}</span>
                    </div>
                  </div>

                  {/* Individual article summary renderer */}
                  {summarizingIdx === idx && (
                    <div className="mt-2 text-[10px] font-mono font-bold text-brutalist-orange animate-pulse flex items-center gap-1.5 bg-stone-50 p-2 border border-dashed border-stone-300">
                      <Loader2 className="animate-spin" size={10} />
                      <span>Generating 2-3 line summary...</span>
                    </div>
                  )}

                  {articleErrors[idx] && (
                    <div className="mt-2 text-[10px] text-red-600 font-bold bg-red-50 p-1.5 border border-red-200">
                      ⚠️ {articleErrors[idx]}
                    </div>
                  )}

                  {articleSummaries[idx] && (
                    <div className="mt-2 text-[11px] leading-relaxed text-stone-600 italic bg-stone-50 p-2 border-l-2 border-brutalist-orange font-medium animate-in fade-in slide-in-from-top-1 duration-200">
                      {articleSummaries[idx]}
                    </div>
                  )}

                  {!articleSummaries[idx] && summarizingIdx !== idx && (
                    <div className="mt-2 flex justify-end">
                      <button
                        onClick={() => summarizeIndividualArticle(item, idx)}
                        disabled={summarizingIdx !== null}
                        className="flex items-center gap-1 font-mono text-[8px] font-black uppercase text-brutalist-orange border border-brutalist-orange px-2 py-0.5 hover:bg-brutalist-orange hover:text-white transition-all disabled:opacity-50"
                      >
                        <Sparkles size={8} />
                        Summarise Article
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* LLM Summary Section */}
          {summaryVisible && (
            <div className="border-t-2 border-brutalist-dark shrink-0 max-h-60 overflow-y-auto bg-white">
              <div className="flex items-center gap-2 px-3 py-2 bg-yellow-500 border-b-2 border-brutalist-dark">
                <Sparkles size={14} className="text-brutalist-dark" />
                <span className="text-xs font-black uppercase tracking-widest text-brutalist-dark">AI Summary</span>
                {summaryLoading && <Loader2 size={12} className="animate-spin text-brutalist-dark ml-1" />}
                <button
                  onClick={() => setSummaryVisible(false)}
                  className="ml-auto text-brutalist-dark/70 hover:text-brutalist-dark text-xs font-bold"
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
      {newsData && (
        <div className="p-2 border-t-4 border-brutalist-dark bg-white shrink-0 flex gap-2">
          <button
            onClick={loadNews}
            disabled={newsLoading}
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
              const isSpecialModule = ['financials', 'technical', 'moat', 'news', 'business'].includes(mod.id);

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
                  ) : mod.id === 'technical' ? (
                    // ── Special Technical module ───────────────────────────────
                    <TechnicalModule symbol={selectedCompany.symbol} />
                  ) : mod.id === 'moat' ? (
                    // ── Special Moat module ────────────────────────────────────
                    <MoatModule symbol={selectedCompany.symbol} />
                  ) : mod.id === 'news' ? (
                    // ── Special News module ────────────────────────────────────
                    <NewsModule symbol={selectedCompany.symbol} />
                  ) : mod.id === 'business' ? (
                    // ── Special Business module ────────────────────────────────
                    <BusinessModule symbol={selectedCompany.symbol} />
                  ) : (
                    // ── Regular LLM-powered modules (Valuation, etc.) ──────────
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
