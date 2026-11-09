"use client";

/**
 * DeepAnalysis — تحلیل روایی (نسخه ۷.۰ · فاز ۱۴.۸.۲)
 * ============================================================
 * 🔴 تغییرات نسخه ۷.۰:
 *   • حذف جدول گروه‌ها (در چک‌لیست هست)
 *   • روایت انسانی: «چرا این سیگنال؟»
 *   • بخش «چه اتفاقی افتاده؟» + «چی کار کنم؟»
 *   • دلیل‌ها با زبان ساده
 */

import { useEffect, useState } from "react";
import {
  Check,
  AlertTriangle,
  GitBranch,
  Target,
  Sparkles,
  Info,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  MessageCircle,
  Lightbulb,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AccordionSection } from "@/components/ui/accordion-section";
import { useAppStore } from "@/store/useAppStore";
import { useSignalData } from "@/hooks/useSignalData";

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return isMobile;
}

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

// ═══════════════════════════════════════════════════════════
// 🔴 روایت‌سازی: چرا این سیگنال؟
// ═══════════════════════════════════════════════════════════
function buildNarrative(data: any): {
  headline: string;
  why: string;
  action: string;
} {
  const signal = data.signal || "";
  const conf = data.confidence || 0;
  const direction = data.direction || "neutral";
  const strategy = data.strategy || "swing";
  const strategyMeta = STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;
  const isLong = signal.includes("LONG");
  const isShort = signal.includes("SHORT");
  const isWeak = signal.includes("ضعیف");
  const isForming = signal.includes("در حال تشکیل");
  const isFar = signal.includes("دور");
  const isNeutral = signal.includes("خنثی");

  // ═══ headline (عنوان) ═══
  let headline = "";
  if (isLong) {
    headline = isWeak
      ? `🟡 خرید ضعیف — بهتره با احتیاط وارد شی`
      : conf >= 70
      ? `✅ خرید قوی — شرایط مساعدِ`
      : `🟢 سیگنال خرید — شرایط مناسبه`;
  } else if (isShort) {
    headline = isWeak
      ? `🟠 فروش ضعیف — پرریسکه، با احتیاط`
      : conf >= 70
      ? `🔴 فروش قوی — شرایط مساعدِ`
      : `🔴 سیگنال فروش — شرایط مناسبه`;
  } else if (isForming) {
    headline = `⏳ در حال تشکیل — هنوز سیگنال کامل نشده`;
  } else if (isFar) {
    headline = `⚪ دور از ورود — فعلاً صبر کن`;
  } else {
    headline = `⚪ بدون سیگنال — بهترین کار، صبر کردنه`;
  }

  // ═══ why (چرا؟) ═══
  const reasons = data.reasons || [];
  const topReasons = reasons.slice(0, 3).filter((r: string) => r);
  let why = "";

  if (isLong || isShort) {
    const dirFa = isLong ? "صعودی" : "نزولی";
    const strengths = reasons
      .filter((r: string) => !r.includes("⚠️") && !r.includes("🚫"))
      .slice(0, 2)
      .map((r: string) => r.replace(/[🟢🟡🟠🔴⚡✅💧📈📊🏗💎]/g, "").trim())
      .filter((r: string) => r.length > 5);

    if (strengths.length > 0) {
      why = `چند دلیل برای ${dirFa} بودن بازار داریم:\n${strengths
        .map((s: string) => `• ${s}`)
        .join("\n")}`;
    } else {
      why = `گروه‌های تحلیل به ${dirFa} بودن بازار رأی دادن. اطمینان ${conf}٪.`;
    }
  } else if (isForming) {
    why = `شرایط داره آماده می‌شه، ولی هنوز به آستانه‌ی سیگنال معامله‌ای نرسیده.\n• اطمینان فعلی: ${conf}٪\n• استراتژی ${strategyMeta.fa} نیاز به اطمینان بالاتری داره\n• چند دقیقه صبر کن، شاید کامل بشه`;
  } else if (isFar) {
    why = `بازار هنوز سیگنال معتبری نمی‌ده.\n• گروه‌ها هم‌جهت نیستن\n• حرکت واضحی شکل نگرفته\n• صبر کن تا شرایط روشن‌تر بشه`;
  } else {
    why = `بازار در رژیم رنج یا بی‌جهته.\n• گروه‌های تحلیل هم‌جهت نیستن\n• اندیکاتورها علامت واضحی نمی‌دن\n• صبر، بهترین استراتژی در این شرایطه`;
  }

  // ═══ action (چیکار کنم؟) ═══
  let action = "";
  if (isLong && conf >= 70) {
    action = `✅ می‌تونی وارد شی — ولی مدیریت سرمایه یادت نره (حداکثر ۲-۳٪).\n💡 حتماً حد ضرر بذار.`;
  } else if (isLong && isWeak) {
    action = `🟡 با احتیاط وارد شو — فقط ۰.۵-۱٪ سرمایه.\n💡 حرکت ضعیفه، TP رو نزدیک‌تر بذار.`;
  } else if (isShort && conf >= 70) {
    action = `✅ SHORT منطقیه — ولی حد ضرر تنگ بذار.\n💡 نوسان ممکنه بالا باشه، مراقب باش.`;
  } else if (isShort && isWeak) {
    action = `🟠 با احتیاط SHORT بزن — فقط با حجم کم.\n💡 ریسک بالاست، حد ضرر نزدیک بذار.`;
  } else if (isForming) {
    action = `⏳ صبر کن — سیگنال در حال کامله.\n💡 چند دقیقه دیگه چک کن یا TF رو عوض کن.`;
  } else {
    action = `⏸ وارد نشو — بهترین معامله، معامله‌ای هست که انجام نشه.\n💡 صبر کن تا سیگنال واضح بیاد.`;
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
    green: "border-green-500/30 bg-green-500/5 text-green-400",
    red: "border-red-500/30 bg-red-500/5 text-red-400",
    yellow: "border-yellow-500/30 bg-yellow-500/5 text-yellow-400",
  };
  const color = scenario.color || "yellow";
  const probability = Math.round((scenario.probability || 0.5) * 100);
  const condition = scenario.condition || "";
  const action = scenario.action || "";

  const isLongScenario = action.includes("LONG") || action.includes("خرید");
  const isShortScenario = action.includes("SHORT") || action.includes("فروش");
  const isConflict =
    (mainDirection === "short" && isLongScenario) ||
    (mainDirection === "long" && isShortScenario);

  return (
    <div
      className={`rounded-lg border p-2.5 ${
        colorMap[color] || colorMap.yellow
      } transition-all hover:bg-white/10 relative`}
    >
      {isConflict && (
        <div className="absolute -top-2 -left-2 rounded bg-orange-600 text-[8px] font-bold text-white px-1.5 py-0.5 shadow-sm">
          ⚠️ خلاف جهت
        </div>
      )}
      <div className="flex items-start gap-2">
        <span className="text-[16px] mt-0.5">{scenario.icon || "•"}</span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="text-[11px] font-medium leading-relaxed text-foreground/90">
            {condition}
          </p>
          <p className="text-[10.5px] leading-relaxed text-foreground/75">
            ↪ {action}
          </p>
          <div className="flex items-center gap-2 pt-1">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/30">
              <div
                className="h-full rounded-full bg-current opacity-80"
                style={{ width: `${probability}%` }}
              />
            </div>
            <span className="num shrink-0 text-[9.5px] font-bold text-muted-foreground">
              {probability}٪
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function DeepAnalysis() {
  const { timeframe, strategy } = useAppStore();
  const { data, loading } = useSignalData();
  const [copied, setCopied] = useState(false);
  const isMobile = useIsMobile();

  const aiExport = data?.ai_export || "";
  const pumpScore = data?.pump_score || 0;
  const dumpScore = data?.dump_score || 0;
  const pumpWarning = data?.pump_warning || "none";
  const pumpType = data?.pump_type || "none";

  const handleCopy = async () => {
    if (!aiExport) return;
    try {
      await navigator.clipboard.writeText(aiExport);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error(e);
    }
  };

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
  const defaultOpenDesktop = !isMobile;
  const strategyMeta = STRATEGY_LABELS[strategy] || STRATEGY_LABELS.swing;
  const narrative = buildNarrative(data);

  return (
    <div className="space-y-2.5">
      {/* ۱. هشدار Pump/Dump */}
      {pumpWarning !== "none" && (
        <div
          className={`rounded-lg border px-2.5 py-2 ${
            pumpWarning === "alert"
              ? "border-red-500/40 bg-red-500/10"
              : "border-amber-500/40 bg-amber-500/10"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Zap
              className={`h-3.5 w-3.5 ${
                pumpWarning === "alert" ? "text-red-500" : "text-amber-500"
              }`}
            />
            <span
              className={`text-[10px] font-bold ${
                pumpWarning === "alert" ? "text-red-500" : "text-amber-500"
              }`}
            >
              {pumpType === "pump" && `⚠️ پامپ شناسایی شد (${pumpScore}/100)`}
              {pumpType === "dump" && `⚠️ دامپ شناسایی شد (${dumpScore}/100)`}
              {pumpType === "both" &&
                `⚠️ نوسان شدید (pump=${pumpScore}, dump=${dumpScore})`}
            </span>
          </div>
          <p className="mt-1 text-[9px] text-foreground/70">
            {pumpType === "pump" && "حرکت صعودی غیرعادی — احتمال اصلاح"}
            {pumpType === "dump" && "حرکت نزولی غیرعادی — احتمال برگشت"}
            {pumpType === "both" && "نوسان دوطرفه شدید — احتیاط"}
          </p>
        </div>
      )}

      {/* ۲. هشدار تله‌ها */}
      {activeTraps.length > 0 && (
        <AccordionSection
          title="⚠️ هشدار تله"
          icon={<AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
          preview={`${activeTraps.length} تله فعال`}
          tone="orange"
          pulse
          defaultOpen={defaultOpenDesktop}
        >
          <div className="space-y-2">
            {activeTraps.map((k) => {
              const trap = traps[k] as {
                active?: boolean;
                reason?: string;
                severity?: number;
              };
              return (
                <div
                  key={k}
                  className="rounded-lg border border-red-500/30 bg-red-500/5 px-2.5 py-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-red-500">
                      🚨 {TRAP_LABELS[k] || k}
                    </span>
                    <span className="num text-[9px] text-muted-foreground">
                      شدت {trap.severity || 0}/10
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] leading-relaxed text-foreground/70">
                    {trap.reason}
                  </p>
                </div>
              );
            })}
          </div>
        </AccordionSection>
      )}

      {/* ۳. 🔴 تحلیل روایی */}
      <AccordionSection
        title="💬 تحلیل و چرایی"
        icon={<MessageCircle className="h-3.5 w-3.5" />}
        preview={narrative.headline}
        tone="primary"
        pulse
        defaultOpen={defaultOpenDesktop}
      >
        <div className="space-y-2.5">
          {/* استراتژی فعال */}
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
          <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-2.5 py-2">
            <p className="text-[9px] font-bold text-blue-400 mb-1 flex items-center gap-1">
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
              narrative.action.includes("✅")
                ? "border-green-500/30 bg-green-500/5"
                : narrative.action.includes("⏸") ||
                  narrative.action.includes("⏳")
                ? "border-amber-500/30 bg-amber-500/5"
                : "border-orange-500/30 bg-orange-500/5"
            }`}
          >
            <p className="text-[9px] font-bold text-foreground/80 mb-1">
              🎯 الان چیکار کنم؟
            </p>
            <p className="text-[10.5px] leading-[1.8] text-foreground/85 whitespace-pre-line">
              {narrative.action}
            </p>
          </div>
        </div>
      </AccordionSection>

      {/* ۴. سناریوها */}
      {scenarios.length > 0 && (
        <AccordionSection
          title="🔀 سناریوهای پیش‌رو"
          icon={<GitBranch className="h-3.5 w-3.5" />}
          preview={`${scenarios.length} سناریو`}
          tone="primary"
          pulse
          defaultOpen={defaultOpenDesktop}
        >
          <div className="space-y-2">
            {scenarios.map((sc, i) => (
              <ScenarioCard
                key={i}
                scenario={sc}
                mainDirection={mainDirection}
              />
            ))}
          </div>
        </AccordionSection>
      )}

      {/* ۵. هشدار نهایی */}
      <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-2.5 py-2 text-[9px] text-yellow-500/80 leading-relaxed">
        ⚠️ این تحلیل بر اساس دیتای فعلی هست. بازار ممکنه متفاوت عمل کنه.
        همیشه با حد ضرر و مدیریت سرمایه وارد شو.
      </div>

      {/* ۶. دکمه کپی */}
      <Button
        onClick={handleCopy}
        variant="default"
        className={`w-full ${
          copied ? "bg-green-600 hover:bg-green-700 text-white" : ""
        }`}
        size="sm"
        disabled={!aiExport}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" /> کپی شد
          </>
        ) : (
          <>
            <Sparkles className="h-3.5 w-3.5" /> کپی داده‌های خام برای AI
          </>
        )}
      </Button>
    </div>
  );
}