"use client";

/**
 * DeepAnalysis — تحلیل عمیق + AI
 * ============================================================
 * نسخه ۲.۰ · فاز ۷
 *
 * 🔴 تغییرات نسخه ۲.۰:
 *   • حذف GET /analyze/deep (تکراری با WS signal)
 *   • حذف POST /analyze (تکراری با SignalDataProvider)
 *   • استفاده از useSignalData (منبع واحد حقیقت)
 *
 * ─── نتیجه ───
 *   ✅ صفر درخواست اضافه
 *   ✅ داده همیشه با SignalCard سازگار
 *   ✅ سرعت بالاتر
 *
 * ═══ بخش‌بندی متن ═══
 *   1. تکنیکال — از ابتدا تا marker «◈ زمینه‌ی بنیادی»
 *   2. بنیادی  — از marker تا marker «◈ جمع‌بندی صادقانه»
 *   3. نتیجه  — از marker تا آخر
 */

import { useEffect, useState } from "react";
import { Copy, Check, Brain, Sparkles, Loader2, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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

export function DeepAnalysis() {
  const { source, timeframe } = useAppStore();
  const { data, loading } = useSignalData();

  // ─── استخراج متن و ai_export از منبع واحد ───
  const text = (data as { deep_analysis?: string } | null)?.deep_analysis || "";
  const aiExport = data?.ai_export || "";

  const [copied, setCopied] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiError, setAiError] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("deepseek_api_key") || "";
    setApiKey(saved);
  }, []);

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

  const handleAiAnalyze = async () => {
    const key = apiKey || localStorage.getItem("deepseek_api_key") || "";
    if (!key) {
      setShowKeyInput(true);
      setAiError("اول کلید DeepSeek رو وارد کن");
      return;
    }
    if (!aiExport) {
      setAiError("داده‌ای برای ارسال نیست");
      return;
    }
    setAiLoading(true);
    setAiError("");
    setAiResult("");
    try {
      const res = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${key}`,
        },
        body: JSON.stringify({
          model: "deepseek-chat",
          messages: [
            {
              role: "system",
              content: `تو یه دوست معامله‌گر باتجربه هستی که به رفیقت مشاوره می‌دی.
قواعد:
- لحن خودمونی و صمیمی، ولی حرفه‌ای (نه خشک، نه بچه‌گانه)
- فارسی محاوره‌ای ساده، بدون اصطلاحات پیچیده
- حداکثر ۱۵۰ کلمه
- توصیه‌محور: آخرش یه جمله «الان چیکار کنم؟»
- اگه سیگنال ضعیفه، صریح بگو «الان نخر، صبر کن»
- اگه تله‌ای هست، هشدار بده
- از اعداد مشخص استفاده کن (قیمت، درصد)`,
            },
            { role: "user", content: aiExport },
          ],
          temperature: 0.7,
          max_tokens: 500,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error?.message || `HTTP ${res.status}`);
      }
      const resData = await res.json();
      setAiResult(resData.choices?.[0]?.message?.content || "پاسخی دریافت نشد");
    } catch (e: unknown) {
      setAiError((e as Error).message || "خطا در ارتباط با AI");
    } finally {
      setAiLoading(false);
    }
  };

  const handleSaveKey = () => {
    localStorage.setItem("deepseek_api_key", apiKey);
    setShowKeyInput(false);
    setAiError("");
  };

  const { tech, fund, concl } = splitSections(text);
  const meta = SOURCE_BY_KEY[source];
  const srcLabel = meta ? `${meta.icon} ${meta.label}` : source;
  const srcClass = meta?.badgeClass ?? "";

  return (
    <div className="space-y-3">
      {/* ═══ کارت تحلیل عمیق ═══ */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" />
            تحلیل عمیق
          </CardTitle>
          <Badge className={`text-[10px] border ${srcClass}`}>{srcLabel}</Badge>
        </CardHeader>

        <CardContent className="space-y-3">
          {loading && !text ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : text ? (
            <>
              {/* ═══ تکنیکال ═══ */}
              <section className="space-y-2">
                <h3 className="flex items-center gap-2 border-b border-border/50 pb-1.5 text-sm font-bold">
                  <span>📊</span>
                  تحلیل تکنیکال
                </h3>
                <div className="rounded-lg bg-muted/30 p-3">
                  <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-foreground">
                    {tech}
                  </pre>
                </div>
              </section>

              {/* ═══ بنیادی ═══ */}
              {fund && (
                <section className="space-y-2">
                  <h3 className="flex items-center gap-2 border-b border-border/50 pb-1.5 text-sm font-bold">
                    <span>🧭</span>
                    تحلیل بنیادی و ساختاری
                  </h3>
                  <div className="rounded-lg bg-muted/30 p-3">
                    <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-foreground">
                      {fund.replace("◈ زمینه‌ی بنیادی و ساختاری\n" + "─".repeat(30) + "\n", "")}
                    </pre>
                  </div>
                </section>
              )}

              {/* ═══ نتیجه‌گیری ═══ */}
              {concl && (
                <section className="space-y-2">
                  <h3 className="flex items-center gap-2 border-b border-border/50 pb-1.5 text-sm font-bold text-primary">
                    <span>🎯</span>
                    نتیجه‌گیری — چیکار کنم؟
                  </h3>
                  <div className="rounded-lg border border-primary/30 bg-primary/5 p-3">
                    <pre className="whitespace-pre-wrap break-words font-sans text-xs font-medium leading-relaxed text-foreground">
                      {concl.replace("◈ جمع‌بندی صادقانه\n" + "─".repeat(30) + "\n", "")}
                    </pre>
                  </div>
                </section>
              )}
            </>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">
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
        </CardContent>
      </Card>

      {/* ═══ کارت تحلیل AI ═══ */}
      <Card className="border-purple-500/30">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 text-base text-purple-400">
            <Sparkles className="h-4 w-4" />
            تحلیل هوش مصنوعی
          </CardTitle>
          <button
            onClick={() => setShowKeyInput(!showKeyInput)}
            className="text-muted-foreground hover:text-foreground"
          >
            <Settings className="h-3.5 w-3.5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-3">
          {showKeyInput && (
            <div className="space-y-2 rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
              <p className="text-[10px] text-muted-foreground">
                کلید DeepSeek خودت رو وارد کن (رایگان از{" "}
                <a
                  href="https://platform.deepseek.com/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-purple-400 underline"
                >
                  platform.deepseek.com
                </a>
                )
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs"
                  dir="ltr"
                />
                <Button size="sm" onClick={handleSaveKey}>
                  ذخیره
                </Button>
              </div>
            </div>
          )}

          <Button
            onClick={handleAiAnalyze}
            disabled={aiLoading || !aiExport}
            className="w-full bg-purple-600 hover:bg-purple-700"
            size="sm"
          >
            {aiLoading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> در حال تحلیل...
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" /> تحلیل با AI
              </>
            )}
          </Button>

          {aiError && (
            <p className="rounded-lg bg-red-500/10 p-2 text-[10px] text-red-400">
              ⚠️ {aiError}
            </p>
          )}

          {aiResult && (
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed">
                {aiResult}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}