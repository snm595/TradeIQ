import { Activity, Clock, Play, Radio, RefreshCw, Search, Star } from 'lucide-react';
import { useMemo, useState } from 'react';

const CORE_PAIRS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL'];
const FAVORITES_KEY = 'tradeiq.favoritePairs';
const RECENTS_KEY = 'tradeiq.recentPairs';

const formatInterval = (ms) => {
  if (ms < 60000) return `${Math.round(ms / 1000)} sec`;
  return `${Math.round(ms / 60000)} min`;
};

const readStoredList = (key, fallback) => {
  try {
    const stored = JSON.parse(window.localStorage.getItem(key));
    return Array.isArray(stored) && stored.length ? stored : fallback;
  } catch {
    return fallback;
  }
};

export default function Header({
  ticker,
  setTicker,
  timeframe,
  setTimeframe,
  onAnalyze,
  loading,
  refreshing,
  refreshInterval,
  setRefreshInterval,
  lastUpdated,
  nextRefreshAt
}) {
  const timeframes = ['5m', '15m', '1h', '4h', '1d'];
  const intervals = [15000, 30000, 45000, 60000, 180000, 300000, 900000];
  const [query, setQuery] = useState(ticker);
  const [favorites, setFavorites] = useState(() => readStoredList(FAVORITES_KEY, ['SPY', 'QQQ', 'BTC-USD']));
  const [recents, setRecents] = useState(() => readStoredList(RECENTS_KEY, []));

  const pairOptions = useMemo(() => {
    const merged = [...favorites, ...recents, ...CORE_PAIRS, query.toUpperCase()].filter(Boolean);
    return [...new Set(merged)].filter((pair) => pair.includes(query.trim().toUpperCase())).slice(0, 9);
  }, [favorites, recents, query]);

  const selectPair = (pair) => {
    const normalized = pair.trim().toUpperCase();
    if (!normalized) return;

    setTicker(normalized);
    setQuery(normalized);
    const nextRecents = [normalized, ...recents.filter((item) => item !== normalized)].slice(0, 6);
    setRecents(nextRecents);
    window.localStorage.setItem(RECENTS_KEY, JSON.stringify(nextRecents));
  };

  const toggleFavorite = () => {
    const normalized = ticker.trim().toUpperCase();
    const nextFavorites = favorites.includes(normalized)
      ? favorites.filter((item) => item !== normalized)
      : [normalized, ...favorites].slice(0, 8);

    setFavorites(nextFavorites);
    window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(nextFavorites));
  };

  const lastLabel = lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'pending';
  const nextLabel = nextRefreshAt ? nextRefreshAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'arming';
  const isFavorite = favorites.includes(ticker);

  return (
    <header className="panel px-4 py-4 flex flex-col gap-6 justify-between">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-lg bg-sky-500/12 flex items-center justify-center border border-sky-300/35 shadow-[0_0_24px_rgba(80,168,255,0.25)]">
          <Activity className="text-sky-200 w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">TradeIQ Intelligence Fabric</h1>
          <p className="text-xs text-slate-400 font-medium uppercase tracking-[0.18em]">Live institutional market monitor</p>
        </div>
      </div>

      <div className="flex flex-wrap items-start xl:items-center gap-3 w-full">
        <div className="ticker-search-wrapper group w-full xl:w-72">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-500" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2.5 border border-slate-700 rounded-lg bg-slate-900/50 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-400/70 transition-all uppercase"
            placeholder="Search pair or enter ticker"
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && selectPair(query)}
          />
          <div className="ticker-dropdown hidden group-focus-within:block hover:block">
            <div className="rounded-lg border border-slate-700 bg-slate-950/95 shadow-2xl p-2 grid gap-1">
              {pairOptions.map((pair) => (
                <button
                  key={pair}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => selectPair(pair)}
                  className="flex items-center justify-between rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100"
                >
                  <span>{pair}</span>
                  {favorites.includes(pair) && <Star className="w-3.5 h-3.5 text-amber-300 fill-amber-300" />}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={toggleFavorite}
          className="h-10 w-10 rounded-lg border border-slate-700 bg-slate-900/50 text-slate-300 grid place-items-center hover:text-amber-200 hover:border-amber-300/50"
          title={isFavorite ? 'Remove favorite' : 'Add favorite'}
        >
          <Star className={`w-4 h-4 ${isFavorite ? 'fill-amber-300 text-amber-300' : ''}`} />
        </button>

        <div className="flex items-center bg-slate-900/50 p-1 rounded-lg border border-slate-700 w-full xl:w-auto">
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

        <select
          value={refreshInterval}
          onChange={(e) => setRefreshInterval(Number(e.target.value))}
          className="h-10 rounded-lg border border-slate-700 bg-slate-900/50 px-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-400/70"
          title="Refresh interval"
        >
          {intervals.map((interval) => (
            <option key={interval} value={interval}>
              {formatInterval(interval)}
            </option>
          ))}
        </select>

        <button
          onClick={onAnalyze}
          disabled={loading}
          className="h-10 w-full xl:w-10 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-100 border border-sky-300/40 grid place-items-center transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title="Refresh intelligence now"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        </button>

        <div className="min-w-56 rounded-lg border border-emerald-300/20 bg-emerald-400/8 px-3 py-2 text-xs text-slate-300">
          <div className="flex items-center gap-2 text-emerald-200 font-semibold">
            <Radio className={`w-3.5 h-3.5 ${refreshing ? 'animate-pulse' : ''}`} />
            {refreshing ? 'Refreshing intelligence' : 'Auto intelligence online'}
          </div>
          <div className="mt-1 text-slate-500">Last {lastLabel} • Next {nextLabel}</div>
        </div>
      </div>
    </header>
  );
}
