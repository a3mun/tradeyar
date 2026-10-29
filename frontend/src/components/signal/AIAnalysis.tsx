"use client";

/**
 * AIAnalysis — تحلیل هوش مصنوعی (نسخه ۴.۰ · فاز ۱۲.۷)
 * ============================================================
 * 🔴 تغییرات نسخه ۴.۰:
 *   • حذف کامل DeepSeek (پولی بود و کاربر رو اذیت می‌کرد)
 *   • فقط OpenRouter با مدل openrouter/free (روتر خودکار)
 *   • UI ساده: دکمه طلایی + لینک گرفتن کلید
 *   • مدیریت خطای ۴۰۲ و ۴۲۹ با پیام دوستانه
 *   • هم‌رنگ تم سایت (طلایی)
 */

import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Loader2,
  Settings,
  Key,
  Trash2,
  AlertCircle,
  ExternalLink,
  Globe,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSignalData } from "@/hooks/useSignalData";

// ═══════════════════════════════════════════════════════════
// ثابت‌ها
// ═══════════════════════════════════════════════════════════
const LS_OPENROUTER = "openrouter_api_key";
const OPENROUTER_MODEL = "openrouter/free"; // روتر خودکار

// ═══════════════════════════════════════════════════════════
// پرامپت سیستم — لحن مشاور صادق
// ═══════════════════════════════════════════════════════════
const SYSTEM_PROMPT = `تو یه دوست معامله‌گر باتجربه هستی که به رفیقت مشاوره می‌دی.

قواعد:
- لحن خودمونی و صمیمی، ولی حرفه‌ای (نه خشک، نه بچه‌گانه)
- فارسی محاوره‌ای ساده، بدون اصطلاحات پیچیده
- حداکثر ۱۵۰ کلمه
- توصیه‌محور: آخرش یه جمله «الان چیکار کنم؟»
- اگه سیگنال ضعیفه، صریح بگو «الان نخر، صبر کن»
- اگه تله‌ای هست، هشدار بده
- از اعداد مشخص استفاده کن (قیمت، درصد)
- **هیچ‌وقت از markdown مثل ** یا ## استفاده نکن**`;

// ═══════════════════════════════════════════════════════════
// ابزار
// ═══════════════════════════════════════════════════════════
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

  // ═══ بارگذاری از localStorage ═══
  useEffect(() => {
    const key = localStorage.getItem(LS_OPENROUTER) || "";
    setApiKey(key);
    setSavedKey(key);
  }, []);

  // ═══ ذخیره کلید ═══
  const handleSaveKey = useCallback(() => {
    const key = apiKey.trim();
    if (!key) return;

    localStorage.setItem(LS_OPENROUTER, key);
    setSavedKey(key);
    setShowKeyInput(false);
    setAiError("");
  }, [apiKey]);

  // ═══ پاک کردن کلید ═══
  const handleClearKey = useCallback(() => {
    localStorage.removeItem(LS_OPENROUTER);
    setApiKey("");
    setSavedKey("");
    setShowKeyInput(true);
    setAiError("");
    setAiResult("");
  }, []);

  // ═══ ارسال به AI ═══
  const handleAiAnalyze = async () => {
    const key = savedKey || apiKey.trim();
    if (!key) {
      setShowKeyInput(true);
      setAiError("اول کلید رایگان OpenRouter رو وارد کن");
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
      const body = {
        model: OPENROUTER_MODEL,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: aiExport },
        ],
        temperature: 0.7,
        max_tokens: 500,
      };

      const res = await fetch(
        "https://openrouter.ai/api/v1/chat/completions",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${key}`,
            "HTTP-Referer": "https://trademun.ir",
            "X-Title": "Trademun",
          },
          body: JSON.stringify(body),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const errMsg = err.error?.message || `HTTP ${res.status}`;

        // 🔴 مدیریت خطاهای خاص OpenRouter
        if (res.status === 402 || errMsg.includes("Payment Required")) {
          throw new Error(
            "موجودی حساب OpenRouter منفیه. برای استفاده از مدل‌های رایگان، موجودی رو مثبت کن (حتی ۱ دلار کافیه) یا یه کلید جدید بساز."
          );
        }
        if (res.status === 429 || errMsg.includes("rate limit")) {
          throw new Error(
            "سهمیه روزانه تموم شد. مدل‌های رایگان OpenRouter روزی ۵۰ درخواست دارن (یا ۱۰۰۰ اگه یه بار ۱۰ دلار شارژ کنی). فردا دوباره امتحان کن."
          );
        }
        if (errMsg.includes("Invalid") || errMsg.includes("authentication")) {
          throw new Error("کلید API نامعتبره. کلید رو پاک کن و دوباره وارد کن.");
        }
        throw new Error(errMsg);
      }

      const resData = await res.json();
      setAiResult(
        resData.choices?.[0]?.message?.content || "پاسخی دریافت نشد"
      );
    } catch (e: unknown) {
      const msg = (e as Error)?.message || "خطا در ارتباط با AI";
      setAiError(msg);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
      <CardTitle className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="h-4 w-4 text-primary" />
        تحلیل هوش مصنوعی
      </CardTitle>
        <button
          onClick={() => setShowKeyInput(!showKeyInput)}
          className="text-muted-foreground transition-colors hover:text-foreground"
          aria-label="تنظیمات"
          title="تنظیمات"
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
          <div className="rounded-lg border border-border bg-muted/10 p-3">
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              کلید رایگان OpenRouter از{" "}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noreferrer"
                className="text-yellow-500 underline"
              >
                openrouter.ai/keys
                <ExternalLink className="mr-0.5 inline h-2.5 w-2.5" />
              </a>{" "}
              — با ثبت‌نام رایگان (روزی ۵۰ درخواست)
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-or-..."
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs"
                dir="ltr"
              />
              <Button
                size="sm"
                onClick={handleSaveKey}
                disabled={!apiKey.trim()}
                variant="default"
                className="font-bold"
              >
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
          className="w-full font-bold"
          variant="default"
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
              تحلیل با هوش مصنوعی
            </>
          )}
        </Button>

        {/* ═══ خطا ═══ */}
        {aiError && (
          <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />
            <div className="flex-1 space-y-1">
              <p className="text-[10px] leading-relaxed text-red-300">
                {aiError}
              </p>
              {(aiError.includes("موجودی") ||
                aiError.includes("نامعتبر") ||
                aiError.includes("کلید")) && (
                <button
                  onClick={() => setShowKeyInput(true)}
                  className="flex items-center gap-0.5 text-[9px] text-red-400 underline hover:text-red-300"
                >
                  <Globe className="h-2.5 w-2.5" />
                  تغییر کلید
                </button>
              )}
            </div>
          </div>
        )}

        {/* ═══ نتیجه ═══ */}
        {aiResult && (
          <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3">
            <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed">
              {aiResult}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}