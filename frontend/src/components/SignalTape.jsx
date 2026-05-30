import { Activity, Ban, CheckCircle2, Clock, TrendingDown, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';

const compact = (value) => String(value || 'unknown').replaceAll('_', ' ');

const EventIcon = ({ event }) => {
  if (event.decision === 'TRADE' && event.signal === 'BUY') return <TrendingUp className="w-4 h-4 text-emerald-200" />;
  if (event.decision === 'TRADE' && event.signal === 'SELL') return <TrendingDown className="w-4 h-4 text-rose-200" />;
  if (event.decision === 'REJECT') return <Ban className="w-4 h-4 text-amber-200" />;
  return <Activity className="w-4 h-4 text-sky-200" />;
};

export default function SignalTape({ events }) {
  return (
    <section className="panel p-5 signal-tape-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Auto Signal Timeline</p>
          <h2 className="panel-title">Institutional Signal Tape</h2>
        </div>
        <span className="price-chip">
          <span className="status-dot status-dot-live" />
          {events.length} events
        </span>
      </div>

      <div className="signal-tape-list">
        {events.length ? events.map((event) => {
          const eventTime = event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'live';
          const rejected = event.decision === 'REJECT';
          const active = event.decision === 'TRADE';

          return (
            <div key={event.id} className="signal-tape-row">
              <div className={clsx('signal-tape-icon', active && 'signal-tape-icon-active', rejected && 'signal-tape-icon-reject')}>
                <EventIcon event={event} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-slate-100">{event.ticker}</span>
                  <span className="text-xs text-slate-500">{event.timeframe}</span>
                  <span className={clsx(
                    'rounded-md px-2 py-0.5 text-[11px] font-semibold',
                    active ? 'bg-emerald-400/12 text-emerald-200' : rejected ? 'bg-amber-400/12 text-amber-200' : 'bg-sky-400/12 text-sky-200'
                  )}>
                    {event.decision}
                  </span>
                  <span className="text-xs text-slate-400">{event.signal || 'NONE'}</span>
                </div>
                <p className="mt-1 truncate text-xs text-slate-400">
                  {compact(event.regime)} • confidence {Math.round(event.confidence || 0)}%
                  {event.continuation !== null && event.continuation !== undefined ? ` • continuation ${Math.round(event.continuation)}%` : ''}
                </p>
                {event.warnings?.length > 0 && (
                  <p className="mt-1 truncate text-xs text-amber-200/80">{event.warnings[0]}</p>
                )}
              </div>
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                {eventTime}
              </div>
            </div>
          );
        }) : (
          <div className="signal-tape-empty">
            <CheckCircle2 className="w-5 h-5 text-emerald-200" />
            <span>Awaiting first live intelligence cycle</span>
          </div>
        )}
      </div>
    </section>
  );
}
