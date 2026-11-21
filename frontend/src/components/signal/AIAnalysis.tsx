
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Loader2,
  AlertCircle,
  Check,
  Copy,
  ClipboardCopy,
  Bot,
  ArrowUpRight,
  Info,
  History,
  Clock,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useSignalData } from "@/hooks/useSignalData";

// تنظیمات
const MAX_HISTORY = 5;
const HISTORY_TTL = 5 * 24 * 60 * 60 * 1000;
const DAILY_LIMIT = 10;

type CachedAnalysis = {
  id: string;
  data: string;
  response: string;
  symbol: string;
  createdAt: string;
};

type DailyUsage = {
  date: string;
  count: number;
};

interface AIAnalysisProps {
  userId?: string;
  symbol?: string;
}

// تاریخ روز بر اساس UTC
function getUTCDate() {
  return new Date().toISOString().slice(0, 10);
}

// استخراج نام نماد از اطلاعات تحلیل
function getSymbolFromData(data: unknown): string {
  if (!data || typeof data !== "object") {
    return "نماد فعلی";
  }

  const obj = data as Record<string, unknown>;

  const candidates = [
    obj.symbol,
    obj.ticker,
    obj.pair,
    obj.symbol_name,
    obj.market,
    obj.asset,
  ];

  for (const value of candidates) {
    if (
      typeof value === "string" &&
      value.trim().length > 0
    ) {
      return value.trim().toUpperCase();
    }
  }

  // بررسی اطلاعات تو در تو
  for (const key of ["meta", "info", "market_data"]) {
    const nested = obj[key];

    if (nested && typeof nested === "object") {
      const result = getSymbolFromData(nested);

      if (result !== "نماد فعلی") return result;
    }
  }

  return "نماد فعلی";
}

// سهمیه روزانه
function getDailyUsage(key: string): DailyUsage {
  try {
    const saved = localStorage.getItem(key);

    if (saved) {
      const usage: DailyUsage = JSON.parse(saved);

      if (
        usage.date === getUTCDate() &&
        Number.isInteger(usage.count) &&
        usage.count >= 0
      ) {
        return usage;
      }
    }
  } catch (error) {
    console.error("[AI Usage]", error);
  }

  return {
    date: getUTCDate(),
    count: 0,
  };
}

// ذخیره تاریخچه
function saveHistory(
  key: string,
  items: CachedAnalysis[]
) {
  try {
    localStorage.setItem(
      key,
      JSON.stringify(items.slice(0, MAX_HISTORY))
    );
  } catch (error) {
    console.error("[AI History]", error);
  }
}

// اعتبارسنجی و پاک‌سازی تاریخچه پنج روزه
function cleanHistory(items: unknown): CachedAnalysis[] {
  if (!Array.isArray(items)) return [];

  const now = Date.now();

  return items
    .filter((item): item is CachedAnalysis => {
      if (
        !item ||
        typeof item.id !== "string" ||
        typeof item.data !== "string" ||
        typeof item.response !== "string" ||
        typeof item.symbol !== "string" ||
        typeof item.createdAt !== "string"
      ) {
        return false;
      }

      const timestamp = new Date(item.createdAt).getTime();

      return (
        Number.isFinite(timestamp) &&
        timestamp <= now &&
        now - timestamp < HISTORY_TTL
      );
    })
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() -
        new Date(a.createdAt).getTime()
    )
    .slice(0, MAX_HISTORY);
}

// تاریخ فارسی
function formatDate(date: string) {
  return new Date(date).toLocaleString("fa-IR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const CHAT_SERVICES = [
  {
    id: "deepseek",
    name: "DeepSeek",
    icon: "🐋",
    url: "https://chat.deepseek.com/",
    note: "بدون VPN · رایگان",
    vpnRequired: false,
  },
  {
    id: "chatgpt",
    name: "ChatGPT",
    icon: "🤖",
    url: "https://chat.openai.com/",
    note: "بدون VPN · رایگان",
    vpnRequired: false,
  },
  {
    id: "gemini",
    name: "Gemini",
    icon: "✨",
    url: "https://gemini.google.com/app",
    note: "نیاز به VPN",
    vpnRequired: true,
  },
  {
    id: "claude",
    name: "Claude",
    icon: "🎭",
    url: "https://claude.ai/",
    note: "نیاز به VPN",
    vpnRequired: true,
  },
  {
    id: "groq",
    name: "Groq",
    icon: "⚡",
    url: "https://console.groq.com/playground",
    note: "نیاز به VPN",
    vpnRequired: true,
  },
] as const;

export function AIAnalysis({
  userId = "guest",
  symbol: symbolProp,
}: AIAnalysisProps) {
  const { data } = useSignalData();

  const aiExport = data?.ai_export || "";

  // اولویت با نمادی است که صریحاً از والد دریافت می‌شود
  const currentSymbol =
    symbolProp?.trim().toUpperCase() ||
    getSymbolFromData(data);

  // ذخیره مستقل برای هر کاربر
  const namespace = encodeURIComponent(userId);

  const historyKey = `ai-history-v2-${namespace}`;
  const usageKey = `ai-usage-v2-${namespace}`;

  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [aiError, setAiError] = useState("");

  const [copied, setCopied] = useState(false);
  const [copiedResult, setCopiedResult] = useState(false);
  const [showChatServices, setShowChatServices] = useState(false);

  const [recentAnalyses, setRecentAnalyses] =
    useState<CachedAnalysis[]>([]);

  const [selectedId, setSelectedId] = useState<string | null>(
    null
  );

  const [historyLoaded, setHistoryLoaded] = useState(false);

  // بارگذاری تاریخچه کاربر
  useEffect(() => {
    setHistoryLoaded(false);
    setAiResult("");
    setSelectedId(null);

    try {
      const saved = localStorage.getItem(historyKey);

      const parsed = saved ? JSON.parse(saved) : [];

      const cleaned = cleanHistory(parsed);

      setRecentAnalyses(cleaned);

      // ذخیره مجدد تاریخچه پاک‌سازی‌شده
      saveHistory(historyKey, cleaned);
    } catch (error) {
      console.error("[AI History Load]", error);
      setRecentAnalyses([]);
    } finally {
      setHistoryLoaded(true);
    }
  }, [historyKey]);

  // کپی داده خام
  const handleCopyRaw = useCallback(async () => {
    if (!aiExport) return;

    try {
      await navigator.clipboard.writeText(aiExport);

      setCopied(true);
      setShowChatServices(true);

      setTimeout(() => setCopied(false), 3000);
    } catch (error) {
      console.error("[Copy]", error);
    }
  }, [aiExport]);

  // کپی نتیجه
  const handleCopyResult = useCallback(async () => {
    if (!aiResult) return;

    try {
      await navigator.clipboard.writeText(aiResult);

      setCopiedResult(true);

      setTimeout(() => setCopiedResult(false), 3000);
    } catch (error) {
      console.error("[Copy Result]", error);
    }
  }, [aiResult]);

  // انتخاب تحلیل قبلی
  const handleViewHistory = (item: CachedAnalysis) => {
    setAiResult(item.response);
    setAiError("");
    setCopiedResult(false);
    setSelectedId(item.id);
  };

  // تحلیل هوشمند
  const handleAiAnalyze = async () => {
    if (!aiExport) {
      setAiError("داده‌ای برای تحلیل نیست — چند لحظه صبر کن.");
      return;
    }

    if (aiLoading || !historyLoaded) return;

    setAiError("");
    setAiResult("");
    setSelectedId(null);

    // ۱. بررسی کش قبل از مصرف سهمیه
    const cached = recentAnalyses.find(
      (item) => item.data === aiExport
    );

    if (cached) {
      handleViewHistory(cached);
      return;
    }

    // ۲. بررسی محدودیت روزانه
    const usage = getDailyUsage(usageKey);

    if (usage.count >= DAILY_LIMIT) {
      setAiError(
        "محدودیت موقت روزانه استفاده از تحلیل هوشمند برای حساب کاربری شما به پایان رسیده است. لطفاً ساعت ۰۳:۳۰ بامداد به وقت ایران (۰۰:۰۰ UTC) مجدداً مراجعه کنید."
      );
      return;
    }

    setAiLoading(true);

    try {
      // ۳. درخواست به API
      const res = await api.post<{
        ok: boolean;
        response: string;
        error?: string;
      }>(
        "/ai",
        { data: aiExport },
        { timeout: 60000 }
      );

      if (!res.data.ok || !res.data.response) {
        throw new Error(
          res.data.error || "خطا در تحلیل هوشمند"
        );
      }

      const response = res.data.response;

      // ۴. ثبت درخواست موفق
      const latestUsage = getDailyUsage(usageKey);

      const updatedUsage: DailyUsage = {
        date: getUTCDate(),
        count: latestUsage.count + 1,
      };

      try {
        localStorage.setItem(
          usageKey,
          JSON.stringify(updatedUsage)
        );
      } catch (error) {
        console.error("[AI Usage Save]", error);
      }

      // ۵. ساخت رکورد تاریخچه
      const newAnalysis: CachedAnalysis = {
        id: crypto.randomUUID(),
        data: aiExport,
        response,
        symbol: currentSymbol,
        createdAt: new Date().toISOString(),
      };

      const updatedHistory = cleanHistory([
        newAnalysis,
        ...recentAnalyses.filter(
          (item) => item.data !== aiExport
        ),
      ]);

      setRecentAnalyses(updatedHistory);

      saveHistory(historyKey, updatedHistory);

      setAiResult(response);
      setSelectedId(newAnalysis.id);

    } catch (error: unknown) {
      const msg =
        (
          error as {
            response?: {
              data?: {
                detail?: string;
              };
            };
          }
        )?.response?.data?.detail ||
        (error as Error)?.message ||
        "مشکلی در دریافت تحلیل پیش آمد.";

      setAiError(msg);

      // خطا سهمیه مصرف نمی‌کند
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="space-y-4">

      {/* تحلیل هوشمند */}
      <div className="rounded-xl border border-[#d6ad60]/20 bg-[#051118] p-4 shadow-xl space-y-3">

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-[#d6ad60]/10 p-1.5 text-[#d6ad60]">
              <Sparkles className="h-4 w-4" />
            </div>

            <span className="text-sm font-bold text-gray-100">
              تحلیل با هوش مصنوعی
            </span>
          </div>

          <span className="text-[10px] text-gray-500">
            Cloudflare AI
          </span>
        </div>

        <p className="text-[11px] leading-relaxed text-gray-400">
          داده‌های تکنیکال این نماد به صورت خودکار به هوش مصنوعی
          ارسال می‌شود و یک تحلیل جامع از روند، نقطه ورود،
          حمایت و مقاومت و مدیریت ریسک دریافت می‌کنید.
        </p>

        {/* دکمه تحلیل */}
        <Button
          onClick={handleAiAnalyze}
          disabled={
            aiLoading ||
            !aiExport ||
            !historyLoaded
          }
          className="w-full h-10 font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90 transition-all"
        >
          {aiLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              در حال تحلیل...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" />
              دریافت تحلیل هوشمند
            </>
          )}
        </Button>

        {/* تاریخچه جمع و جور */}
        {historyLoaded && recentAnalyses.length > 0 && (
          <div className="pt-2 space-y-1.5">

            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-1.5">
                <History className="h-3.5 w-3.5 text-[#d6ad60]" />

                <span className="text-[11px] font-bold text-gray-300">
                  تحلیل‌های اخیر
                </span>
              </div>

              <span className="text-[9px] text-gray-500">
                نگهداری ۵ روزه
              </span>
            </div>

            {recentAnalyses.map((item) => {
              const isSelected = selectedId === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleViewHistory(item)}
                  aria-pressed={isSelected}
                  className={`
                    w-full min-h-[36px]
                    flex items-center justify-between gap-2
                    rounded-md border px-2.5 py-1.5
                    text-right transition-all
                    ${
                      isSelected
                        ? "border-[#d6ad60]/70 bg-[#d6ad60]/10 shadow-[inset_0_0_0_1px_rgba(214,173,96,0.12)]"
                        : "border-white/5 bg-black/20 hover:border-white/15 hover:bg-white/[0.03]"
                    }
                  `}
                >
                  <div className="flex items-center gap-2 min-w-0">

                    <span
                      className={`
                        flex h-5 w-5 shrink-0 items-center justify-center
                        rounded text-[9px] font-bold
                        ${
                          isSelected
                            ? "bg-[#d6ad60] text-[#101827]"
                            : "bg-white/5 text-gray-500"
                        }
                      `}
                    >
                      {isSelected ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Bot className="h-3 w-3" />
                      )}
                    </span>

                    <span
                      className={`text-[10px] font-semibold truncate ${
                        isSelected
                          ? "text-[#e2c17e]"
                          : "text-gray-300"
                      }`}
                    >
                      {item.symbol}
                    </span>

                    <span className="text-[9px] text-gray-600">
                      {formatDate(item.createdAt)}
                    </span>

                  </div>

                  <span
                    className={`text-[9px] shrink-0 ${
                      isSelected
                        ? "text-[#e2c17e]"
                        : "text-gray-600"
                    }`}
                  >
                    {isSelected ? "انتخاب‌شده" : "مشاهده"}
                  </span>

                </button>
              );
            })}
          </div>
        )}

        {/* خطا */}
        {aiError && (
          <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />

            <p className="text-[10px] leading-relaxed text-red-300">
              {aiError}
            </p>
          </div>
        )}

        {/* نتیجه */}
        {aiResult && (
          <div className="mt-3 rounded-lg border border-white/5 bg-black/20 p-3">

            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Bot className="h-4 w-4 text-[#d6ad60]" />

                <span className="text-xs font-bold text-gray-200">
                  تحلیل هوش مصنوعی
                </span>

                {selectedId && (
                  <span className="text-[9px] text-[#d6ad60]">
                    · ذخیره‌شده
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={handleCopyResult}
                className="text-[10px] flex items-center gap-1 text-gray-500 hover:text-[#d6ad60] transition-colors"
              >
                {copiedResult ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}

                {copiedResult ? "کپی شد" : "کپی متن"}
              </button>
            </div>

            <div className="max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-gray-300 text-justify">
                {aiResult}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* کپی داده خام */}
      <div className="rounded-xl border border-white/5 bg-[#051118] p-4 shadow-xl space-y-3">

        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-white/5 p-1.5 text-gray-400">
            <ClipboardCopy className="h-4 w-4" />
          </div>

          <span className="text-sm font-bold text-gray-100">
            کپی داده‌های خام
          </span>
        </div>

        <p className="text-[11px] leading-relaxed text-gray-400">
          اگر ترجیح می‌دهید از هوش مصنوعی دیگری استفاده کنید،
          می‌توانید داده‌های کامل تحلیل را کپی کرده و در سرویس‌های
          زیر پیست کنید.
        </p>

        <Button
          onClick={handleCopyRaw}
          disabled={!aiExport}
          variant="outline"
          className={`w-full h-10 border-white/10 font-bold transition-colors ${
            copied
              ? "bg-green-500/10 text-green-400 border-green-500/30"
              : "text-gray-200 hover:bg-white/5"
          }`}
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 mr-2" />
              کپی شد — حالا در چت پیست کنید
            </>
          ) : (
            <>
              <Copy className="h-4 w-4 mr-2" />
              کپی داده‌های خام
            </>
          )}
        </Button>

        {showChatServices && (
          <div className="space-y-2 pt-2">

            <p className="text-[10px] font-bold text-gray-500">
              👇 یکی از سرویس‌های زیر را انتخاب کنید:
            </p>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {CHAT_SERVICES.map((svc) => (
                <a
                  key={svc.id}
                  href={svc.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group relative flex flex-col items-start gap-1 rounded-lg border border-white/5 bg-black/20 p-2 hover:border-[#d6ad60]/30 hover:bg-white/5 transition-colors"
                >
                  {svc.vpnRequired && (
                    <span className="absolute -top-1.5 -right-1.5 rounded-full bg-orange-500/90 px-1.5 py-0.5 text-[8px] font-bold text-white shadow-sm">
                      VPN
                    </span>
                  )}

                  <div className="flex items-center gap-1.5 w-full">
                    <span className="text-sm">
                      {svc.icon}
                    </span>

                    <span className="text-[11px] font-bold text-gray-200">
                      {svc.name}
                    </span>

                    <ArrowUpRight className="h-3 w-3 ml-auto text-gray-500 group-hover:text-[#d6ad60]" />
                  </div>

                  <p
                    className={`text-[8px] ${
                      svc.vpnRequired
                        ? "text-orange-400/80"
                        : "text-green-400/80"
                    }`}
                  >
                    {svc.note}
                  </p>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* توضیحات */}
      <div className="flex items-start gap-1.5 px-1">
        <Info className="h-3 w-3 mt-0.5 shrink-0 text-gray-600" />

        <p className="text-[9px] leading-relaxed text-gray-500 text-justify">
          تحلیل‌های هوش مصنوعی صرفاً جنبه کمکی دارند و جایگزین
          تحلیل شخصی شما نیستند. تصمیم نهایی با خودتان است.
        </p>
      </div>

    </div>
  );
}
