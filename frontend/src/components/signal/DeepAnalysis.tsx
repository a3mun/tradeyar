"use client";

/**
 * DeepAnalysis — تحلیل عمیق (نسخه ۷.۱ · فاز ۱۰.۵)
 * ============================================================
 * 🔴 تغییرات:
 *   • عنوان «تحلیل عمیق سیگنال»
 *   • دکمه «کپی همه داده‌های خام برای AI»
 *   • ContentBlock جدید با جداسازی بصری موضوعات
 *   • تیترها مشکی (نه آبی) — هم‌خون با متن
 *   • پاراگراف‌بندی بهتر
 */

import { useState } from "react";
import { Copy, Check, BarChart3, Compass, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AccordionSection } from "@/components/ui/accordion-section";
import { useAppStore } from "@/store/useAppStore";
import { useSignalData } from "@/hooks/useSignalData";

function splitSections(raw: string) {
  if (!raw) return { tech: "", fund: "", concl: "" };
  const fundMarker = "◈ زمینه‌ی بنیادی";
  const conclMarker = "◈ جمع‌بندی صادقانه";
  const fundIdx = raw.indexOf(fundMarker);
  const conclIdx = raw.indexOf(conclMarker);
  let tech = raw;
  let fund = "";
  let concl = "";
  if (fundIdx !== -1) {
    tech = raw.slice(0, fundIdx).trim();
    const rest = raw.slice(fundIdx);
    if (conclIdx !== -1) {
      const relConcl = conclIdx - fundIdx;
      fund = rest.slice(0, relConcl).trim();
      concl = rest.slice(relConcl).trim();
    } else {
      fund = rest.trim();
    }
  } else if (conclIdx !== -1) {
    tech = raw.slice(0, conclIdx).trim();
    concl = raw.slice(conclIdx).trim();
  }
  return { tech, fund, concl };
}

function previewLine(text: string, max = 80): string {
  if (!text) return "";
  const cleaned = text
    .replace(/[─◈📊🧭🎯▎▲▼●🚀📉🔥]/g, "")
    .replace(/\*\*/g, "")
    .replace(/\n+/g, " ")
    .trim();
  return cleaned.slice(0, max);
}

/**
 * ContentBlock — نمایش متن تحلیل با جداسازی بصری موضوعات
 *
 * ═══ قواعد ═══
 *   • خطی که با «▎» شروع میشه → تیتر اصلی + نوار آبی سمت راست
 *   • خطی که با «**..**» احاطه شده → زیرتیتر
 *   • خط معمولی → متن عادی
 */
function ContentBlock({ text }: { text: string }) {
  if (!text) return null;

  const lines = text
    .replace(/─{3,}/g, "")
    .split("\n")
    .map((l) => l.replace(/\s+$/, ""))
    .filter((l) => l.trim().length > 0);

  type Block =
    | { type: "title"; content: string }
    | { type: "subtitle"; content: string }
    | { type: "text"; content: string[] };

  const blocks: Block[] = [];
  let currentText: string[] = [];

  const flushText = () => {
    if (currentText.length > 0) {
      blocks.push({ type: "text", content: [...currentText] });
      currentText = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // ─── تیتر اصلی: ▎ ───
    const isMainTitle = line.startsWith("▎");

    if (isMainTitle) {
      flushText();
      const title = line
        .replace(/^▎/, "")
        .replace(/\*\*/g, "")
        .trim();
      blocks.push({ type: "title", content: title });
      continue;
    }

    // ─── زیرتیتر: **...** ───
    const isSubTitle = /^\*\*[^*]+\*\*$/.test(line) && line.length < 50;

    if (isSubTitle) {
      flushText();
      const subtitle = line.replace(/\*\*/g, "").trim();
      blocks.push({ type: "subtitle", content: subtitle });
      continue;
    }

    // ─── متن معمولی ───
    currentText.push(rawLine.trimEnd());
  }
  flushText();

  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        // ═══ تیتر اصلی ═══
        if (block.type === "title") {
          return (
            <div key={i} className="pt-1 first:pt-0">
              <div className="mb-1.5 flex items-center gap-2">
                <div className="h-3.5 w-1 rounded-full bg-primary" />
                <h4 className="text-[12px] font-bold text-foreground">
                  {block.content}
                </h4>
              </div>
            </div>
          );
        }

        // ═══ زیرتیتر ═══
        if (block.type === "subtitle") {
          return (
            <div key={i} className="pt-0.5">
              <h5 className="text-[11px] font-bold text-foreground/80">
                {block.content}
              </h5>
            </div>
          );
        }

        // ═══ متن ═══
        return (
          <p
            key={i}
            className="whitespace-pre-wrap break-words text-[11px] leading-[1.7] text-foreground/85"
          >
            {block.content.join("\n")}
          </p>
        );
      })}
    </div>
  );
}

export function DeepAnalysis() {
  const { timeframe } = useAppStore();
  const { data, loading } = useSignalData();

  const text =
    (data as { deep_analysis?: string } | null)?.deep_analysis || "";
  const aiExport = data?.ai_export || "";

  const [copied, setCopied] = useState(false);

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

  const { tech, fund, concl } = splitSections(text);

  if (loading && !text) {
    return (
      <div className="space-y-2 rounded-lg border border-border/40 bg-card/30 p-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  if (!text) {
    return (
      <p className="py-4 text-center text-xs text-muted-foreground">
        ⏳ تحلیل برای {timeframe} در دسترس نیست
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {/* ═══ بخش ۱: تحلیل عمیق سیگنال ═══ */}
      <AccordionSection
        title="تحلیل عمیق سیگنال"
        icon={<BarChart3 className="h-3.5 w-3.5" />}
        preview={previewLine(tech)}
        tone="primary"
        pulse
      >
        <ContentBlock text={tech} />
      </AccordionSection>

      {/* ═══ بخش ۲: تحلیل بنیادی ═══ */}
      {fund && (
        <AccordionSection
          title="تحلیل بنیادی"
          icon={<Compass className="h-3.5 w-3.5" />}
          preview={previewLine(fund)}
          tone="default"
          pulse
        >
          <ContentBlock text={fund.replace("◈ زمینه‌ی بنیادی", "")} />
        </AccordionSection>
      )}

      {/* ═══ بخش ۳: جمع‌بندی ═══ */}
      {concl && (
        <AccordionSection
          title="جمع‌بندی — چیکار کنم؟"
          icon={<Target className="h-3.5 w-3.5" />}
          preview={previewLine(concl)}
          tone="orange"
          pulse
          defaultOpen
        >
          <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-3">
            <ContentBlock text={concl.replace("◈ جمع‌بندی صادقانه", "")} />
          </div>
        </AccordionSection>
      )}

      {/* ═══ دکمه کپی ═══ */}
      <Button
        onClick={handleCopy}
        variant={copied ? "default" : "secondary"}
        className={`w-full ${copied ? "bg-green-600 hover:bg-green-700" : ""}`}
        size="sm"
        disabled={!aiExport}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" /> کپی شد
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" /> کپی همه داده‌های خام برای AI
          </>
        )}
      </Button>
    </div>
  );
}