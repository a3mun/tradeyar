"use client";

/**
 * AIAnalysis — تحلیل هوش مصنوعی DeepSeek
 * ============================================================
 * نسخه ۲.۰ · فاز ۱۰.۱
 *
 * ═══ تغییرات نسخه ۲.۰ ═══
 *   • نمایش کلید فعال (مخفف)
 *   • دکمه تغییر/پاک کردن کلید
 *   • پیام خطای واضح‌تر (Insufficient Balance راهنما)
 *   • دکمه Reload کلید پس از ذخیره
 */

import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Loader2,
  Settings,
  Key,
  Trash2,
  RefreshCw,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSignalData } from "@/hooks/useSignalData";

const LS_KEY = "deepseek_api_key";

function maskKey(key: string): string {
  if (!key || key.length < 12) return "—";
  return `${key.slice(0, 6)}…${key.slice(-4)}`;
}

export function AIAnalysis() {
  const { data } = useSignalData();
  const aiExport = data?.ai_export || "";

  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiError, setAiError] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState("");

  // ═══ بارگذاری کلید ذخیره‌شده ═══
  useEffect(() => {
    const saved = localStorage.getItem(LS_KEY) || "";
    setApiKey(saved);
    setSavedKey(saved);
  }, []);

  const handleSaveKey = useCallback(() => {
    const key = apiKey.trim();
    if (!key) return;
    localStorage.setItem(LS_KEY, key);
    setSavedKey(key);
    setShowKeyInput(false);
    setAiError("");
  }, [apiKey]);

  const handleClearKey = useCallback(() => {
    localStorage.removeItem(LS_KEY);
    setApiKey("");
    setSavedKey("");
    setShowKeyInput(true);
    setAiError("");
    setAiResult("");
  }, []);

  const handleAiAnalyze = async () => {
    const key = savedKey || localStorage.getItem(LS_KEY) || "";
    if (!key) {
      setShowKeyInput(true);
      setAiError("اول کلید DeepSeek رو وارد کن");
      return;
    }
    if (!aiExport) {
      setAiError("داده‌ای برای ارسال نیست — چند ثانیه صبر کن");
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
- از اعداد مشخص استفاده کن (قیمت، درصد)
- **هیچ‌وقت از markdown مثل ** یا ## استفاده نکن**`,
            },
            { role: "user", content: aiExport },
          ],
          temperature: 0.7,
          max_tokens: 500,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const errMsg = err.error?.message || `HTTP ${res.status}`;

        // ─── راهنمای خطاهای رایج ───
        if (errMsg.includes("Insufficient Balance")) {
          throw new Error(
            "موجودی حساب DeepSeek شما صفر یا ناکافیه. " +
              "برای ادامه: کلید فعلی رو حذف کن و از platform.deepseek.com " +
              "یه کلید جدید با اعتبار بساز."
          );
        }
        if (errMsg.includes("Invalid") || errMsg.includes("authentication")) {
          throw new Error(
            "کلید DeepSeek نامعتبره. کلید رو حذف کن و دوباره وارد کن."
          );
        }
        throw new Error(errMsg);
      }

      const resData = await res.json();
      setAiResult(resData.choices?.[0]?.message?.content || "پاسخی دریافت نشد");
    } catch (e: unknown) {
      const msg = (e as Error)?.message || "خطا در ارتباط با AI";
      setAiError(msg);
    } finally {
      setAiLoading(false);
    }
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
          className="text-muted-foreground transition-colors hover:text-foreground"
          aria-label="تنظیمات کلید"
          title="تنظیمات کلید"
        >
          <Settings className="h-3.5 w-3.5" />
        </button>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* ═══ نمایش کلید فعال ═══ */}
        {savedKey && !showKeyInput && (
          <div className="flex items-center justify-between rounded-md bg-muted/20 px-2 py-1.5 text-[10px]">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Key className="h-3 w-3" />
              کلید فعال:
              <span className="num font-mono text-foreground/80">
                {maskKey(savedKey)}
              </span>
            </span>
            <button
              onClick={handleClearKey}
              className="flex items-center gap-0.5 text-red-400 hover:text-red-300"
              title="پاک کردن کلید"
            >
              <Trash2 className="h-3 w-3" />
              پاک کن
            </button>
          </div>
        )}

        {/* ═══ فرم ورود کلید ═══ */}
        {showKeyInput && (
          <div className="space-y-2 rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              کلید DeepSeek خودت رو وارد کن (رایگان از{" "}
              <a
                href="https://platform.deepseek.com/api_keys"
                target="_blank"
                rel="noreferrer"
                className="text-purple-400 underline"
              >
                platform.deepseek.com
                <ExternalLink className="mr-0.5 inline h-2.5 w-2.5" />
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
              <Button size="sm" onClick={handleSaveKey} disabled={!apiKey.trim()}>
                ذخیره
              </Button>
            </div>
            <p className="text-[9px] text-muted-foreground/70">
              🔒 کلید فقط در مرورگر شما ذخیره می‌شه — هیچ‌وقت به سرور Trademun فرستاده نمی‌شه.
            </p>
          </div>
        )}

        {/* ═══ دکمه تحلیل ═══ */}
        <Button
          onClick={handleAiAnalyze}
          disabled={aiLoading || !aiExport}
          className="w-full bg-purple-600 hover:bg-purple-700"
          size="sm"
        >
          {aiLoading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              در حال تحلیل...
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" />
              تحلیل با DeepSeek
            </>
          )}
        </Button>

        {/* ═══ نمایش خطا ═══ */}
        {aiError && (
          <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />
            <div className="flex-1 space-y-1">
              <p className="text-[10px] leading-relaxed text-red-300">
                {aiError}
              </p>
              {(aiError.includes("موجودی") ||
                aiError.includes("نامعتبر")) && (
                <button
                  onClick={() => setShowKeyInput(true)}
                  className="flex items-center gap-0.5 text-[9px] text-red-400 underline hover:text-red-300"
                >
                  <RefreshCw className="h-2.5 w-2.5" />
                  تغییر کلید
                </button>
              )}
            </div>
          </div>
        )}

        {/* ═══ نمایش نتیجه ═══ */}
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