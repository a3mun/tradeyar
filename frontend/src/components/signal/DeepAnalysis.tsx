"use client";

import { useEffect, useState } from "react";
import { Copy, Check, Brain, Sparkles, Loader2, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

const SOURCE_BADGE: Record<string, { color: string; label: string }> = {
  nobitex: { color: "bg-purple-500/15 text-purple-400 border-purple-500/30", label: "🟣 نوبیتکس" },
  bitpin: { color: "bg-green-500/15 text-green-400 border-green-500/30", label: "🟢 بیت‌پین" },
  wallex: { color: "bg-blue-500/15 text-blue-400 border-blue-500/30", label: "🔵 والکس" },
  abantether: { color: "bg-sky-500/15 text-sky-400 border-sky-500/30", label: "🔷 آبان‌تتر" },
  tsetmc: { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", label: "🇮🇷 بورس" },
};

export function DeepAnalysis() {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile } = useAppStore();
  const [text, setText] = useState("");
  const [aiExport, setAiExport] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // ═══ AI state ═══
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiError, setAiError] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState("");

  // ═══ Load API key ═══
  useEffect(() => {
    const saved = localStorage.getItem("deepseek_api_key") || "";
    setApiKey(saved);
  }, []);

  // ═══ Fetch deep analysis ═══
  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setText("");
    api
      .get("/analyze/deep", {
        params: { ticker, source, timeframe, market_type: marketType, risk_profile: riskProfile, ticker_name: tickerName },
      })
      .then((res) => setText(res.data.paragraph || ""))
      .catch(() => setText(""))
      .finally(() => setLoading(false));
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile]);

  // ═══ Fetch ai_export ═══
  useEffect(() => {
    if (!ticker) return;
    api
      .post("/analyze", {
        ticker, source, timeframe,
        market_type: marketType, risk_profile: riskProfile, ticker_name: tickerName,
      })
      .then((res) => setAiExport(res.data.ai_export || ""))
      .catch(() => setAiExport(""));
  }, [ticker, tickerName, source, timeframe, marketType, riskProfile]);

  // ═══ Copy ═══
  const handleCopy = async () => {
    if (!aiExport) return;
    try {
      await navigator.clipboard.writeText(aiExport);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) { console.error(e); }
  };

  // ═══ AI Analysis ═══
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
          "Authorization": `Bearer ${key}`,
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
- از اعداد مشخص استفاده کن (قیمت، درصد)
- به هیچ وجه تحلیل تکنیکال رو با فاندامنتال قاطی نکن`,
            },
            { role: "user", content: aiExport },
          ],
          temperature: 0.7,
          max_tokens: 800,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error?.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setAiResult(data.choices?.[0]?.message?.content || "پاسخی دریافت نشد");
    } catch (e: any) {
      setAiError(e.message || "خطا در ارتباط با AI");
    } finally {
      setAiLoading(false);
    }
  };

  const handleSaveKey = () => {
    localStorage.setItem("deepseek_api_key", apiKey);
    setShowKeyInput(false);
    setAiError("");
  };

  const src = SOURCE_BADGE[source] || SOURCE_BADGE.nobitex;

  return (
    <div className="space-y-3">
      {/* ═══ کارت تحلیل عمیق ═══ */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" />
            تحلیل عمیق
          </CardTitle>
          <Badge className={`text-[10px] border ${src.color}`}>{src.label}</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : text ? (
            <div className="rounded-lg bg-muted/30 p-3">
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-foreground">{text}</pre>
            </div>
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
            {copied ? (<><Check className="h-3.5 w-3.5" /> کپی شد</>) : (<><Copy className="h-3.5 w-3.5" /> کپی داده‌ها برای AI</>)}
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
          <button onClick={() => setShowKeyInput(!showKeyInput)} className="text-muted-foreground hover:text-foreground">
            <Settings className="h-3.5 w-3.5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* ═══ API Key ═══ */}
          {showKeyInput && (
            <div className="space-y-2 rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
              <p className="text-[10px] text-muted-foreground">
                کلید DeepSeek خودت رو وارد کن (رایگان از{" "}
                <a href="https://platform.deepseek.com/" target="_blank" rel="noreferrer" className="text-purple-400 underline">platform.deepseek.com</a>)
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
                <Button size="sm" onClick={handleSaveKey}>ذخیره</Button>
              </div>
            </div>
          )}

          {/* ═══ Button ═══ */}
          <Button
            onClick={handleAiAnalyze}
            disabled={aiLoading || !aiExport}
            className="w-full bg-purple-600 hover:bg-purple-700"
            size="sm"
          >
            {aiLoading ? (<><Loader2 className="h-3.5 w-3.5 animate-spin" /> در حال تحلیل...</>) : (<><Sparkles className="h-3.5 w-3.5" /> تحلیل با AI</>)}
          </Button>

          {/* ═══ Error ═══ */}
          {aiError && (
            <p className="rounded-lg bg-red-500/10 p-2 text-[10px] text-red-400">⚠️ {aiError}</p>
          )}

          {/* ═══ Result ═══ */}
          {aiResult && (
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
              <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed">{aiResult}</pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}