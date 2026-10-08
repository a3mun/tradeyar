"use client";

/**
 * DeepAnalysis — تحلیل عمیق (نسخه ۴.۰)
 * ============================================================
 * 🔴 تغییرات:
 *   • استفاده از CollapsibleCard (ساده‌تر)
 *   • موبایل: پیش‌فرض بسته + خلاصه یک‌خطی
 *   • دسکتاپ: همیشه باز
 */

import { useState } from "react";
import { Copy, Check, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { useAppStore } from "@/store/useAppStore";
import { useSignalData } from "@/hooks/useSignalData";
import { SOURCE_BY_KEY } from "@/lib/sources";

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

function extractSummary(concl: string): string {
  if (!concl) return "";
  const cleaned = concl
    .replace("◈ جمع‌بندی صادقانه", "")
    .replace(/─+/g, "")
    .trim();
  const lines = cleaned.split("\n").filter((l) => l.trim());
  return lines[0]?.slice(0, 80) || "";
}

export function DeepAnalysis() {
  const { source, timeframe } = useAppStore();
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
  const meta = SOURCE_BY_KEY[source];
  const srcLabel = meta ? `${meta.icon} ${meta.label}` : source;
  const summary = extractSummary(concl);

  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <Brain className="h-3.5 w-3.5" />
          تحلیل عمیق
        </span>
      }
      pulse
      keepCollapsibleOnDesktop
      forceOpenOnDesktop
    >
      <div className="space-y-3">
        {loading && !text ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : text ? (
          <>
            {/* تکنیکال */}
            <section className="space-y-2">
              <h3 className="flex items-center gap-2 border-b border-border/50 pb-1.5 text-xs font-bold">
                <span>📊</span>
                تحلیل تکنیکال
              </h3>
              <div className="rounded-lg bg-muted/30 p-3">
                <pre className="whitespace-pre-wrap break-words font-sans text-[11px] leading-relaxed text-foreground">
                  {tech}
                </pre>
              </div>
            </section>

            {/* بنیادی */}
            {fund && (
              <section className="space-y-2">
                <h3 className="flex items-center gap-2 border-b border-border/50 pb-1.5 text-xs font-bold">
                  <span>🧭</span>
                  تحلیل بنیادی
                </h3>
                <div className="rounded-lg bg-muted/30 p-3">
                  <pre className="whitespace-pre-wrap break-words font-sans text-[11px] leading-relaxed text-foreground">
                    {fund.replace(
                      "◈ زمینه‌ی بنیادی و ساختاری\n" + "─".repeat(30) + "\n",
                      ""
                    )}
                  </pre>
                </div>
              </section>
            )}

            {/* نتیجه‌گیری */}
            {concl && (
              <section className="space-y-2">
                <h3 className="flex items-center gap-2 border-b border-primary/30 pb-1.5 text-xs font-bold text-primary">
                  <span>🎯</span>
                  نتیجه‌گیری — چیکار کنم؟
                </h3>
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-3">
                  <pre className="whitespace-pre-wrap break-words font-sans text-[11px] font-medium leading-relaxed text-foreground">
                    {concl.replace(
                      "◈ جمع‌بندی صادقانه\n" + "─".repeat(30) + "\n",
                      ""
                    )}
                  </pre>
                </div>
              </section>
            )}
          </>
        ) : (
          <p className="py-4 text-center text-xs text-muted-foreground">
            ⏳ تحلیل برای {timeframe} در دسترس نیست
          </p>
        )}

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
              <Copy className="h-3.5 w-3.5" /> کپی داده‌ها برای AI
            </>
          )}
        </Button>
      </div>
    </CollapsibleCard>
  );
}