import { AlertTriangle, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { mapRegimeToReference } from '../utils/referenceLanguage';

export default function RegimePanel({ regime }) {
  if (!regime) return null;

  const { current_regime, description, is_choppy } = regime;
  const reference = mapRegimeToReference(current_regime);

  const getConfig = () => {
    switch (current_regime) {
      case 'trending_up':
        return { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' };
      case 'trending_down':
        return { icon: TrendingDown, color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' };
      case 'sideways':
        return { icon: Minus, color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/20' };
      case 'high_volatility':
      case 'expansion':
        return { icon: Activity, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' };
      case 'low_volatility':
      case 'compression':
        return { icon: Minus, color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20' };
      default:
        return { icon: Minus, color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/20' };
    }
  };

  const config = getConfig();
  const Icon = config.icon;

  const formatRegimeName = (name) => {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  return (
    <section className="panel p-5 flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-2">
        <Activity className="w-5 h-5 text-cyan-300" />
        <h3 className="font-semibold text-lg">AI Market Intelligence Module</h3>
      </div>

      <div className={`p-4 rounded-xl border ${config.border} ${config.bg} flex items-start gap-4 transition-all relative overflow-hidden`}>
        <div className="absolute inset-0 pointer-events-none bg-gradient-to-r from-white/3 to-transparent" />
        <div className={`p-2 rounded-lg ${config.bg} ${config.color} border ${config.border}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <h4 className={`font-bold text-lg ${config.color} tracking-tight`}>
            {formatRegimeName(current_regime)}
          </h4>
          <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
            {description}
          </p>
          <p className="text-xs text-slate-400 mt-2">{reference.title} • {reference.note}</p>
        </div>
      </div>

      {is_choppy && (
        <div className="mt-2 flex items-center gap-2 text-amber-400 bg-amber-400/10 border border-amber-400/20 p-3 rounded-lg text-sm font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <p>Anti-chop filter active. Directional signals may be suppressed.</p>
        </div>
      )}
    </section>
  );
}
