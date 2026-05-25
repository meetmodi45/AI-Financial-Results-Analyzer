import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import {
  Search, Loader2, Activity, Shield, TrendingUp, DollarSign,
  LineChart as LineChartIcon, Briefcase, ChevronRight, Play,
  RefreshCw, AlertTriangle, CheckCircle, Zap, X
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000/api/v1`;

const MODULES = [
  {
    id: 'business',
    title: 'Business Analysis',
    shortTitle: 'Business',
    icon: Briefcase,
    accent: '#2563EB',
    teaser: 'Revenue model, management quality, TAM, growth strategy & competitive positioning.',
  },
  {
    id: 'valuation',
    title: 'Valuation & Multiples',
    shortTitle: 'Valuation',
    icon: Activity,
    accent: '#7C3AED',
    teaser: 'Trailing/Forward P/E, P/B, EV/EBITDA, FCF Yield, PEG Ratio & intrinsic value estimate.',
  },
  {
    id: 'financials',
    title: 'Financials & Fundamentals',
    shortTitle: 'Financials',
    icon: DollarSign,
    accent: '#059669',
    teaser: 'Revenue growth, margins, ROE, ROCE, debt ratios & balance sheet health check.',
  },
  {
    id: 'technical',
    title: 'Technical & Flow Analysis',
    shortTitle: 'Technical',
    icon: LineChartIcon,
    accent: '#DC2626',
    teaser: 'RSI, MACD, 52-week range, moving averages & institutional FII/DII flow signals.',
  },
  {
    id: 'moat',
    title: 'Moat & Competition',
    shortTitle: 'Moat',
    icon: Shield,
    accent: '#D97706',
    teaser: 'Porter\'s Five Forces, switching costs, brand strength & competitive advantage durability.',
  },
  {
    id: 'news',
    title: 'Latest News',
    shortTitle: 'News',
    icon: TrendingUp,
    accent: '#0891B2',
    teaser: 'Recent headlines, regulatory updates, management commentary & market sentiment signals.',
  },
];

export default function ResearchDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeModule, setActiveModule] = useState('business');
  const [moduleStates, setModuleStates] = useState({});
  const [isRunningAll, setIsRunningAll] = useState(false);
  const readingPaneRef = useRef(null);

  // Debounced search
  useEffect(() => {
    const fn = setTimeout(async () => {
      if (searchTerm.length >= 2) {
        setIsSearching(true);
        try {
          const res = await axios.get(`${API_BASE}/equity-research/search?q=${searchTerm}`);
          setSearchResults(res.data);
          setShowDropdown(true);
        } catch (err) {
          console.error('Search failed', err);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 300);
    return () => clearTimeout(fn);
  }, [searchTerm]);

  const handleSelectCompany = (company) => {
    setSelectedCompany(company);
    setSearchTerm('');
    setShowDropdown(false);
    setModuleStates({});
    setActiveModule('business');
  };

  const analyzeModule = (moduleId) => {
    if (!selectedCompany) return;

    setModuleStates(prev => ({
      ...prev,
      [moduleId]: { loading: true, data: '', error: null },
    }));

    const eventSource = new EventSource(
      `${API_BASE}/equity-research/analyze/${selectedCompany.symbol}/${moduleId}`
    );

    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        setModuleStates(prev => ({
          ...prev,
          [moduleId]: { ...prev[moduleId], loading: false },
        }));
      } else {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.error) {
            setModuleStates(prev => ({
              ...prev,
              [moduleId]: { loading: false, data: '', error: parsed.error },
            }));
            eventSource.close();
          } else if (parsed.content) {
            setModuleStates(prev => ({
              ...prev,
              [moduleId]: {
                ...prev[moduleId],
                data: prev[moduleId].data + parsed.content,
              },
            }));
          }
        } catch (e) {
          console.error('SSE parse error', e, event.data);
        }
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setModuleStates(prev => ({
        ...prev,
        [moduleId]: {
          ...prev[moduleId],
          loading: false,
          error: 'Connection lost. Please try again.',
        },
      }));
    };
  };

  const runAllModules = () => {
    if (!selectedCompany || isRunningAll) return;
    setIsRunningAll(true);
    MODULES.forEach(mod => analyzeModule(mod.id));
    setTimeout(() => setIsRunningAll(false), 2000);
  };

  const completedCount = MODULES.filter(m => moduleStates[m.id]?.data && !moduleStates[m.id]?.loading).length;
  const loadingCount = MODULES.filter(m => moduleStates[m.id]?.loading).length;

  const activeMod = MODULES.find(m => m.id === activeModule);
  const activeState = moduleStates[activeModule] || { loading: false, data: null, error: null };
  const ActiveIcon = activeMod?.icon;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

      {/* ─── Search Header ─── */}
      <div className="brutalist-panel p-8 text-center bg-[#F2EBE3]">
        <h2 className="text-4xl md:text-5xl font-black uppercase tracking-tighter mb-4 leading-none">
          Perform Institutional level of Equity Research
        </h2>
        <p className="text-brutalist-dark font-mono text-sm max-w-2xl mx-auto mb-8 font-bold">
          Search any NSE-listed company. Our 6 AI agents cover Business, Valuation, Financials, Technicals, Moat & News.
        </p>

        <div className="max-w-xl mx-auto relative">
          <div className="relative flex items-center">
            <Search className="absolute left-4 text-brutalist-dark" size={24} strokeWidth={3} />
            <input
              type="text"
              placeholder="Search by Symbol or Company Name (e.g. TCS)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-4 text-lg font-bold border-4 border-brutalist-dark bg-white focus:outline-none focus:ring-4 focus:ring-brutalist-orange transition-all shadow-[4px_4px_0px_0px_#1A1A1A] placeholder-brutalist-dark/50"
            />
            {isSearching && <Loader2 className="absolute right-4 animate-spin text-brutalist-orange" size={24} />}
          </div>

          {showDropdown && searchResults.length > 0 && (
            <div className="absolute top-full mt-2 left-0 w-full bg-white border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] z-50 max-h-72 overflow-y-auto">
              {searchResults.map((company) => (
                <div
                  key={company.symbol}
                  onClick={() => handleSelectCompany(company)}
                  className="p-4 border-b-2 border-brutalist-dark hover:bg-brutalist-orange hover:text-white cursor-pointer transition-colors text-left flex justify-between items-center"
                >
                  <div>
                    <div className="font-black text-lg">{company.symbol}</div>
                    <div className="font-mono text-xs font-bold opacity-75">{company.name}</div>
                  </div>
                  <span className="text-xs font-bold border-2 border-current px-2 py-1 uppercase tracking-widest shrink-0">NSE</span>
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

      {/* ─── Research Terminal ─── */}
      {selectedCompany && (
        <div className="space-y-6">

          {/* Company Banner */}
          <div className="brutalist-panel p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-brutalist-dark text-white shadow-[8px_8px_0px_0px_#D95A2B]">
            <div>
              <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-tight text-brutalist-orange">{selectedCompany.name}</h2>
              <div className="font-mono text-xs tracking-widest text-[#F2EBE3] flex flex-wrap items-center gap-3 mt-2">
                <span className="bg-white/20 px-2 py-1 text-brutalist-orange font-bold">NSE: {selectedCompany.symbol}</span>
                {selectedCompany.isin && <span className="text-brutalist-orange font-bold">ISIN: {selectedCompany.isin}</span>}
              </div>
            </div>

            {/* Master "Generate All" Button */}
            <button
              onClick={runAllModules}
              disabled={isRunningAll || loadingCount > 0}
              className="flex items-center gap-3 px-6 py-3 bg-brutalist-orange text-white border-2 border-white font-black uppercase tracking-widest text-sm shadow-[4px_4px_0px_0px_white] hover:-translate-x-1 hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_white] transition-all disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 whitespace-nowrap"
            >
              {loadingCount > 0 ? (
                <><Loader2 size={18} className="animate-spin" /> Generating {loadingCount} Agents...</>
              ) : (
                <><Zap size={18} /> Generate Full Report</>
              )}
            </button>
          </div>

          {/* Progress Bar (when running) */}
          {(loadingCount > 0 || completedCount > 0) && (
            <div className="brutalist-panel px-6 py-4 bg-white flex items-center gap-4">
              <span className="font-mono text-xs font-bold uppercase tracking-widest shrink-0 text-brutalist-dark">
                {completedCount}/{MODULES.length} Complete
              </span>
              <div className="flex-1 h-3 border-2 border-brutalist-dark bg-stone-100 relative overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-brutalist-green transition-all duration-500"
                  style={{ width: `${(completedCount / MODULES.length) * 100}%` }}
                >
                  <div className="w-full h-full opacity-30 bg-[repeating-linear-gradient(45deg,transparent,transparent_4px,#000_4px,#000_8px)]" />
                </div>
              </div>
              <span className="font-mono text-xs font-bold text-brutalist-dark shrink-0">
                {Math.round((completedCount / MODULES.length) * 100)}%
              </span>
            </div>
          )}

          {/* ─── Two-Column Reading Pane ─── */}
          <div className="flex gap-0 border-4 border-brutalist-dark shadow-[8px_8px_0px_0px_#1A1A1A] bg-white min-h-[70vh]">

            {/* Left Sidebar — Agent List */}
            <div className="w-52 xl:w-64 shrink-0 border-r-4 border-brutalist-dark flex flex-col bg-[#F8F5F1]">
              <div className="p-4 border-b-4 border-brutalist-dark bg-brutalist-dark">
                <p className="font-black uppercase tracking-widest text-xs text-brutalist-orange">6 AI Agents</p>
              </div>
              {MODULES.map((mod) => {
                const state = moduleStates[mod.id] || {};
                const Icon = mod.icon;
                const isActive = activeModule === mod.id;
                const isDone = !!(state.data && !state.loading);
                const isLoading = !!state.loading;
                const hasError = !!state.error;

                return (
                  <button
                    key={mod.id}
                    onClick={() => {
                      setActiveModule(mod.id);
                      if (!state.data && !state.loading) analyzeModule(mod.id);
                    }}
                    className={`w-full text-left p-4 border-b-2 border-brutalist-dark/30 flex items-center gap-3 transition-all group relative
                      ${isActive ? 'bg-white border-l-4 border-l-brutalist-orange font-black' : 'hover:bg-stone-100 border-l-4 border-l-transparent'}`}
                  >
                    {/* Status dot */}
                    <div
                      className="w-8 h-8 shrink-0 flex items-center justify-center border-2 border-current transition-colors"
                      style={{ color: isActive ? mod.accent : '#1A1A1A', backgroundColor: isActive ? `${mod.accent}18` : 'transparent' }}
                    >
                      {isLoading ? (
                        <Loader2 size={16} className="animate-spin" style={{ color: mod.accent }} />
                      ) : isDone ? (
                        <CheckCircle size={16} className="text-brutalist-green" />
                      ) : hasError ? (
                        <AlertTriangle size={16} className="text-brutalist-orange" />
                      ) : (
                        <Icon size={16} />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className={`text-xs font-black uppercase tracking-tight truncate ${isActive ? 'text-brutalist-dark' : 'text-brutalist-dark/70'}`}>
                        {mod.shortTitle}
                      </div>
                      {isLoading && (
                        <div className="text-[10px] font-mono text-brutalist-orange uppercase tracking-widest animate-pulse">Generating...</div>
                      )}
                      {isDone && !isLoading && (
                        <div className="text-[10px] font-mono text-brutalist-green uppercase tracking-widest">Done</div>
                      )}
                      {!state.data && !isLoading && !hasError && (
                        <div className="text-[10px] font-mono text-brutalist-dark/40 uppercase tracking-widest">Click to run</div>
                      )}
                    </div>

                    {isActive && <ChevronRight size={14} className="shrink-0 text-brutalist-orange" />}
                  </button>
                );
              })}

              {/* Run All Button (sidebar) */}
              <div className="mt-auto p-4 border-t-4 border-brutalist-dark">
                <button
                  onClick={runAllModules}
                  disabled={isRunningAll || loadingCount > 0}
                  className="w-full py-2 text-xs font-black uppercase tracking-widest bg-brutalist-dark text-white hover:bg-brutalist-orange transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <Zap size={14} />
                  Run All
                </button>
              </div>
            </div>

            {/* Right Reading Pane */}
            <div className="flex-1 flex flex-col overflow-hidden" ref={readingPaneRef}>
              {/* Pane Header */}
              <div
                className="p-5 border-b-4 border-brutalist-dark flex items-center justify-between shrink-0"
                style={{ backgroundColor: `${activeMod?.accent}12` }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 border-2 border-brutalist-dark flex items-center justify-center shadow-[2px_2px_0px_0px_#1A1A1A]"
                    style={{ backgroundColor: activeMod?.accent }}
                  >
                    {ActiveIcon && <ActiveIcon size={20} className="text-white" strokeWidth={2.5} />}
                  </div>
                  <div>
                    <h3 className="font-black uppercase tracking-tight text-brutalist-dark">{activeMod?.title}</h3>
                    <p className="text-xs font-mono text-brutalist-dark/50 font-bold">
                      {selectedCompany.symbol} · AI-Generated Research
                    </p>
                  </div>
                </div>

                {/* Pane Actions */}
                <div className="flex items-center gap-2">
                  {activeState.data && (
                    <button
                      onClick={() => analyzeModule(activeModule)}
                      disabled={activeState.loading}
                      className="flex items-center gap-2 px-4 py-2 text-xs font-black uppercase tracking-widest border-2 border-brutalist-dark hover:bg-stone-100 transition-colors disabled:opacity-50"
                    >
                      <RefreshCw size={14} className={activeState.loading ? 'animate-spin' : ''} />
                      Regenerate
                    </button>
                  )}
                  {!activeState.data && !activeState.loading && (
                    <button
                      onClick={() => analyzeModule(activeModule)}
                      className="flex items-center gap-2 px-5 py-2 text-xs font-black uppercase tracking-widest bg-brutalist-dark text-white hover:bg-brutalist-orange transition-colors border-2 border-brutalist-dark shadow-[3px_3px_0px_0px_#D95A2B]"
                    >
                      <Play size={14} fill="currentColor" />
                      Run Agent
                    </button>
                  )}
                </div>
              </div>

              {/* Pane Content */}
              <div className="flex-1 overflow-y-auto p-6 md:p-8">

                {/* Empty / Teaser State */}
                {!activeState.data && !activeState.loading && !activeState.error && (
                  <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto py-16">
                    <div
                      className="w-20 h-20 border-4 border-brutalist-dark flex items-center justify-center mb-6 shadow-[4px_4px_0px_0px_#1A1A1A]"
                      style={{ backgroundColor: `${activeMod?.accent}15` }}
                    >
                      {ActiveIcon && <ActiveIcon size={36} strokeWidth={1.5} style={{ color: activeMod?.accent }} />}
                    </div>
                    <h4 className="font-black uppercase text-lg tracking-tight text-brutalist-dark mb-3">{activeMod?.title}</h4>
                    <p className="font-mono text-sm text-brutalist-dark/60 font-bold leading-relaxed mb-8">
                      {activeMod?.teaser}
                    </p>
                    {/* Skeleton preview lines */}
                    <div className="w-full space-y-3 text-left mb-8">
                      {[80, 65, 90, 50, 75].map((w, i) => (
                        <div key={i} className="h-3 bg-stone-200 rounded-none" style={{ width: `${w}%` }} />
                      ))}
                    </div>
                    <button
                      onClick={() => analyzeModule(activeModule)}
                      className="flex items-center gap-3 px-8 py-4 bg-brutalist-dark text-white font-black uppercase tracking-widest text-sm border-2 border-brutalist-dark shadow-[5px_5px_0px_0px_#D95A2B] hover:-translate-x-1 hover:-translate-y-1 hover:shadow-[7px_7px_0px_0px_#D95A2B] transition-all"
                      style={{ '--tw-shadow-color': activeMod?.accent }}
                    >
                      <Play size={16} fill="currentColor" />
                      Run {activeMod?.shortTitle} Agent
                    </button>
                  </div>
                )}

                {/* Loading (streaming) State */}
                {activeState.loading && !activeState.data && (
                  <div className="h-full flex flex-col items-center justify-center py-16">
                    <div className="relative w-16 h-16 mb-6">
                      <div
                        className="absolute inset-0 border-4 border-brutalist-dark animate-ping opacity-20"
                        style={{ borderColor: activeMod?.accent }}
                      />
                      <div
                        className="w-full h-full border-4 border-brutalist-dark flex items-center justify-center"
                        style={{ backgroundColor: `${activeMod?.accent}15`, borderColor: activeMod?.accent }}
                      >
                        <Loader2 size={28} className="animate-spin" style={{ color: activeMod?.accent }} />
                      </div>
                    </div>
                    <p className="font-black uppercase tracking-widest text-brutalist-dark text-sm animate-pulse">Compiling Research...</p>
                    <p className="font-mono text-xs text-brutalist-dark/40 mt-2 font-bold">AI is generating your {activeMod?.title} report</p>
                  </div>
                )}

                {/* Error State */}
                {activeState.error && (
                  <div className="p-6 bg-brutalist-orange/10 border-4 border-brutalist-orange flex gap-4">
                    <AlertTriangle size={24} className="text-brutalist-orange shrink-0 mt-1" strokeWidth={3} />
                    <div>
                      <p className="font-black uppercase text-brutalist-orange text-sm mb-1">Agent Error</p>
                      <p className="font-mono text-sm text-brutalist-dark font-bold">{activeState.error}</p>
                      <button
                        onClick={() => analyzeModule(activeModule)}
                        className="mt-4 px-4 py-2 text-xs font-black uppercase tracking-widest bg-brutalist-orange text-white border-2 border-brutalist-dark hover:opacity-90 transition-opacity"
                      >
                        Retry
                      </button>
                    </div>
                  </div>
                )}

                {/* Markdown Content */}
                {activeState.data && (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        h1: ({ node, ...props }) => <h1 className="text-2xl font-black uppercase border-b-4 border-brutalist-dark pb-3 mb-6 tracking-tight" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-lg font-black uppercase text-brutalist-dark mt-8 mb-4 pb-2 border-b-2 border-brutalist-dark/20 tracking-tight" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-base font-black uppercase tracking-wider text-brutalist-dark mt-6 mb-3" {...props} />,
                        p: ({ node, ...props }) => <p className="mb-4 text-brutalist-dark leading-relaxed font-medium text-[15px]" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-none pl-0 mb-4 space-y-2" {...props} />,
                        li: ({ node, ...props }) => (
                          <li className="flex items-start gap-3 text-brutalist-dark font-medium text-[15px]">
                            <span className="mt-1.5 w-2 h-2 rounded-none shrink-0 bg-brutalist-orange" />
                            <span {...props} />
                          </li>
                        ),
                        strong: ({ node, ...props }) => <strong className="font-black bg-yellow-100 px-1" {...props} />,
                        blockquote: ({ node, ...props }) => (
                          <blockquote
                            className="border-l-4 pl-5 italic font-medium my-5 py-3 bg-stone-50"
                            style={{ borderColor: activeMod?.accent }}
                            {...props}
                          />
                        ),
                        table: ({ node, ...props }) => <div className="overflow-x-auto my-4"><table className="w-full border-4 border-brutalist-dark text-sm" {...props} /></div>,
                        th: ({ node, ...props }) => <th className="p-3 border-2 border-brutalist-dark bg-brutalist-dark text-white font-black uppercase tracking-wider text-left text-xs" {...props} />,
                        td: ({ node, ...props }) => <td className="p-3 border-2 border-brutalist-dark/30 font-medium" {...props} />,
                      }}
                    >
                      {activeState.data}
                    </ReactMarkdown>
                    {activeState.loading && (
                      <span className="inline-flex items-center gap-1 font-mono text-xs text-brutalist-orange animate-pulse">
                        <Loader2 size={12} className="animate-spin" /> Streaming...
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
