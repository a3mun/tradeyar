/**
 * lib/thresholds.ts
 * آستانه‌های مرکزی — فاز ۱۴.۷.۳
 * ============================================================
 * 🔴 منبع واحد — هم SignalCard، هم TFTable
 * هم‌راستا با core/analyzer.py::_determine_signal
 * ماتریس ۵ سطح: (استراتژی × ریسک)
 */

export type ConfidenceLevel = "golden" | "strong" | "normal" | "weak" | "neutral";

export type Strategy = "scalp" | "swing" | "position";
export type RiskProfile = "aggressive" | "conservative";

/**
 * ماتریس min_confidence بر اساس (استراتژی × ریسک)
 * هم‌راستا با core/strategies.py::min_confidence_by_risk
 */
export const STRATEGY_MIN_CONF: Record<Strategy, Record<RiskProfile, number>> = {
  scalp: { aggressive: 30, conservative: 50 },
  swing: { aggressive: 40, conservative: 50 },
  position: { aggressive: 50, conservative: 60 },
};

/**
 * ماتریس min_votes بر اساس (استراتژی × ریسک)
 */
export const STRATEGY_MIN_VOTES: Record<Strategy, Record<RiskProfile, number>> = {
  scalp: { aggressive: 2, conservative: 3 },
  swing: { aggressive: 2, conservative: 3 },
  position: { aggressive: 3, conservative: 3 },
};

/**
 * دریافت min_conf برای (استراتژی، ریسک)
 */
export function getStrategyMinConf(
  strategy: string | undefined,
  riskProfile: string | undefined
): number {
  const s = (strategy as Strategy) || "swing";
  const r = (riskProfile as RiskProfile) || "aggressive";
  return STRATEGY_MIN_CONF[s]?.[r] ?? 45;
}

/**
 * دریافت min_votes برای (استراتژی، ریسک)
 */
export function getStrategyMinVotes(
  strategy: string | undefined,
  riskProfile: string | undefined
): number {
  const s = (strategy as Strategy) || "swing";
  const r = (riskProfile as RiskProfile) || "aggressive";
  return STRATEGY_MIN_VOTES[s]?.[r] ?? 2;
}

/**
 * سطح اطمینان بر اساس confidence (فقط برای رنگ‌بندی)
 * ⚠️ توجه: این تابع «آستانه‌ی استراتژی» را در نظر نمی‌گیرد.
 *    برای «فعال بودن سیگنال»، از `isSignalActive()` استفاده کن.
 *
 * آستانه‌ها (بدون min_conf):
 *   golden ≥85
 *   strong ≥70
 *   normal ≥45
 *   weak ≥25
 *   neutral <25
 */
export function getConfidenceLevel(
  confidence: number,
  isDirectional: boolean
): ConfidenceLevel {
  if (!isDirectional) {
    if (confidence >= 30) return "normal";
    if (confidence >= 15) return "weak";
    return "neutral";
  }
  if (confidence >= 85) return "golden";
  if (confidence >= 70) return "strong";
  if (confidence >= 45) return "normal";
  if (confidence >= 25) return "weak";
  return "neutral";
}

/**
 * آیا سیگنال «فعال» است؟ (باید در UI رنگ پررنگ بگیرد)
 *
 * منطق (هم‌راستا با backend):
 *    - confidence >= strategy_min_conf
 *    - direction ≠ neutral
 *    - signal from backend ≠ "در حال تشکیل" / "دور" / "خنثی"
 */
export function isSignalActive(
  confidence: number,
  direction: string,
  signal: string,
  strategy: string | undefined,
  riskProfile: string | undefined
): boolean {
  if (!direction || direction === "neutral") return false;
  const minConf = getStrategyMinConf(strategy, riskProfile);
  if (confidence < minConf) return false;
  if (!signal) return false;
  if (signal.includes("در حال تشکیل")) return false;
  if (signal.includes("دور")) return false;
  if (signal.includes("خنثی")) return false;
  return true;
}

/**
 * برچسب فارسی برای هر سطح
 */
export const LEVEL_LABEL_FA: Record<ConfidenceLevel, string> = {
  golden: "طلایی",
  strong: "قوی",
  normal: "معمولی",
  weak: "ضعیف",
  neutral: "خنثی",
};

/**
 * رنگ اصلی هر سطح
 */
export const LEVEL_COLOR: Record<ConfidenceLevel, string> = {
  golden: "#facc15",
  strong: "#22c55e",
  normal: "#3b82f6",
  weak: "#f97316",
  neutral: "#94a3b8",
};

/**
 * رنگ درصد اطمینان در نمودار میله‌ای (آبی)
 */
export const CONF_BAR_COLOR: Record<
  ConfidenceLevel,
  { text: string; bar: string }
> = {
  golden: { text: "#60a5fa", bar: "#3b82f6" },
  strong: { text: "#93c5fd", bar: "#60a5fa" },
  normal: { text: "#bfdbfe", bar: "#93c5fd" },
  weak: { text: "#dbeafe", bar: "#bfdbfe" },
  neutral: { text: "#e2e8f0", bar: "#cbd5e1" },
};