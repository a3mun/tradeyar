
"use client";

/**
 * DeepAnalysis — تحلیل و چرایی (نسخه ۱۰.۱ · Logic Improved)
 * ============================================================
 * بهبود منطق توضیحات و پیشنهاد اقدام
 * حفظ ساختار و ظاهر نسخه اصلی
 */

import {
  AlertTriangle,
  GitBranch,
  Lightbulb,
  Zap,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppStore } from "@/store/useAppStore";
import { useSignalData } from "@/hooks/useSignalData";

const TRAP_LABELS: Record<string, string> = {
  bull_trap: "تله صعودی",
  bear_trap: "تله نزولی",
  fake_breakout: "شکست جعلی",
  exhaustion: "خستگی روند",
};

const STRATEGY_LABELS: Record<
  string,
  { fa: string; icon: string; why: string }
> = {
  scalp: {
    fa: "اسکالپ",
    icon: "⚡",
    why: "تحلیل سریع برای معاملات ۱-۵ دقیقه",
  },
  swing: {
    fa: "سوئینگ",
    icon: "🌊",
    why: "تحلیل میان‌مدت — از ۱۵ دقیقه تا روزانه",
  },
  position: {
    fa: "پوزیشن",
    icon: "🏛",
    why: "تحلیل بلندمدت — چند روز تا چند هفته",
  },
};

function buildNarrative(data: any): {
  headline: string;
  why: string;
  action: string;
} {
  const signal = String(data.signal || "");
  const conf = Number(data.confidence ?? 0);
  const strategy = data.strategy || "swing";
  const strategyMeta =
    STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;

  // ابتدا وضعیت‌های خاص را تشخیص می‌دهیم تا direction خنثی
  // باعث اشتباه در تشخیص «در حال تشکیل» یا «دور» نشود.
  const isForming = signal.includes("در حال تشکیل");
  const isFar = signal.includes("دور");

  const isLong = !isForming && !isFar && (
    data.direction === "long" || signal.includes("LONG")
  );

  const isShort = !isForming && !isFar && (
    data.direction === "short" || signal.includes("SHORT")
  );

  const isWeak = signal.includes("ضعیف");

  let headline = "";

  if (isForming) {
    headline = "در حال تشکیل — هنوز سیگنال کامل نشده";
  } else if (isFar) {
    headline = "دور از ورود — فعلاً صبر کن";
  } else if (isLong) {
    headline = isWeak
      ? "خرید ضعیف — بهتره با احتیاط عمل کنی"
      : conf >= 70
      ? "خرید قوی — شرایط مساعدتره"
      : "سیگنال خرید — هنوز به تأیید بیشتری نیاز داره";
  } else if (isShort) {
    headline = isWeak
      ? "فروش ضعیف — ریسک بالاتره، با احتیاط"
      : conf >= 70
      ? "فروش قوی — شرایط مساعدتره"
      : "سیگنال فروش — هنوز به تأیید بیشتری نیاز داره";
  } else {
    headline = "بدون سیگنال — بهترین کار، صبر کردنه";
  }

  const reasons = Array.isArray(data.reasons)
    ? data.reasons.filter((r: unknown) => typeof r === "string")
    : [];

  let why = "";

  if (isLong || isShort) {
    const dirFa = isLong ? "صعودی" : "نزولی";

    const strengths = reasons
      .filter(
        (r: string) =>
          !r.includes("⚠️") && !r.includes("🚫")
      )
      .map((r: string) =>
        r.replace(/[🟢🟡🟠🔴⚡✅💧📈📊🏗💎]/g, "").trim()
      )
      .filter((r: string) => r.length > 5)
      .slice(0, 2);

    if (strengths.length > 0) {
      why = `چند دلیل برای ${dirFa} بودن بازار داریم:\n${strengths
        .map((s: string) => `• ${s}`)
        .join("\n")}`;
    } else {
      why = `جهت تحلیل فعلی ${dirFa} است، اما توضیح مشخصی از دلایل این جهت در داده‌های تحلیل دریافت نشده است.\n• اطمینان فعلی: ${conf}٪`;
    }

    // هشدارهای موجود در دلایل تحلیل را از کاربر پنهان نمی‌کنیم.
    const warnings = reasons
      .filter(
        (r: string) =>
          r.includes("⚠️") || r.includes("🚫")
      )
      .map((r: string) =>
        r.replace(/[🟢🟡🟠🔴⚡✅💧📈📊🏗💎]/g, "").trim()
      )
      .filter((r: string) => r.length > 3)
      .slice(0, 2);

    if (warnings.length > 0) {
      why += `\n\nنکات احتیاطی:\n${warnings
        .map((s: string) => `• ${s}`)
        .join("\n")}`;
    }
  } else if (isForming) {
    why = `شرایط داره آماده می‌شه، ولی هنوز به آستانه‌ی سیگنال معامله‌ای نرسیده.\n• اطمینان فعلی: ${conf}٪\n• استراتژی ${strategyMeta.fa} نیاز به اطمینان و تأیید متناسب با خودش داره\n• کمی صبر کن و دوباره شرایط رو بررسی کن.`;
  } else if (isFar) {
    why = `جهت بازار ممکنه در حال شکل‌گیری باشه، اما قیمت هنوز در محدوده مناسبی برای ورود نیست.\n• ورود در این نقطه می‌تونه نسبت ریسک به بازده رو نامناسب کنه\n• بهتره منتظر نزدیک شدن قیمت به محدوده مناسب باشی\n• از تعقیب قیمت بعد از حرکت شدید خودداری کن.`;
  } else {
    const neutral = data.neutral_explain;

    if (typeof neutral === "string" && neutral.trim()) {
      why = neutral.trim();
    } else if (neutral && typeof neutral === "object") {
      why = [
        neutral.short,
        neutral.long,
        neutral.hint,
      ]
        .filter(
          (v: unknown) =>
            typeof v === "string" && v.trim().length > 0
        )
        .join("\n");
    }

    if (!why) {
      why = `بازار در حال حاضر جهت مشخص و قابل اتکایی نداره.\n• گروه‌های تحلیل هنوز هم‌جهت نیستن\n• شواهد کافی برای انتخاب یک جهت معاملاتی وجود نداره\n• صبر می‌تونه تصمیم منطقی‌تری باشه.`;
    }
  }

  let action = "";

  // اولویت با وضعیت واقعی سیگنال است، نه صرفاً درصد اطمینان.
  if (isForming) {
    action = `فعلاً وارد نشو — سیگنال هنوز کامل نشده.\nچند دقیقه دیگه شرایط رو دوباره بررسی کن یا هماهنگی تایم‌فریم‌های دیگه رو ببین.`;
  } else if (isFar) {
    action = `در این قیمت وارد نشو — از نقطه مناسب ورود فاصله داریم.\nمنتظر اصلاح قیمت یا شکل‌گیری موقعیت مناسب‌تر بمون.\nقیمت رو صرفاً به‌خاطر حرکت سریعش تعقیب نکن.`;
  } else if (isLong && isWeak) {
    action = `برای خرید عجله نکن — حرکت هنوز قدرت کافی نداره.\nمنتظر تأیید بیشتر و تثبیت حرکت صعودی بمون.\nاگر قصد معامله داری، حجم رو متناسب با حد ضرر و ریسک مجازت تعیین کن.`;
  } else if (isShort && isWeak) {
    action = `برای فروش عجله نکن — حرکت نزولی هنوز قدرت کافی نداره.\nمنتظر تأیید بیشتر و تثبیت روند نزولی بمون.\nاگر قصد معامله داری، حجم رو متناسب با حد ضرر و ریسک مجازت تعیین کن.`;
  } else if (isLong && conf >= 70) {
    action = `جهت تحلیل صعودیه و شواهد قوی‌تری داریم؛ می‌تونی موقعیت خرید رو بررسی کنی.\nقبل از ورود، محدوده ورود و حد ضرر رو بررسی کن و مدیریت سرمایه رو رعایت کن.\nاگر قیمت از نقطه مناسب ورود فاصله گرفته، دنبالش نرو.`;
  } else if (isLong) {
    action = `سیگنال خرید داریم، اما اطمینان هنوز به سطح بالایی نرسیده.\nبهتره برای ورود منتظر تأیید بیشتر بمونی.\nاگر شرایط ورود فراهم شد، حد ضرر و مدیریت سرمایه رو رعایت کن.`;
  } else if (isShort && conf >= 70) {
    action = `جهت تحلیل نزولیه و شواهد قوی‌تری داریم؛ می‌تونی موقعیت فروش رو بررسی کنی.\nقبل از ورود، محدوده مناسب و حد ضرر رو بررسی کن.\nدر نوسانات شدید از افزایش بی‌رویه حجم معامله خودداری کن.`;
  } else if (isShort) {
    action = `سیگنال فروش داریم، اما اطمینان هنوز به سطح بالایی نرسیده.\nبهتره برای ورود منتظر تأیید بیشتر بمونی.\nاگر شرایط ورود فراهم شد، حد ضرر و مدیریت سرمایه رو رعایت کن.`;
  } else {
    action = `وارد معامله جهت‌دار نشو — هنوز سیگنال واضحی نداریم.\nصبر کن تا شرایط بازار روشن‌تر و گروه‌های تحلیل هماهنگ‌تر بشن.\nگاهی بهترین تصمیم، انجام ندادن معامله است.`;
  }

  return { headline, why, action };
}

function ScenarioCard({
  scenario,
  mainDirection,
}: {
  scenario: any;
  mainDirection: string;
}) {
  const colorMap: Record<string, string> = {
    green: "border-green-500/20 bg-green-500/5 text-green-400/90",
    red: "border-red-500/20 bg-red-500/5 text-red-400/90",
    yellow: "border-[#d6ad60]/20 bg-[#d6ad60]/5 text-[#d6ad60]/90",
  };

  const color = scenario.color || "yellow";

  // صفر یک مقدار معتبر است و نباید با مقدار پیش‌فرض جایگزین شود.
  const rawProbability = Number(scenario.probability);
  const hasProbability =
    scenario.probability !== null &&
    scenario.probability !== undefined &&
    Number.isFinite(rawProbability);

  const probability = hasProbability
    ? Math.max(
        0,
        Math.min(
          100,
          Math.round(
            rawProbability <= 1
              ? rawProbability * 100
              : rawProbability
          )
        )
      )
    : null;

  const condition = scenario.condition || "";
  const action = scenario.action || "";

  const isLongScenario =
    /\bLONG\b/i.test(action) || scenario.type === "long";

  const isShortScenario =
    /\bSHORT\b/i.test(action) || scenario.type === "short";

  const isConflict =
    (mainDirection === "short" && isLongScenario) ||
    (mainDirection === "long" && isShortScenario);

  return (
    <div
      className={`rounded-lg border p-2.5 ${
        colorMap[color] || colorMap.yellow
      } transition-all hover:bg-white/5 relative`}
    >
      {isConflict && (
        <div className="absolute -top-2 -left-2 rounded bg-orange-600 text-[8px] font-bold text-white px-1.5 py-0.5 shadow-sm z-10">
          ⚠️ خلاف جهت
        </div>
      )}

      <div className="flex items-start gap-2">
        <span className="text-[16px] mt-0.5 shrink-0">
          {scenario.icon || "•"}
        </span>

        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="text-[11px] font-medium leading-relaxed text-foreground/90">
            {condition}
          </p>

          <p className="text-[10.5px] leading-relaxed text-foreground/75">
            ↪ {action}
          </p>

          {probability !== null && (
            <div className="flex items-center gap-2 pt-1">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/30">
                <div
                  className="h-full rounded-full bg-current opacity-80"
                  style={{ width: `${probability}%` }}
                />
              </div>

              <span className="num shrink-0 text-[9px] font-bold text-muted-foreground whitespace-nowrap">
                شانس موفقیت {probability}٪
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function DeepAnalysis() {
  const { timeframe, strategy } = useAppStore();
  const { data, loading } = useSignalData();

  const pumpScore = data?.pump_score ?? 0;
  const dumpScore = data?.dump_score ?? 0;
  const pumpWarning = data?.pump_warning || "none";
  const pumpType = data?.pump_type || "none";

  if (loading && !data) {
    return (
      <div className="space-y-2 rounded-lg border border-white/10 bg-white/5 p-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  if (!data) {
    return (
      <p className="py-4 text-center text-xs text-muted-foreground">
        ⏳ تحلیل برای {timeframe} در دسترس نیست
      </p>
    );
  }

  const traps = data.traps || {};

  const activeTraps = Object.entries(traps)
    .filter(([, v]) => (v as { active?: boolean })?.active)
    .map(([k]) => k);

  const scenarios = data.scenarios || [];
  const mainDirection = data.direction || "neutral";
  const strategyMeta =
    STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;

  const narrative = buildNarrative({
    ...data,
    strategy: data.strategy || strategy,
  });

  const actionIsPositive =
    (mainDirection === "long" || mainDirection === "short") &&
    !narrative.action.includes("عجله نکن") &&
    !narrative.action.includes("وارد نشو");

  const actionIsNegative =
    narrative.action.includes("وارد نشو");

  return (
    <div className="space-y-3">
      {/* هشدار Pump/Dump */}
      {pumpWarning !== "none" && (
        <div
          className={`rounded-lg border px-2.5 py-2 ${
            pumpWarning === "alert"
              ? "border-red-500/30 bg-red-500/5"
              : "border-[#d6ad60]/30 bg-[#d6ad60]/5"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Zap
              className={`h-3.5 w-3.5 ${
                pumpWarning === "alert"
                  ? "text-red-500"
                  : "text-[#d6ad60]"
              }`}
            />

            <span
              className={`text-[10px] font-bold ${
                pumpWarning === "alert"
                  ? "text-red-500"
                  : "text-[#d6ad60]"
              }`}
            >
              {pumpType === "pump" &&
                `حرکت صعودی غیرعادی (${pumpScore}/100)`}

              {pumpType === "dump" &&
                `حرکت نزولی غیرعادی (${dumpScore}/100)`}

              {pumpType === "both" &&
                `نوسان شدید (صعودی ${pumpScore}، نزولی ${dumpScore})`}
            </span>
          </div>

          <p className="mt-1 text-[9px] text-foreground/70">
            {pumpType === "pump" &&
              "حرکت صعودی غیرعادی شناسایی شده — مراقب ورود هیجانی و احتمال اصلاح باش."}

            {pumpType === "dump" &&
              "حرکت نزولی غیرعادی شناسایی شده — مراقب نوسان و احتمال برگشت قیمت باش."}

            {pumpType === "both" &&
              "نوسان دوطرفه شدید شناسایی شده — با احتیاط بیشتری تصمیم بگیر."}
          </p>
        </div>
      )}

      {/* هشدار تله‌ها */}
      {activeTraps.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-2.5">
          <p className="text-[10px] font-bold text-red-500/90 mb-1.5 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {activeTraps.length} تله فعال
          </p>

          <div className="space-y-1.5">
            {activeTraps.map((k) => {
              const trap = traps[k] as {
                active?: boolean;
                reason?: string;
                severity?: number;
              };

              return (
                <div
                  key={k}
                  className="rounded-md border border-red-500/10 bg-red-500/5 px-2 py-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-red-500/90">
                      {TRAP_LABELS[k] || k}
                    </span>

                    <span className="num text-[8px] text-muted-foreground">
                      شدت {trap.severity ?? 0}/10
                    </span>
                  </div>

                  <p className="mt-0.5 text-[9px] leading-relaxed text-foreground/70">
                    {trap.reason}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* تحلیل روایی - استراتژی */}
      <div className="rounded-lg border border-[#d6ad60]/20 bg-[#d6ad60]/5 px-2.5 py-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-[12px]">{strategyMeta.icon}</span>

          <span className="text-[10px] font-bold text-[#d6ad60]">
            استراتژی: {strategyMeta.fa}
          </span>
        </div>

        <p className="text-[9px] text-muted-foreground mt-0.5">
          {strategyMeta.why}
        </p>
      </div>

      {/* عنوان */}
      <div className="rounded-lg bg-white/5 border border-white/10 px-3 py-2">
        <p className="text-[11px] font-bold text-foreground/90 leading-relaxed">
          {narrative.headline}
        </p>
      </div>

      {/* چرا؟ */}
      <div className="rounded-lg border border-[#d6ad60]/20 bg-[#d6ad60]/5 px-2.5 py-2">
        <p className="text-[9px] font-bold text-[#d6ad60] mb-1 flex items-center gap-1">
          <Lightbulb className="h-3 w-3" />
          چرا این سیگنال؟
        </p>

        <p className="text-[10.5px] leading-[1.8] text-foreground/85 whitespace-pre-line">
          {narrative.why}
        </p>
      </div>

      {/* چیکار کنم؟ */}
      <div
        className={`rounded-lg border px-2.5 py-2 ${
          actionIsPositive
            ? "border-green-500/20 bg-green-500/5"
            : actionIsNegative
            ? "border-[#d6ad60]/20 bg-[#d6ad60]/5"
            : "border-[#d6ad60]/20 bg-[#d6ad60]/5"
        }`}
      >
        <p className="text-[9px] font-bold text-foreground/80 mb-1">
          🎯 الان چیکار کنم؟
        </p>

        <p className="text-[10.5px] leading-[1.8] text-foreground/85 whitespace-pre-line">
          {narrative.action}
        </p>
      </div>

      {/* سناریوها */}
      {scenarios.length > 0 && (
        <div>
          <p className="text-[10px] font-bold text-muted-foreground mb-1 flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            سناریوهای پیش‌رو ({scenarios.length})
          </p>

          <div className="space-y-2">
            {scenarios.map((sc, i) => (
              <ScenarioCard
                key={i}
                scenario={sc}
                mainDirection={mainDirection}
              />
            ))}
          </div>
        </div>
      )}

      {/* هشدار نهایی */}
      <div className="rounded-lg border border-[#d6ad60]/10 bg-[#d6ad60]/5 px-2.5 py-2 text-[9px] text-[#d6ad60]/80 leading-relaxed">
        ⚠️ این تحلیل بر اساس دیتای فعلی هست. بازار ممکنه متفاوت عمل کنه.
        همیشه با حد ضرر و مدیریت سرمایه وارد شو.
      </div>
    </div>
  );
}
