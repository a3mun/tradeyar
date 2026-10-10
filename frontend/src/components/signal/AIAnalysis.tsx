"use client";

/**
 * AIAnalysis — تحلیل هوش مصنوعی (DeepSeek + OpenRouter)
 * ============================================================
 * نسخه ۳.۰ · فاز ۱۰.۲
 *
 * ═══ تغییرات نسخه ۳.۰ ═══
 *   • پشتیبانی از OpenRouter (مدل‌های رایگان)
 *   • انتخاب provider (DeepSeek / OpenRouter)
 *   • انتخاب مدل OpenRouter
 *   • نمایش کلید فعال (مخفف) + دکمه پاک کردن
 *   • راهنمای گام‌به‌گام برای گرفتن کلید
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
  Zap,
  Globe,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSignalData } from "@/hooks/useSignalData";

// ═══════════════════════════════════════════════════════════
// ثابت‌ها
// ═══════════════════════════════════════════════════════════
const LS_DEEPSEEK = "deepseek_api_key";
const LS_OPENROUTER = "openrouter_api_key";
const LS_PROVIDER = "ai_provider";
const LS_MODEL = "openrouter_model";

type Provider = "deepseek" | "openrouter";

interface OpenRouterModel {
  id: string;
  label: string;
  desc: string;
}

// مدل‌های رایگان OpenRouter
const OPENROUTER_MODELS: OpenRouterModel[] = [
  {
    id: "deepseek/deepseek-r1:free",
    label: "DeepSeek R1 (رایگان)",
    desc: "استدلال قوی · کیفیت عالی",
  },
  {
    id: "deepseek/deepseek-chat-v3.1:free",
    label: "DeepSeek V3.1 (رایگان)",
    desc: "سریع · کیفیت خوب",
  },
  {
    id: "google/gemini-flash-1.5-8b",
    label: "Gemini 1.5 Flash (رایگان)",
    desc: "سریع‌ترین · عالی برای موبایل",
  },
  {
    id: "meta-llama/llama-3.3-70b-instruct:free",
    label: "Llama 3.3 70B (رایگان)",
    desc: "قدرتمند · پایداری خوب",
  },
];

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

  // ─── provider + model ───
  const [provider, setProvider] = useState<Provider>("openrouter");
  const [model, setModel] = useState<string>(OPENROUTER_MODELS[0].id);

  // ─── کلیدها ───
  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState("");

  // ═══ بارگذاری از localStorage ═══
  useEffect(() => {
    const savedProvider =
      (localStorage.getItem(LS_PROVIDER) as Provider) || "openrouter";
    const savedModel =
      localStorage.getItem(LS_MODEL) || OPENROUTER_MODELS[0].id;

    setProvider(savedProvider);
    setModel(savedModel);

    const key =
      savedProvider === "deepseek"
        ? localStorage.getItem(LS_DEEPSEEK) || ""
        : localStorage.getItem(LS_OPENROUTER) || "";
    setApiKey(key);
    setSavedKey(key);
  }, []);

  // ═══ تغییر provider ═══
  const handleProviderChange = useCallback((newProvider: Provider) => {
    setProvider(newProvider);
    localStorage.setItem(LS_PROVIDER, newProvider);

    const key =
      newProvider === "deepseek"
        ? localStorage.getItem(LS_DEEPSEEK) || ""
        : localStorage.getItem(LS_OPENROUTER) || "";
    setApiKey(key);
    setSavedKey(key);
    setAiError("");
    setAiResult("");
  }, []);

  // ═══ تغییر model ═══
  const handleModelChange = useCallback((newModel: string) => {
    setModel(newModel);
    localStorage.setItem(LS_MODEL, newModel);
  }, []);

  // ═══ ذخیره کلید ═══
  const handleSaveKey = useCallback(() => {
    const key = apiKey.trim();
    if (!key) return;

    if (provider === "deepseek") {
      localStorage.setItem(LS_DEEPSEEK, key);
    } else {
      localStorage.setItem(LS_OPENROUTER, key);
    }
    setSavedKey(key);
    setShowKeyInput(false);
    setAiError("");
  }, [apiKey, provider]);

  // ═══ پاک کردن کلید ═══
  const handleClearKey = useCallback(() => {
    if (provider === "deepseek") {
      localStorage.removeItem(LS_DEEPSEEK);
    } else {
      localStorage.removeItem(LS_OPENROUTER);
    }
    setApiKey("");
    setSavedKey("");
    setShowKeyInput(true);
    setAiError("");
    setAiResult("");
  }, [provider]);

  // ═══ ارسال به AI ═══
  const handleAiAnalyze = async () => {
    const key = savedKey || apiKey.trim();
    if (!key) {
      setShowKeyInput(true);
      setAiError("اول کلید API رو وارد کن");
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
      const endpoint =
        provider === "deepseek"
          ? "https://api.deepseek.com/chat/completions"
          : "https://openrouter.ai/api/v1/chat/completions";

      const modelId =
        provider === "deepseek" ? "deepseek-chat" : model;

      const body = {
        model: modelId,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: aiExport },
        ],
        temperature: 0.7,
        max_tokens: 500,
      };

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      };

      // ─── OpenRouter specific ───
      if (provider === "openrouter") {
        headers["HTTP-Referer"] = "https://trademun.ir";
        headers["X-Title"] = "Trademun";
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const errMsg = err.error?.message || `HTTP ${res.status}`;

        if (errMsg.includes("Insufficient Balance")) {
          throw new Error(
            "موجودی حساب DeepSeek صفر یا ناکافیه. برای ادامه: کلید فعلی رو حذف کن و از platform.deepseek.com یه کلید جدید با اعتبار بساز. یا از OpenRouter (رایگان) استفاده کن."
          );
        }
        if (errMsg.includes("Invalid") || errMsg.includes("authentication")) {
          throw new Error("کلید API نامعتبره. کلید رو حذف کن و دوباره وارد کن.");
        }
        if (errMsg.includes("rate limit") || errMsg.includes("429")) {
          throw new Error(
            "تعداد درخواست‌ها زیاده. چند دقیقه صبر کن و دوباره تلاش کن."
          );
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

  const currentModel = OPENROUTER_MODELS.find((m) => m.id === model);

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
          aria-label="تنظیمات"
          title="تنظیمات"
        >
          <Settings className="h-3.5 w-3.5" />
        </button>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* ═══ انتخاب provider ═══ */}
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            سرویس AI
          </label>
          <div className="grid grid-cols-2 gap-1.5">
            <Button
              size="sm"
              variant={provider === "openrouter" ? "default" : "outline"}
              onClick={() => handleProviderChange("openrouter")}
              className={`h-7 text-[10px] ${
                provider === "openrouter"
                  ? "bg-purple-600 hover:bg-purple-700"
                  : ""
              }`}
            >
              <Globe className="h-3 w-3 mr-1" />
              OpenRouter (رایگان)
            </Button>
            <Button
              size="sm"
              variant={provider === "deepseek" ? "default" : "outline"}
              onClick={() => handleProviderChange("deepseek")}
              className={`h-7 text-[10px] ${
                provider === "deepseek"
                  ? "bg-purple-600 hover:bg-purple-700"
                  : ""
              }`}
            >
              <Zap className="h-3 w-3 mr-1" />
              DeepSeek
            </Button>
          </div>
        </div>

        {/* ═══ انتخاب مدل (فقط OpenRouter) ═══ */}
        {provider === "openrouter" && (
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">
              مدل
            </label>
            <select
              value={model}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[10px]"
            >
              {OPENROUTER_MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            {currentModel && (
              <p className="text-[9px] text-muted-foreground/70">
                {currentModel.desc}
              </p>
            )}
          </div>
        )}

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
              {provider === "deepseek" ? (
                <>
                  کلید DeepSeek از{" "}
                  <a
                    href="https://platform.deepseek.com/api_keys"
                    target="_blank"
                    rel="noreferrer"
                    className="text-purple-400 underline"
                  >
                    platform.deepseek.com
                    <ExternalLink className="mr-0.5 inline h-2.5 w-2.5" />
                  </a>{" "}
                  — نیاز به اعتبار داره
                </>
              ) : (
                <>
                  کلید رایگان OpenRouter از{" "}
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noreferrer"
                    className="text-purple-400 underline"
                  >
                    openrouter.ai/keys
                    <ExternalLink className="mr-0.5 inline h-2.5 w-2.5" />
                  </a>{" "}
                  — رایگان با ثبت‌نام
                </>
              )}
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={provider === "deepseek" ? "sk-..." : "sk-or-..."}
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs"
                dir="ltr"
              />
              <Button
                size="sm"
                onClick={handleSaveKey}
                disabled={!apiKey.trim()}
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
              تحلیل با {provider === "deepseek" ? "DeepSeek" : "OpenRouter"}
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
                  <RefreshCw className="h-2.5 w-2.5" />
                  تغییر کلید
                </button>
              )}
            </div>
          </div>
        )}

        {/* ═══ نتیجه ═══ */}
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