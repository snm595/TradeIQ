import { Activity, BarChart3, BrainCircuit, Shield, Sparkles } from 'lucide-react';

const items = [
  { icon: Activity, label: 'Pulse', id: 'pulse' },
  { icon: BarChart3, label: 'Market', id: 'market' },
  { icon: BrainCircuit, label: 'AI', id: 'ai' },
  { icon: Shield, label: 'Risk', id: 'risk' },
  { icon: Sparkles, label: 'Labs', id: 'labs' },
];

export default function SidebarNav({ activeSection = 'pulse', onNavigate }) {
  return (
    <aside className="panel hidden md:flex flex-col justify-between items-center py-4 px-2 relative z-2">
      <div className="w-12 h-12 rounded-xl border border-sky-300/35 bg-sky-400/10 grid place-items-center shadow-[0_0_24px_rgba(74,165,255,0.3)]">
        <BrainCircuit className="w-6 h-6 text-sky-200" />
      </div>
      <nav className="flex flex-col gap-3">
        {items.map((item) => (
          <button
            key={item.label}
            onClick={() => onNavigate?.(item.id)}
            className={`w-11 h-11 rounded-xl border transition-all grid place-items-center ${
              activeSection === item.id
                ? 'bg-sky-500/15 border-sky-300/45 text-sky-200 shadow-[0_0_26px_rgba(60,153,255,0.24)]'
                : 'bg-slate-900/30 border-slate-700/70 text-slate-400 hover:text-slate-200 hover:border-slate-500'
            }`}
            aria-label={item.label}
            title={item.label}
          >
            <item.icon className="w-5 h-5" />
          </button>
        ))}
      </nav>
      <div className="text-[10px] tracking-[0.24em] uppercase text-slate-500 [writing-mode:vertical-rl] rotate-180">
        TradeIQ
      </div>
    </aside>
  );
}
