"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Sparkles, Loader2, Settings, Key, Trash2, AlertCircle, ExternalLink,
  Globe, Check, Copy, ClipboardCopy, Bot, ArrowUpRight, Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useSignalData } from "@/hooks/useSignalData";

const LS_OPENROUTER = "openrouter_api_key";

const CHAT_SERVICES = [
  { id: "deepseek", name: "DeepSeek", icon: "🐋", url: "https://chat.deepseek.com/", note: "بدون VPN · رایگان", color: "border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10", vpnRequired: false },
  { id: "chatgpt", name: "ChatGPT", icon: "🤖", url: "https://chat.openai.com/", note: "بدون VPN · رایگان", color: "border-green-500/30 bg-green-500/5 hover:bg-green-500/10", vpnRequired: false },
  { id: "gemini", name: "Gemini", icon: "✨", url: "https://gemini.google.com/app", note: "نیاز به VPN", color: "border-purple-500/30 bg-purple-500/5 hover:bg-purple-500/10", vpnRequired: true },
  { id: "claude", name: "Claude", icon: "🎭", url: "https://claude.ai/", note: "نیاز به VPN", color: "border-orange-500/30 bg-orange-500/5 hover:bg-orange-500/10", vpnRequired: true },
  { id: "groq", name: "Groq", icon: "⚡", url: "https://console.groq.com/playground", note: "نیاز به VPN", color: "border-red-500/30 bg-red-500/5 hover:bg-red-500/10", vpnRequired: true },
] as const;

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
  const [copied, setCopied] = useState(false);
  const [showChatServices, setShowChatServices] = useState(false);

  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState("");

  useEffect(() => {
    const key = localStorage.getItem(LS_OPENROUTER) || "";
    setApiKey(key);
    setSavedKey(key);
  }, []);

  const handleSaveKey = useCallback(() => {
    const key = apiKey.trim();
    if (!key) return;
    localStorage.setItem(LS_OPENROUTER, key);
    setSavedKey(key);
    setShowKeyInput(false);
    setAiError("");
  }, [apiKey]);

  const handleClearKey = useCallback(() => {
    localStorage.removeItem(LS_OPENROUTER);
    setApiKey("");
    setSavedKey("");
    setShowKeyInput(true);
    setAiError("");
    setAiResult("");
  }, []);

  const handleCopyRaw = useCallback(async () => {
    if (!aiExport) return;
    try {
      await navigator.clipboard.writeText(aiExport);
      setCopied(true);
      setShowChatServices(true);
      setTimeout(() => setCopied(false), 3000);
    } catch (e) {
      console.error("[Copy] خطا:", e);
    }
  }, [aiExport]);

  const handleAiAnalyze = async () => {
    if (!aiExport) {
      setAiError("داده‌ای برای تحلیل نیست — چند لحظه صبر کن.");
      return;
    }

    setAiLoading(true);
    setAiError("");
    setAiResult("");

    try {
      // 🔴 درخواست به پروکسی بک‌اند (نه مستقیم به OpenRouter)
      const res = await api.post<{ ok: boolean; response: string; error?: string }>(
        "/ai",
        {
          data: aiExport,
          api_key: savedKey || apiKey.trim() || undefined,
        },
        { timeout: 60000 },
      );

      if (!res.data.ok) {
        throw new Error(res.data.error || "خطا در تحلیل");
      }
      setAiResult(res.data.response);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e as Error)?.message ||
        "مشکلی پیش آمد";
      setAiError(msg);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 px-2.5 py-2">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-400" />
        <p className="text-[10px] leading-relaxed text-blue-300/90">
          <b>دو روش داری:</b> یا با API رایگان مستقیم تحلیل بگیر، یا داده‌های خام رو کپی کن و توی <b>DeepSeek</b> یا <b>ChatGPT</b> بچسبون. اگه روش اول خطا داد، روش دوم همیشه جواب می‌ده.
        </p>
      </div>

      {/* روش ۱ */}
      <div className="rounded-lg border border-[#d6ad60]/20 bg-[#d6ad60]/5 p-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-[#d6ad60]" />
            <span className="text-[11px] font-bold text-[#d6ad60]">روش ۱ — تحلیل مستقیم</span>
          </div>
          <button
            onClick={() => setShowKeyInput(!showKeyInput)}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
            title="تنظیمات کلید"
          >
            <Settings className="h-3.5 w-3.5" />
          </button>
        </div>

        {savedKey && !showKeyInput && (
          <div className="flex items-center justify-between rounded-md bg-muted/20 px-2 py-1.5 text-[10px]">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Key className="h-3 w-3" />
              کلید فعال:
              <span className="num font-mono text-foreground/80">{maskKey(savedKey)}</span>
            </span>
            <button onClick={handleClearKey} className="flex items-center gap-0.5 text-red-400 hover:text-red-300">
              <Trash2 className="h-3 w-3" /> پاک کن
            </button>
          </div>
        )}

        {showKeyInput && (
          <div className="rounded-lg border border-border bg-background/50 p-2.5">
            <p className="text-[10px] leading-relaxed text-muted-foreground mb-1.5">
              یه کلید رایگان از{" "}
              <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="text-yellow-500 underline">
                openrouter.ai/keys <ExternalLink className="mr-0.5 inline h-2.5 w-2.5" />
              </a>{" "}
              بگیر (روزی ۵۰ درخواست رایگان).
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
              <Button size="sm" onClick={handleSaveKey} disabled={!apiKey.trim()} variant="default" className="font-bold">
                ذخیره
              </Button>
            </div>
            <p className="text-[9px] text-muted-foreground/70 mt-1">
              🔒 کلیدت فقط توی مرورگر خودت ذخیره میشه و هیچ‌وقت به سرور ما فرستاده نمیشه.
            </p>
          </div>
        )}

        <Button
          onClick={handleAiAnalyze}
          disabled={aiLoading || !aiExport}
          className="w-full font-bold"
          variant="default"
          size="sm"
        >
          {aiLoading ? (
            <><Loader2 className="h-3.5 w-3.5 animate-spin" /> در حال تحلیل...</>
          ) : (
            <><Sparkles className="h-3.5 w-3.5" /> تحلیل با هوش مصنوعی</>
          )}
        </Button>
      </div>

      {/* روش ۲ */}
      <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3 space-y-2">
        <div className="flex items-center gap-1.5">
          <ClipboardCopy className="h-3.5 w-3.5 text-purple-400" />
          <span className="text-[11px] font-bold text-purple-400">روش ۲ — کپی داده خام</span>
        </div>

        <p className="text-[10px] leading-relaxed text-muted-foreground">
          داده‌های کامل تحلیل رو کپی کن و توی هر هوش مصنوعی (DeepSeek، ChatGPT، Gemini و...) بچسبون.
          <br />
          <span className="text-purple-400 font-medium">⚡ سریع‌ترین راه برای تحلیل لحظه‌ای</span>
        </p>

        <Button
          onClick={handleCopyRaw}
          disabled={!aiExport}
          variant="default"
          size="sm"
          className={`w-full font-bold transition-colors ${copied ? "bg-green-600 text-white hover:bg-green-700" : "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"}`}
        >
          {copied ? (
            <><Check className="h-3.5 w-3.5" /> کپی شد — حالا توی چت پیست کن</>
          ) : (
            <><Copy className="h-3.5 w-3.5" /> کپی داده‌های خام برای AI</>
          )}
        </Button>

        {showChatServices && (
          <div className="space-y-1.5 pt-1">
            <p className="text-[9px] font-bold text-muted-foreground">👇 یکی رو انتخاب کن و توی چت پیست کن:</p>
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
              {CHAT_SERVICES.map((svc) => (
                <a key={svc.id} href={svc.url} target="_blank" rel="noreferrer" className={`group relative flex items-center justify-between gap-1 rounded-md border px-2 py-1.5 transition-colors ${svc.color}`}>
                  {svc.vpnRequired && (
                    <span className="absolute -top-1.5 -right-1.5 rounded-full bg-orange-500/90 px-1 py-0.5 text-[7px] font-bold text-white shadow-sm" title="نیاز به VPN">VPN</span>
                  )}
                  <div className="min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-[12px]">{svc.icon}</span>
                      <span className="text-[10px] font-bold truncate">{svc.name}</span>
                    </div>
                    <p className={`text-[8px] truncate ${svc.vpnRequired ? "text-orange-400/80" : "text-emerald-400/80"}`}>{svc.note}</p>
                  </div>
                  <ArrowUpRight className="h-3 w-3 shrink-0 opacity-60" />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="text-[8.5px] text-muted-foreground/70 text-center leading-relaxed pt-1">
        💡 برای کاربران ایران: <span className="text-emerald-400">DeepSeek</span> و <span className="text-emerald-400">ChatGPT</span> بدون VPN کار می‌کنن. بقیه نیاز به VPN دارن.
      </p>

      {aiError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />
          <div className="flex-1 space-y-1">
            <p className="text-[10px] leading-relaxed text-red-300">{aiError}</p>
            {(aiError.includes("اعتبار") || aiError.includes("نامعتبر") || aiError.includes("کلید") || aiError.includes("سهمیه")) && (
              <div className="flex flex-wrap gap-2 pt-1">
                <button onClick={() => setShowKeyInput(true)} className="flex items-center gap-0.5 text-[9px] text-red-400 underline hover:text-red-300">
                  <Globe className="h-2.5 w-2.5" /> تغییر کلید
                </button>
                <button onClick={() => setShowChatServices(true)} className="flex items-center gap-0.5 text-[9px] text-purple-400 underline hover:text-purple-300">
                  <Bot className="h-2.5 w-2.5" /> استفاده از روش کپی داده
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {aiResult && (
        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Bot className="h-3.5 w-3.5 text-yellow-500" />
            <span className="text-[10px] font-bold text-yellow-500">تحلیل هوش مصنوعی:</span>
          </div>
          <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed">{aiResult}</pre>
        </div>
      )}
    </div>
  );
}