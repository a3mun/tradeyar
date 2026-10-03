/**
 * لایه نمایش — ترجمه مقادیر خام بک‌اند به فارسی
 * هم‌راستا با core/contracts.py (Regime, Consensus, Signal)
 */

// ═══════════════════════════════════════════════════════════
// رژیم بازار
// ═══════════════════════════════════════════════════════════
export const REGIME_FA: Record<
  string,
  { icon: string; text: string; short: string; color: string }
> = {
  trend: {
    icon: "📈",
    text: "بازار جهت‌دار",
    short: "جهت‌دار",
    color: "text-green-500",
  },
  transitional: {
    icon: "⚖️",
    text: "بازار در حال‌تغییر",
    short: "در حال‌تغییر",
    color: "text-yellow-500",
  },
  range: {
    icon: "📊",
    text: "بازار بی‌جهت",
    short: "بی‌جهت",
    color: "text-muted-foreground",
  },
};

// ═══════════════════════════════════════════════════════════
// اجماع
// ═══════════════════════════════════════════════════════════
export const CONSENSUS_FA: Record<string, { text: string; color: string }> = {
  strong: { text: "🔥 اجماع قوی", color: "text-green-500" },
  normal: { text: "✅ اجماع معمولی", color: "text-blue-500" },
  weak: { text: "⚠️ اجماع ضعیف", color: "text-yellow-500" },
  neutral: { text: "⚪ بدون اجماع", color: "text-muted-foreground" },
};

// ═══════════════════════════════════════════════════════════
// گروه‌ها
// ═══════════════════════════════════════════════════════════
export const GROUP_FA: Record<
  string,
  { icon: string; name: string; desc: string }
> = {
  momentum: {
    icon: "⚡",
    name: "مومنتوم",
    desc: "RSI، Stochastic، Williams، CCI، ROC",
  },
  trend: {
    icon: "📈",
    name: "روند",
    desc: "EMA200، MACD، ADX، Supertrend، Ichimoku",
  },
  volatility: {
    icon: "📊",
    name: "نوسان",
    desc: "Bollinger، ATR، Keltner، Donchian، StdDev",
  },
  volume: {
    icon: "💧",
    name: "حجم",
    desc: "OBV، CVD، Delta، CMF، MFI، Absorption",
  },
  structure: {
    icon: "🏗",
    name: "ساختار",
    desc: "Pivot، Swing، Fibonacci، S/R",
  },
};

// ═══════════════════════════════════════════════════════════
// تله‌ها
// ═══════════════════════════════════════════════════════════
export const TRAP_FA: Record<string, string> = {
  bull_trap: "🚨 تله صعودی",
  bear_trap: "🚨 تله نزولی",
  fake_breakout: "⚠️ شکست جعلی",
  exhaustion: "😮‍💨 خستگی روند",
};

// ═══════════════════════════════════════════════════════════
// ابزارهای ترجمه
// ═══════════════════════════════════════════════════════════
export function regimeFa(regime: string): string {
  return REGIME_FA[regime]?.short || regime;
}

export function regimeFullFa(regime: string): string {
  return REGIME_FA[regime]?.text || regime;
}

export function regimeIcon(regime: string): string {
  return REGIME_FA[regime]?.icon || "📊";
}

export function regimeColor(regime: string): string {
  return REGIME_FA[regime]?.color || "text-muted-foreground";
}

export function consensusFa(consensus: string): string {
  return CONSENSUS_FA[consensus]?.text || consensus;
}

export function consensusColor(consensus: string): string {
  return CONSENSUS_FA[consensus]?.color || "text-muted-foreground";
}

export function groupFa(key: string): string {
  return GROUP_FA[key]?.name || key;
}

export function groupIcon(key: string): string {
  return GROUP_FA[key]?.icon || "•";
}

export function trapFa(key: string): string {
  return TRAP_FA[key] || key;
}

// ═══════════════════════════════════════════════════════════
// رنگ سیگنال
// ═══════════════════════════════════════════════════════════
export function signalColor(signal: string): string {
  if (signal.includes("LONG")) return "text-green-500";
  if (signal.includes("SHORT")) return "text-red-500";
  return "text-yellow-500";
}

export function signalBg(signal: string): string {
  if (signal.includes("LONG"))
    return "bg-green-500/10 border-green-500/30";
  if (signal.includes("SHORT"))
    return "bg-red-500/10 border-red-500/30";
  return "bg-yellow-500/10 border-yellow-500/30";
}

// ═══════════════════════════════════════════════════════════
// رنگ‌بندی اطمینان
// ═══════════════════════════════════════════════════════════
export function confidenceColor(conf: number): string {
  if (conf >= 70) return "text-green-500";
  if (conf >= 50) return "text-blue-500";
  if (conf >= 30) return "text-yellow-500";
  return "text-muted-foreground";
}

// ═══════════════════════════════════════════════════════════
// اعداد با کاما
// ═══════════════════════════════════════════════════════════
export function formatNumber(n: number, decimals = 2): string {
  if (!isFinite(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}

// ═══════════════════════════════════════════════════════════
// رنگ Fear & Greed
// ═══════════════════════════════════════════════════════════
export function fearGreedColor(value: number): string {
  if (value <= 20) return "#ef4444";
  if (value <= 40) return "#f97316";
  if (value <= 60) return "#eab308";
  if (value <= 80) return "#22c55e";
  return "#10b981";
}