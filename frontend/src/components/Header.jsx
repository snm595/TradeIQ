import { Search, Activity, Clock } from 'lucide-react';

export default function Header({ ticker, setTicker, timeframe, setTimeframe, onAnalyze, loading }) {
  const timeframes = ['15m', '1h', '4h', '1d'];

  return (
    <header className="panel px-4 py-4 flex flex-col xl:flex-row gap-4 justify-between xl:items-center">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-xl bg-sky-500/12 flex items-center justify-center border border-sky-300/35 shadow-[0_0_24px_rgba(80,168,255,0.25)]">
          <Activity className="text-sky-200 w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">TradeIQ Intelligence Fabric</h1>
          <p className="text-xs text-slate-400 font-medium uppercase tracking-[0.18em]">Institutional AI Trading Console</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row items-start lg:items-center gap-3 w-full xl:w-auto">
        <div className="relative w-full lg:w-48">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-500" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2.5 border border-slate-700 rounded-lg bg-slate-900/50 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-400/70 transition-all uppercase"
            placeholder="Ticker (e.g. SPY)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && onAnalyze()}
          />
        </div>

        <div className="flex items-center bg-slate-900/50 p-1 rounded-lg border border-slate-700 w-full lg:w-auto">
          <Clock className="w-4 h-4 text-slate-500 ml-2 mr-1" />
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex-1 lg:flex-none ${
                timeframe === tf 
                  ? 'bg-sky-500/25 text-sky-100 shadow-[0_0_20px_rgba(74,165,255,0.25)] border border-sky-300/40'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700/50'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        <button
          onClick={onAnalyze}
          disabled={loading}
          className="w-full lg:w-auto px-6 py-2.5 bg-gradient-to-r from-sky-500 to-cyan-500 hover:from-sky-400 hover:to-cyan-400 text-slate-950 font-semibold rounded-lg shadow-[0_14px_35px_rgba(41,154,255,0.35)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Analyzing...' : 'Run Intelligence'}
        </button>
      </div>
    </header>
  );
}
