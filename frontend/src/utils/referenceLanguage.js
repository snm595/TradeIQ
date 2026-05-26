export function mapRegimeToReference(regime) {
  const key = (regime || '').toLowerCase();
  if (key === 'trending_up') {
    return {
      title: 'Directional Acceptance (Bull)',
      note: 'Control is accepted above value; trend continuation bias stays active.',
    };
  }
  if (key === 'trending_down') {
    return {
      title: 'Directional Acceptance (Bear)',
      note: 'Control is accepted below value; downside continuation bias stays active.',
    };
  }
  if (key === 'sideways') {
    return {
      title: 'VWAP Balance / Reversion Risk',
      note: 'Inside-control behavior and failed shifts suggest mean-reversion risk.',
    };
  }
  if (key === 'expansion') {
    return {
      title: 'Expansion Phase',
      note: 'Range expansion with directional pressure. Monitor breakout quality and rejection memory.',
    };
  }
  if (key === 'compression') {
    return {
      title: 'Compression Coil',
      note: 'Low displacement environment. Wait for clean control shift and acceptance.',
    };
  }
  return {
    title: 'Neutral Control',
    note: 'Await stronger confluence before execution.',
  };
}

export function buildReferenceChecklist(signal) {
  const reasons = signal?.reasons || [];
  const warnings = signal?.warnings || [];

  const checklist = [
    {
      key: 'vwap_control',
      label: 'VWAP Control',
      status: reasons.some((r) => r.toLowerCase().includes('vwap')) ? 'pass' : 'watch',
      good: 'Acceptance aligned',
      bad: 'Recheck control shift',
    },
    {
      key: 'ema_structure',
      label: 'EMA Structure',
      status: reasons.some((r) => r.toLowerCase().includes('ema')) ? 'pass' : 'watch',
      good: 'Trend filter aligned',
      bad: 'Slope/filter weak',
    },
    {
      key: 'volume_expansion',
      label: 'Volume Expansion',
      status: reasons.some((r) => r.toLowerCase().includes('volume')) ? 'pass' : 'watch',
      good: 'Participation confirmed',
      bad: 'No expansion edge',
    },
    {
      key: 'anti_chop',
      label: 'Anti-Chop Gate',
      status: warnings.some((w) => w.toLowerCase().includes('choppy') || w.toLowerCase().includes('failed breakout')) ? 'block' : 'pass',
      good: 'Directional environment',
      bad: 'Rejection/sideways memory',
    },
  ];

  return checklist;
}

export function referenceSummary(signal) {
  const decision = signal?.decision || 'WAIT';
  if (decision === 'TRADE') {
    return 'Confluence threshold passed. Structure + value control align for execution.';
  }
  if ((signal?.signal || '').toUpperCase() === 'NO SIGNAL') {
    return 'No directional trigger. Engine is waiting for control shift confirmation.';
  }
  return 'Setup rejected by quality gates. Recheck acceptance, volume, and anti-chop context.';
}
