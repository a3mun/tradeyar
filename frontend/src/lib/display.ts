/**
 * lib/display.ts — توابع کمکی نمایش
 * ============================================================
 * 🎨 پالت رنگ Trademun:
 *   • LONG / صعودی  → سبز   (#22c55e)
 *   • SHORT / نزولی → قرمز  (#ef4444)
 *   • خنثی          → خاکستری (#64748b)
 *   • اطمینان       → سبز/زرد/خاکستری (بر اساس مقدار)
 *   • SL            → قرمز
 *   • TP            → سبز
 *   • Entry         → خاکستری روشن
 */

// ═══════════════════════════════════════════════════════════
// اعداد — فرمت‌بندی
// ═══════════════════════════════════════════════════════════

/**
 * formatNumber — فرمت عدد با کاما
 * ============================================================
 * مثال:
 *   formatNumber(85187)    → "85,187"
 *   formatNumber(4163.05)  → "4,163.05"
 *   formatNumber(0.006223) → "0.006223"
 *   formatNumber(null)     → "—"
 */
export function formatNumber(
  value: number | null | undefined,
  options?: { maxDecimals?: number }
): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value === 0) return "0";

  const abs = Math.abs(value);

  // ─── اعداد خیلی کوچیک: نمایش دقت کامل ───
  if (abs < 0.001) {
    return value.toString();
  }
  if (abs < 1) {
    const fixed = value.toFixed(6);
    return fixed.replace(/\.?0+$/, "");
  }

  // ─── اعداد معمولی ───
  const maxDecimals = options?.maxDecimals ?? 2;
  return value.toLocaleString("en-US", {
    maximumFractionDigits: maxDecimals,
  });
}


/**
 * formatCompact — فرمت فشرده برای موبایل
 */
export function formatCompact(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);

  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  if (abs >= 1) return value.toFixed(2);
  if (abs >= 0.01) return value.toFixed(4);
  return value.toString();
}


// ═══════════════════════════════════════════════════════════
// سیگنال — رنگ‌ها
// ═══════════════════════════════════════════════════════════

/**
 * signalColor — رنگ متن سیگنال
 */
export function signalColor(signal: string | null | undefined): string {
  if (!signal) return "text-slate-400";
  const s = signal.toUpperCase();

  if (
    s.includes("LONG") ||
    signal.includes("صعودی") ||
    signal.includes("خرید")
  ) {
    return "text-green-500";
  }
  if (
    s.includes("SHORT") ||
    signal.includes("نزولی") ||
    signal.includes("فروش")
  ) {
    return "text-red-500";
  }
  return "text-slate-400"; // خنثی
}


/**
 * signalBg — پس‌زمینه‌ی کارت سیگنال
 */
export function signalBg(signal: string | null | undefined): string {
  if (!signal) return "border-slate-500/20 bg-slate-500/5";
  const s = signal.toUpperCase();

  if (
    s.includes("LONG") ||
    signal.includes("صعودی") ||
    signal.includes("خرید")
  ) {
    return "border-green-500/30 bg-green-500/5";
  }
  if (
    s.includes("SHORT") ||
    signal.includes("نزولی") ||
    signal.includes("فروش")
  ) {
    return "border-red-500/30 bg-red-500/5";
  }
  return "border-slate-500/20 bg-slate-500/5";
}


/**
 * confidenceColor — رنگ بج اطمینان
 */
export function confidenceColor(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "text-muted-foreground";
  if (value >= 70) return "text-green-500";
  if (value >= 50) return "text-yellow-500";
  return "text-muted-foreground";
}


// ═══════════════════════════════════════════════════════════
// اجماع
// ═══════════════════════════════════════════════════════════

export function consensusFa(consensus: string | null | undefined): string {
  if (!consensus) return "—";
  const map: Record<string, string> = {
    strong: "✅ اجماع قوی",
    normal: "✅ اجماع معمولی",
    weak: "⚠️ اجماع ضعیف",
    none: "⚪ بدون اجماع",
    neutral: "⚪ بدون اجماع",
  };
  return map[consensus] || consensus;
}


export function consensusColor(consensus: string | null | undefined): string {
  if (!consensus) return "text-muted-foreground";
  const map: Record<string, string> = {
    strong: "text-green-500",
    normal: "text-blue-500",
    weak: "text-yellow-500",
    none: "text-slate-400",
    neutral: "text-slate-400",
  };
  return map[consensus] || "text-muted-foreground";
}


// ═══════════════════════════════════════════════════════════
// رژیم بازار
// ═══════════════════════════════════════════════════════════

export function regimeFa(regime: string | null | undefined): string {
  if (!regime) return "—";
  const map: Record<string, string> = {
    trend: "جهت‌دار",
    transitional: "در حال‌تغییر",
    range: "بی‌جهت",
  };
  return map[regime] || regime;
}


export function regimeFullFa(regime: string | null | undefined): string {
  if (!regime) return "—";
  const map: Record<string, string> = {
    trend: "بازار جهت‌دار",
    transitional: "بازار در حال‌تغییر",
    range: "بازار بی‌جهت",
  };
  return map[regime] || regime;
}


export function regimeIcon(regime: string | null | undefined): string {
  if (!regime) return "⚪";
  const map: Record<string, string> = {
    trend: "📈",
    transitional: "⚖️",
    range: "🔀",
  };
  return map[regime] || "⚪";
}


// ═══════════════════════════════════════════════════════════
// Fear & Greed
// ═══════════════════════════════════════════════════════════

/**
 * fearGreedColor — رنگ شاخص ترس و طمع
 * ============================================================
 *   • ≤ ۲۰  → ترس شدید     → قرمز
 *   • ≤ ۴۰  → ترس          → نارنجی
 *   • ≤ ۶۰  → خنثی         → زرد
 *   • ≤ ۸۰  → طمع          → سبز روشن
 *   • > ۸۰  → طمع شدید     → سبز
 */
export function fearGreedColor(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "text-muted-foreground";
  if (value <= 20) return "text-red-600";
  if (value <= 40) return "text-orange-500";
  if (value <= 60) return "text-yellow-500";
  if (value <= 80) return "text-green-500";
  return "text-emerald-500";
}


// ═══════════════════════════════════════════════════════════
// اعداد فارسی
// ═══════════════════════════════════════════════════════════

export function toFaDigits(value: string | number): string {
  const faDigits = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
  return String(value).replace(/\d/g, (d) => faDigits[parseInt(d, 10)]);
}


// ═══════════════════════════════════════════════════════════
// درصد
// ═══════════════════════════════════════════════════════════

export function formatPercent(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}٪`;
}


export function formatPercentSimple(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toFixed(decimals)}٪`;
}


// ═══════════════════════════════════════════════════════════
// R:R
// ═══════════════════════════════════════════════════════════

export function formatRR(rr: number | null | undefined): string {
  if (rr == null || Number.isNaN(rr)) return "—";
  return rr.toFixed(2);
}


export function rrColor(rr: number | null | undefined): string {
  if (rr == null) return "text-muted-foreground";
  if (rr >= 2) return "text-green-500";
  if (rr >= 1) return "text-blue-500";
  return "text-red-500";
}