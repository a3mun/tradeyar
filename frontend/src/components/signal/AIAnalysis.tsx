"use client";

/**
 * AIAnalysis — تحلیل هوش مصنوعی (نسخه ۱.۰ — فاز ۸.۴)
 * ============================================================
 * کارت مستقل AI — جدا از DeepAnalysis
 */

import { useEffect, useState } from "react";
import { Sparkles, Loader2, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSignalData } from "@/hooks/useSignalData";

export function AIAnalysis() {
  const { data } = useSignalData();
  const aiExport = data?.ai_export || "";

  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiError, setAiError] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("deepseek_api_key") || "";
    setApiKey(saved);
  }, []);

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

  return (
    <Card className="border-purple-500/30">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm text-purple-400">
          <Sparkles className="h-4 w-4" />
          تحلیل هوش مصنوعی
        </CardTitle>
        <button
          onClick={() => setShowKeyInput(!showKeyInput)}
          className="text-muted-foreground hover:text-foreground"
          aria-label="تنظیمات کلید"
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
  );
}