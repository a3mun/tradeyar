"use client";

/**
 * DeepAnalysis — تحلیل عمیق (نسخه ۱۰.۲ · فاز ۱۲.۶)
 * ============================================================
 * 🔴 تغییرات نسخه ۱۰.۲:
 *   • دکمه کپی هم‌رنگ با دکمه‌های اصلی سایت (زرد/طلایی ملایم)
 *   • توضیحات سناریوها شیوا و دوستانه‌تر
 */

import { useEffect, useState } from "react";
import {
  Check,
  BarChart3,
  AlertTriangle,
  GitBranch,
  Target,
  Sparkles,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AccordionSection } from "@/components/ui/accordion-section";
import { useAppStore } from "@/store/useAppStore";
import { useSignalData } from "@/hooks/useSignalData";

// ═══════════════════════════════════════════════════════════
// تشخیص موبایل
// ═══════════════════════════════════════════════════════════
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

// ═══════════════════════════════════════════════════════════
// 🎯 ترجمه‌ی explanation به زبان دوستانه
// ═══════════════════════════════════════════════════════════
function friendlyExplanation(explanation: string, signal: string): string {
  if (!explanation) return "";

  let text = explanation.replace(/—/g, "،").trim();

  const isLong = signal.includes("LONG");
  const isShort = signal.includes("SHORT");
  const isWeak = signal.includes("ضعیف");

  if (isLong && isWeak) {
    text +=
      "\n\n💡 سیگنال ضعیفه — با احتیاط. حد ضرر رو حتماً تنظیم کن، شاید بهتره صبر کنی.";
  } else if (isLong) {
    text +=
      "\n\n💡 می‌تونی وارد شی، ولی با مدیریت سرمایه. حتماً حد ضرر بذار.";
  } else if (isShort && isWeak) {
    text +=
      "\n\n💡 SHORT ضعیف — پرریسکه. اگه وارد شی، سریع خارج شو.";
  } else if (isShort) {
    text +=
      "\n\n💡 SHORT منطقیه، ولی حد ضرر رو تنگ بذار. نوسان می‌تونه سریع برگرده.";
  } else {
    text += "\n\n💡 الان بازار سیگنال واضحی نداره. صبر کن.";
  }

  return text;
}

// ═══════════════════════════════════════════════════════════
// 🎯 روان‌سازی متن سناریوها (شیوا و مشاوره‌محور)
// ═══════════════════════════════════════════════════════════
function friendlyScenario(action: string, condition: string): string {
  let text = action;

  // جایگزینی عبارات خشک با جملات روان‌تر
  text = text.replace(/SL زیر حمایت/g, "حد ضرر رو کمی زیر این سطح بذار");
  text = text.replace(/SL تنگ بذار/g, "حد ضرر نزدیک بذار");
  text = text.replace(/ورود LONG — SL=/g, "ورود LONG — حد ضرر=");
  text = text.replace(/SL=/g, "حد ضرر=");
  text = text.replace(/TP=/g, "حد سود=");
  text = text.replace(/R \(/g, "مقاومت (");
  text = text.replace(/حمایت \(/g, "حمایت (");
  text = text.replace(/مقاومت \(/g, "مقاومت (");
  text = text.replace(/مراقب باش/g, "حواسات باشه، شاید بازار برگرده");

  // برای سناریوهای برخورد به حمایت/مقاومت
  if (condition.includes("حمایت")) {
    text = text.replace(
      /فرصت خرید/g,
      "فرصت خرید خوبه، ولی صبر کن ببینی خریدارها میان یا نه"
    );
  }
  if (condition.includes("مقاومت")) {
    text = text.replace(
      /مراقب باش/g,
      "این سطح مقاومته — اگه رد نشه، ممکنه برگرده پایین"
    );
  }

  return text;
}

// ═══════════════════════════════════════════════════════════
// تجزیه‌کننده متن — فقط بخش‌های ارزشمند
// ═══════════════════════════════════════════════════════════
function extractValuableSections(raw: string): string {
  if (!raw) return "";

  const lines = raw.split("\n");
  const keep: string[] = [];
  let currentSection = "";

  for (const line of lines) {
    const trimmed = line.trim();

    if (
      trimmed.includes("نظر گروه‌ها") ||
      trimmed.includes("سطوح کلیدی") ||
      trimmed.includes("عمق بازار") ||
      trimmed.includes("سناریوهای پیش‌رو")
    ) {
      currentSection = "skip";
      continue;
    }

    if (
      trimmed.includes("بازار چطوره") ||
      trimmed.includes("چرا این سیگنال") ||
      trimmed.includes("جمع‌بندی")
    ) {
      currentSection = "keep";
      continue;
    }

    if (trimmed.match(/^[─▎◈]{2,}/) || trimmed.match(/^[|]/)) {
      if (currentSection === "keep") keep.push("");
      continue;
    }

    if (currentSection === "keep" && trimmed) {
      const clean = trimmed
        .replace(/^[▎◈]\s*/, "")
        .replace(/\*\*/g, "")
        .replace(/^[•·]\s*/, "• ");
      keep.push(clean);
    }
  }

  return keep.join("\n");
}

// ═══════════════════════════════════════════════════════════
// ParagraphBlock — متن روان‌تر
// ═══════════════════════════════════════════════════════════
function ParagraphBlock({ text }: { text: string }) {
  if (!text.trim()) return null;

  const paragraphs = text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  return (
    <div className="space-y-2">
      {paragraphs.map((p, i) => {
        const lines = p.split("\n").filter((l) => l.trim());

        if (lines.every((l) => l.startsWith("•"))) {
          return (
            <ul
              key={i}
              className="space-y-1 rounded-md bg-muted/20 px-3 py-2"
            >
              {lines.map((l, j) => (
                <li
                  key={j}
                  className="text-[11px] leading-relaxed text-foreground/80"
                >
                  {l}
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p
            key={i}
            className="rounded-md bg-muted/15 px-3 py-2 text-[11px] leading-[1.9] text-foreground/80"
          >
            {lines.join(" ")}
          </p>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// ScenarioCard
// ═══════════════════════════════════════════════════════════
function ScenarioCard({
  scenario,
}: {
  scenario: {
    icon?: string;
    condition?: string;
    action?: string;
    probability?: number;
    color?: string;
  };
}) {
  const colorMap: Record<string, string> = {
    green: "border-green-500/30 bg-green-500/5",
    red: "border-red-500/30 bg-red-500/5",
    yellow: "border-yellow-500/30 bg-yellow-500/5",
  };
  const color = scenario.color || "yellow";
  const probability = Math.round((scenario.probability || 0.5) * 100);
  const condition = scenario.condition || "";
  const action = scenario.action || "";
  
  const friendlyAction = friendlyScenario(action, condition);

  return (
    <div
      className={`rounded-md border px-2.5 py-2.5 ${colorMap[color] || colorMap.yellow}`}
    >
      <div className="flex items-start gap-2">
        <span className="text-[14px] mt-0.5">{scenario.icon || "•"}</span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="text-[11px] font-medium leading-relaxed text-foreground/90">
            {condition}
          </p>
          <p className="text-[10.5px] leading-relaxed text-foreground/75">
            ↪ {friendlyAction}
          </p>
        </div>
        <span className="num shrink-0 text-[9.5px] font-bold text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">
          {probability}٪
        </span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// DeepAnalysis اصلی
// ═══════════════════════════════════════════════════════════
export function DeepAnalysis() {
  const { timeframe } = useAppStore();
  const { data, loading } = useSignalData();
  const [copied, setCopied] = useState(false);
  const isMobile = useIsMobile();

  const aiExport = data?.ai_export || "";
  const techText =
    (data as { deep_analysis?: string } | null)?.deep_analysis || "";
  const valuableText = extractValuableSections(techText);

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
      <div className="space-y-2 rounded-lg border border-border/40 bg-card/30 p-3">
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
  const explanation = data.explanation || "";
  const neutralExplain =
    (data as { neutral_explain?: { long?: string; hint?: string } })
      .neutral_explain || null;

  // 🔴 دسکتاپ باز، موبایل بسته
  const defaultOpenDesktop = !isMobile;

  return (
    <div className="space-y-2.5">
      {/* ═══ هشدارها ═══ */}
      {activeTraps.length > 0 && (
        <AccordionSection
          title="⚠️ هشدار — قبل از ورود بخون"
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
                  className="rounded-md border border-red-500/30 bg-red-500/5 px-2.5 py-2"
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

      {/* ═══ تحلیل عمیق ═══ */}
      {valuableText && (
        <AccordionSection
          title="تحلیل عمیق"
          icon={<BarChart3 className="h-3.5 w-3.5" />}
          preview="چرا این سیگنال — به زبان ساده"
          tone="primary"
          pulse
          defaultOpen={defaultOpenDesktop}
        >
          <ParagraphBlock text={valuableText} />
        </AccordionSection>
      )}

      {/* ═══ سناریوها ═══ */}
      {scenarios.length > 0 && (
        <AccordionSection
          title="سناریوهای پیش‌رو"
          icon={<GitBranch className="h-3.5 w-3.5" />}
          preview={`${scenarios.length} سناریو با احتمال`}
          tone="primary"
          pulse
          defaultOpen={defaultOpenDesktop}
        >
          <div className="space-y-2">
            {scenarios.map((sc, i) => (
              <ScenarioCard key={i} scenario={sc} />
            ))}
          </div>
        </AccordionSection>
      )}

      {/* ═══ جمع‌بندی ═══ */}
      {(explanation || neutralExplain) && (
        <AccordionSection
          title="جمع‌بندی — چیکار کنم؟"
          icon={<Target className="h-3.5 w-3.5" />}
          preview={explanation || neutralExplain?.long || "توصیه نهایی"}
          tone="orange"
          pulse
          defaultOpen={defaultOpenDesktop}
        >
          <div className="space-y-2">
            {explanation && (
              <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 px-3 py-2.5">
                <div className="flex items-start gap-2">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-500" />
                  <div className="flex-1">
                    <p className="text-[11px] leading-[1.8] text-foreground/85 whitespace-pre-wrap">
                      {friendlyExplanation(explanation, data.signal || "")}
                    </p>
                  </div>
                </div>
              </div>
            )}
            {neutralExplain?.long && (
              <div className="rounded-md bg-muted/20 px-2.5 py-2 text-[10px] leading-relaxed text-foreground/70">
                {neutralExplain.long}
              </div>
            )}
            {neutralExplain?.hint && (
              <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-2.5 py-2 text-[10px] leading-relaxed text-blue-400">
                💡 {neutralExplain.hint}
              </div>
            )}
            <div className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-2.5 py-2 text-[9px] text-yellow-500/80">
              ⚠️ این تحلیل بر اساس دیتای فعلی هست. بازار ممکنه متفاوت عمل کنه.
              همیشه با حد ضرر و مدیریت سرمایه وارد شو.
            </div>
          </div>
        </AccordionSection>
      )}

      {/* ═══ دکمه کپی — استفاده از تم دکمه اصلی سایت ═══ */}
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