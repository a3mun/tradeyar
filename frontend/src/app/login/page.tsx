"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, setUser, getToken, getUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ShieldCheck, Zap, Brain, Globe, Send } from "lucide-react";

type Signal = { id: number; x: number; y: number; duration: number; delay: number; size: number };
type Candle = { id: number; start: number; peak: number; color: string; };

const FEATURES = [
  { icon: Zap, text: "تحلیل ۵ گروهی با ۲۰+ اندیکاتور" },
  { icon: ShieldCheck, text: "سیستم مدیریت ریسک و هشدار تله‌ها" },
  { icon: Brain, text: "تحلیل عمیق و هوش مصنوعی" },
];

export default function LoginPage() {
  const router = useRouter();
  
  // ⬅️ اگه کاربر لاگین‌کرده، نفرستش /login — بفرستش صفحه اصلی
  useEffect(() => {
    const token = getToken();
    const user = getUser();
    if (token && user) {
      router.replace("/");
    }
  }, [router]);

  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(0);
  
  const [activeFeature, setActiveFeature] = useState(0);

  const [floatingSignals, setFloatingSignals] = useState<Signal[]>([]);
  const [candleHeights, setCandleHeights] = useState<Candle[]>([]);

  useEffect(() => {
    setCandleHeights(
      Array.from({ length: 15 }).map((_, i) => ({
        id: i,
        start: 20 + (i * 7) % 40,
        peak: 50 + (i * 11) % 40,
        color: i % 2 === 0 ? "bg-[#10b981]" : "bg-[#ef4444]",
      }))
    );

    setFloatingSignals(
      Array.from({ length: 10 }).map((_, i) => ({
        id: i,
        x: -100,
        y: Math.random() * 800,
        duration: 10 + Math.random() * 8,
        delay: Math.random() * 5,
        size: 2 + Math.random() * 1.5,
      }))
    );

    const featureInterval = setInterval(() => {
      setActiveFeature((prev) => (prev + 1) % FEATURES.length);
    }, 4000);

    return () => clearInterval(featureInterval);
  }, []);

  useEffect(() => {
    if (timer > 0) {
      const t = setTimeout(() => setTimer(timer - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [timer]);

  const handleSendOtp = async () => {
    if (!phone || phone.length < 11) return setError("شماره موبایل نامعتبر است");
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "خطا در ارسال کد");
      }
      
      setStep(2);
      setTimer(120);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length < 5) return setError("کد ۵ رقمی را وارد کنید");
    
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "کد نامعتبر است");

      setToken(data.access_token);
      setUser(data.user);
      
      // ⬅️ همه به صفحه اصلی برن (ادمین هم می‌تونه از منو بره پنل)
      router.push("/");
      
    } catch (err: any) {
      setError(err.message);
      setLoading(false); 
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && step === 1) {
      e.preventDefault();
      handleSendOtp();
    }
  };

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#07111f] text-white">
      
      {/* ═══ پس‌زمینه سینمایی ═══ */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <svg className="absolute inset-0 h-full w-full opacity-70" viewBox="0 0 1200 800" preserveAspectRatio="none">
          <motion.path
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.6 }}
            transition={{ duration: 8, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
            d="M-30 580 C100 520 120 620 230 500 S360 560 450 420 S590 490 690 320 S840 390 920 250 S1080 300 1240 110"
            fill="none"
            stroke="#d6ad60"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>

        <div className="absolute inset-0 flex items-end justify-around gap-1 px-2 opacity-40">
          {candleHeights.map((candle) => (
            <motion.div
              key={candle.id}
              initial={{ height: `${candle.start}%`, opacity: 0.4 }}
              animate={{ height: [`${candle.start}%`, `${candle.peak}%`, `${candle.start}%`] }}
              transition={{ duration: 5 + (candle.id % 3), repeat: Infinity, ease: "easeInOut", delay: candle.id * 0.1 }}
              className={`w-3 sm:w-4 rounded-t-sm ${candle.color}`}
            />
          ))}
        </div>

        {floatingSignals.map((signal) => (
          <motion.div
            key={`signal-${signal.id}`}
            initial={{ x: signal.x, y: signal.y, opacity: 0 }}
            animate={{ 
              x: 1200, 
              y: [signal.y, signal.y + 30, signal.y - 30, signal.y],
              opacity: [0, 0.7, 0], 
              scale: [1, 1.3, 1] 
            }}
            transition={{ duration: signal.duration, repeat: Infinity, ease: "linear", delay: signal.delay }}
            className="absolute rounded-full bg-[#d6ad60] shadow-[0_0_15px_#d6ad60]"
            style={{ width: `${signal.size * 4}px`, height: `${signal.size * 4}px` }}
          />
        ))}

        <div className="absolute inset-0 bg-gradient-to-br from-[#07111f]/60 via-[#07111f]/40 to-[#07111f]/80" />
      </div>

      {/* هدر — ⬅️ فقط لوگو، بدون متن اضافی */}
      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img src="/icon-512.png" alt="Trademun" className="h-12 w-auto rounded-xl object-contain" />
        </Link>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <div className="h-2 w-2 animate-pulse rounded-full bg-[#10b981]" />
          دستیار هوشمند بازار
        </div>
      </header>

      <div className="relative z-10 mx-auto grid w-full max-w-5xl flex-1 items-center gap-8 p-4 sm:p-6 lg:grid-cols-2">
        
        {/* ═══ دسکتاپ: متن معرفی ═══ */}
        <div className="hidden lg:block">
          <span className="text-xs tracking-widest text-[#d6ad60]">SMARTER MARKET INSIGHTS</span>
          <h1 className="mt-6 text-5xl font-bold leading-tight">
            تحلیل بازارهای مالی<br />
            <span className="text-[#d6ad60]">با تریدمون</span>
          </h1>
          <p className="mt-6 text-sm leading-relaxed text-gray-400">
            با تریدمون، تحلیل تکنیکال دقیق و سیگنال‌های لحظه‌ای رو از صرافی‌های معتبر و بازار سرمایه ایران (بورس) دریافت کن. تصمیم بهتر، با دید بهتر.
          </p>
          <div className="mt-8 space-y-3 text-sm">
            {FEATURES.map((f, i) => (
              <div key={i} className="flex items-center gap-3">
                <f.icon className="h-4 w-4 text-[#d6ad60]" />
                <span>{f.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ فرم ورود ═══ */}
        <div className="relative w-full">
          
          {/* موبایل: متن معرفی */}
          <div className="mb-6 text-center lg:hidden">
            <h1 className="text-2xl font-bold leading-tight">
              تحلیل بازارهای مالی
            </h1>
          </div>

          {/* نوتیف (بالای فرم) */}
          <div className="mb-4 flex justify-center lg:hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeFeature}
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.5 }}
                className="flex items-center gap-2 rounded-full border border-[#d6ad6040] bg-[#0d1b2de0] px-4 py-2 text-xs text-[#d6ad60] shadow-lg backdrop-blur-md"
              >
                {(() => {
                  const Icon = FEATURES[activeFeature].icon;
                  return <Icon className="h-4 w-4" />;
                })()}
                <span>{FEATURES[activeFeature].text}</span>
              </motion.div>
            </AnimatePresence>
          </div>

          <form onSubmit={handleVerify} className="relative w-full rounded-2xl border border-white/10 bg-[#0d1b2dd0] p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
            
            <h2 className="text-xl font-bold mb-1">ورود به تریدمون</h2>
            <p className="mb-6 text-xs text-gray-400">
              {step === 1 ? "برای ادامه، شماره موبایلت را وارد کن." : `کد ارسال شده به ${phone} را وارد کن.`}
            </p>

            {error && <div className="mb-4 rounded-lg bg-red-500/10 p-3 text-xs text-red-500">{error}</div>}

            {step === 1 ? (
              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-xs text-gray-400">شماره موبایل</label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/30 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <span className="text-sm text-[#d6ad60] pl-3 border-r border-white/10" dir="ltr">+98</span>
                    <Input
                      type="tel"
                      placeholder="0912 000 0000"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      onKeyDown={handleKeyDown}
                      className="border-0 bg-transparent text-right text-base text-white shadow-none focus-visible:ring-0 h-11"
                      maxLength={11}
                      dir="ltr"
                    />
                  </div>
                </div>
                
                <Button onClick={handleSendOtp} disabled={loading} className="h-11 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] hover:opacity-90">
                  {loading ? "در حال ارسال..." : "دریافت کد ورود"}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-xs text-gray-400">کد تایید</label>
                    <button type="button" onClick={() => setStep(1)} className="flex items-center gap-1 text-xs text-[#d6ad60] hover:underline">
                      ویرایش شماره <ArrowLeft className="h-3 w-3" />
                    </button>
                  </div>
                  <Input
                    type="text"
                    placeholder="- - - - -"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="h-12 border-white/10 bg-black/30 text-center text-xl tracking-[0.5em] text-white focus-visible:ring-[#d6ad60]"
                    maxLength={5}
                    dir="ltr"
                  />
                </div>
                
                <Button type="submit" disabled={loading} className="h-11 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] hover:opacity-90">
                  {loading ? "در حال بررسی..." : "ورود به حساب"}
                </Button>
                
                <div className="text-center text-xs">
                  {timer > 0 ? (
                    <span className="text-gray-500">ارسال مجدد در {Math.floor(timer/60)}:{String(timer%60).padStart(2,'0')}</span>
                  ) : (
                    <button type="button" onClick={handleSendOtp} className="text-[#d6ad60] hover:underline">ارسال مجدد کد</button>
                  )}
                </div>
              </div>
            )}
          </form>

          {/* ⬅️ LONG/SHORT زیر کارت (دسکتاپ و موبایل) */}
          <div className="mt-6 flex items-center justify-center gap-8 opacity-80">
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="rounded-lg border border-[#10b981] bg-[#10b981]/10 px-6 py-2 text-sm font-bold text-[#10b981] shadow-[0_0_20px_#10b98140]"
            >
              LONG
            </motion.div>
            <motion.div
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="rounded-lg border border-[#ef4444] bg-[#ef4444]/10 px-6 py-2 text-sm font-bold text-[#ef4444] shadow-[0_0_20px_#ef444440]"
            >
              SHORT
            </motion.div>
          </div>

          {/* ⬅️ موبایل: متن جذاب زیر فرم */}
          <div className="mt-6 text-center lg:hidden">
            <p className="text-xs text-gray-400 leading-relaxed">
              با تریدمون، تحلیل تکنیکال دقیق و سیگنال‌های لحظه‌ای رو از صرافی‌های معتبر و بازار سرمایه ایران (بورس) دریافت کن. تصمیم بهتر، با دید بهتر.
            </p>
          </div>
        </div>
      </div>

      {/* فوتر */}
      <footer className="relative z-10 border-t border-white/5 bg-[#07111f]/50 px-4 py-3 text-center text-[10px] text-gray-500 backdrop-blur-sm sm:px-6">
        <div className="flex flex-wrap items-center justify-center gap-4">
          <span>© 2026 تریدمون</span>
          <span className="hidden sm:inline">•</span>
          <span>دستیار هوشمند بازارهای مالی</span>
          <span className="hidden sm:inline">•</span>
          <a href="https://trademun.ir" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-[#d6ad60] transition-colors">
            <Globe className="h-3 w-3" /> trademun.ir
          </a>
          <a href="https://t.me/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-[#d6ad60] transition-colors">
            <Send className="h-3 w-3" /> t.me/trademun
          </a>
          <a href="https://ble.ir/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-[#d6ad60] transition-colors">
            <Send className="h-3 w-3" /> ble.ir/trademun
          </a>
        </div>
        <p className="mt-1 text-[9px] opacity-70">
          ⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارند.
        </p>
      </footer>
    </main>
  );
}