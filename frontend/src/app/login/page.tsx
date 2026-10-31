"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, setUser, getToken, getUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, useInView } from "framer-motion";
import { 
  ArrowLeft, 
  ShieldCheck, 
  Zap, 
  Brain, 
  Globe, 
  Send, 
  Activity, 
  CheckCircle2, 
  Cpu, 
  TrendingUp, 
  Key
} from "lucide-react";

// ═══════════════════════════════════════════════════════════
// 🔴 کامپوننت شمارنده پویا (Count-up)
// ═══════════════════════════════════════════════════════════
function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (!isInView) return;
    
    let start = 0;
    const duration = 1500; // مدت زمان انیمیشن (میلی‌ثانیه)
    const steps = 50;
    const stepTime = duration / steps;
    const increment = value / steps;

    const timer = setInterval(() => {
      start += increment;
      if (start >= value) {
        setCount(value);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [value, isInView]);

  return <span ref={ref} className="num">{count}{suffix}</span>;
}

// 🔴 آمار (با مقادیر عددی برای انیمیشن)
const STATS = [
  { label: "اندیکاتور تکنیکال", value: 32, suffix: "+" }, // ← عدد هدف را اینجا تغییر بده
  { label: "صرافی متصل", value: 5, suffix: "" }, // ← عدد هدف را اینجا تغییر بده
  { label: "دقت پیش‌بینی جهت", value: 78, suffix: "٪" }, // ← عدد هدف را اینجا تغییر بده
  { label: "دقت رسیدن به هدف", value: 62, suffix: "٪" }, // ← عدد هدف را اینجا تغییر بده
];

// 🔴 قابلیت‌ها
const FEATURES = [
  { icon: Zap, title: "تحلیل جامع بازار", desc: "موتور تحلیل با ۳۲ اندیکاتور تکنیکال حرفه‌ای" },
  { icon: Cpu, title: "هوش مصنوعی", desc: "تحلیل عمیق داده‌ها با هوش مصنوعی" },
  { icon: Key, title: "API شخصی", desc: "اتصال کلید هوش مصنوعی شخصی خودت" },
  { icon: ShieldCheck, title: "مدیریت ریسک", desc: "حد ضرر و هدف هوشمند بر اساس نوسان بازار" },
  { icon: Activity, title: "هشدار تله‌ها", desc: "تشخیص تله‌های صعودی، نزولی و شکست‌های جعلی" },
  { icon: TrendingUp, title: "مقایسه صرافی‌ها", desc: "اولین سایت مقایسه لحظه‌ای صرافی‌های ایرانی" },
];

// 🔴 لیست لوگوها (فعال و غیرفعال)
const EXCHANGES = [
  { name: "نوبیتکس", logo: "/logos/nobitex.png", active: true },
  { name: "بیت‌پین", logo: "/logos/bitpin.png", active: true },
  { name: "والکس", logo: "/logos/wallex.png", active: true },
  { name: "تبدیل", logo: "/logos/tabdeal.png", active: true },
  { name: "بورس تهران", logo: "/logos/tsetmc.png", active: true },
  { name: "رمزینکس", logo: "/logos/ramzinex.png", active: false },
  { name: "توبیت", logo: "/logos/toobit.png", active: false },
  { name: "بینگ‌ایکس", logo: "/logos/bingx.png", active: false },
  { name: "بیت۲۴", logo: "/logos/bit24.png", active: false },
  { name: "آبان‌تتر", logo: "/logos/abantether.png", active: false },
];

export default function LoginPage() {
  const router = useRouter();
  
  useEffect(() => {
    const token = getToken();
    const user = getUser();
    if (token && user) {
      router.replace("/");
    }
  }, [router]);

  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(0);
  
  const [floatingSignals, setFloatingSignals] = useState<any[]>([]);
  const [candleHeights, setCandleHeights] = useState<any[]>([]);
  
  const codeInputs = useRef<(HTMLInputElement | null)[]>([]);
  const [codeDigits, setCodeDigits] = useState(["", "", "", "", ""]);

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
  }, []);

  useEffect(() => {
    if (timer > 0) {
      const t = setTimeout(() => setTimer(timer - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [timer]);

  const handleSendOtp = async () => {
    if (!phone || phone.length < 11) return setError("لطفاً شماره موبایل خود را به درستی وارد کنید.");
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
        throw new Error(data.detail || "خطا در ارسال کد تایید.");
      }
      
      setStep(2);
      setTimer(120);
      setTimeout(() => codeInputs.current[0]?.focus(), 100);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const fullCode = codeDigits.join("");
    if (fullCode.length < 5) return setError("لطفاً کد ۵ رقمی ارسال شده را کامل وارد کنید.");
    
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code: fullCode }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "کد وارد شده نامعتبر است.");

      setToken(data.access_token);
      setUser(data.user);
      
      if (data.user?.is_new) {
        router.push("/dashboard?welcome=true");
      } else {
        router.push("/");
      }
      
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

  const handleCodeChange = (index: number, value: string) => {
    if (isNaN(Number(value))) return;
    const newDigits = [...codeDigits];
    newDigits[index] = value.substring(value.length - 1);
    setCodeDigits(newDigits);

    if (value && index < 4) {
      codeInputs.current[index + 1]?.focus();
    }
    
    if (newDigits.every(d => d !== "") && index === 4) {
      setTimeout(() => {
        const form = document.querySelector("form");
        if (form) form.requestSubmit();
      }, 100);
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !codeDigits[index] && index > 0) {
      codeInputs.current[index - 1]?.focus();
    }
  };

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#07111f] text-white">
      
      {/* 🔴 سئو: تگ H1 پنهان */}
      <div className="hidden">
        <h1>تحلیل تکنیکال، سیگنال هوش مصنوعی و مقایسه صرافی‌های ایرانی | تریدمون</h1>
        <p>اولین سایت تحلیل رباتیک کریپتو و بورس ایران با هوش مصنوعی و مقایسه لحظه‌ای قیمت صرافی‌ها</p>
      </div>

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

        <div className="absolute inset-0 bg-gradient-to-br from-[#07111f]/80 via-[#07111f]/60 to-[#07111f]/95" />
      </div>

      {/* هدر — 🔴 نئون لوگو حذف شد */}
      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img src="/icon-512.png" alt="Trademun" className="h-14 w-auto sm:h-16 rounded-xl object-contain" />
        </Link>
        <div className="flex items-center gap-2 text-xs text-gray-400 bg-white/5 py-1 px-3 rounded-full border border-white/10">
          <div className="h-2 w-2 animate-pulse rounded-full bg-[#10b981]" />
          دستیار هوشمند بازار
        </div>
      </header>

      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center gap-8 p-4 py-8 sm:p-6 lg:flex-row lg:items-center lg:justify-between lg:pt-16">
        
        {/* ═══ بخش تبلیغاتی (سمت چپ) ═══ */}
        <div className="flex w-full flex-col items-center lg:items-start lg:w-1/2 text-center lg:text-right">
          
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-yellow-500/30 bg-yellow-500/10 px-4 py-1.5 text-xs font-medium text-yellow-500">
            <ShieldCheck className="h-4 w-4" />
            شفافیت کامل در آمار و مدیریت ریسک
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight mt-2">
            تحلیل بازارهای مالی<br />
            <span className="text-[#d6ad60]">با تریدمون</span>
          </h1>
          
          <p className="mt-4 max-w-lg text-sm leading-relaxed text-gray-400">
            تریدمون به شما کمک می‌کند تا با تحلیل‌های رباتیک و هوش مصنوعی، بهترین تصمیم را در بازار کریپتو و بورس ایران بگیرید. همچنین می‌توانید قیمت‌ها را بین صرافی‌های مختلف مقایسه کنید.
          </p>

          {/* 🔴 آمار زنده با انیمیشن شمارنده */}
          <div className="mt-6 grid w-full max-w-lg grid-cols-2 gap-3 sm:grid-cols-4">
            {STATS.map((stat, i) => (
              <div key={i} className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-white/5 py-2 backdrop-blur-md">
                <span className="text-lg font-bold text-[#d6ad60]">
                  <AnimatedNumber value={stat.value} suffix={stat.suffix} />
                </span>
                <span className="text-[9px] text-gray-400 mt-1 text-center">{stat.label}</span>
              </div>
            ))}
          </div>

          {/* 🔴 کارت‌های قابلیت */}
          <div className="mt-8 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
            {FEATURES.map((f, i) => (
              <div key={i} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-md transition-colors hover:bg-white/10">
                <div className="rounded-lg bg-[#d6ad60]/15 p-2">
                  <f.icon className="h-4 w-4 text-[#d6ad60]" />
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-white">{f.title}</p>
                  <p className="text-[10px] text-gray-400 mt-0.5 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* 🔴 لوگوی صرافی‌ها — فقط در دسکتاپ */}
          <div className="mt-8 w-full max-w-lg hidden lg:block">
            <p className="text-[10px] text-gray-400 mb-3 text-right">پشتیبانی از صرافی‌های معتبر و در آینده نزدیک</p>
            <div className="flex flex-wrap items-center justify-start gap-2">
              {EXCHANGES.map((ex, i) => (
                <div key={i} className={`flex flex-col items-center gap-1 ${!ex.active ? "opacity-40" : ""}`}>
                  <div className={`h-8 w-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden p-1 ${!ex.active ? "grayscale" : ""}`}>
                    <img src={ex.logo} alt={ex.name} className="h-full w-full object-contain" onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                      const parent = (e.target as HTMLImageElement).parentElement;
                      if (parent && !parent.querySelector('.fallback-text')) {
                        const span = document.createElement('span');
                        span.className = 'fallback-text text-[7px] text-gray-300 font-bold';
                        span.innerText = ex.name.substring(0, 2);
                        parent.appendChild(span);
                      }
                    }} />
                  </div>
                  <span className="text-[7px] text-gray-400">{ex.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ فرم ورود (سمت راست) ═══ */}
        <div className="relative w-full max-w-sm lg:w-[400px] lg:sticky lg:top-24">
          
          <form onSubmit={handleVerify} className="relative w-full rounded-3xl border border-white/10 bg-[#0d1b2dd0] p-6 shadow-[0_0_40px_rgba(214,173,96,0.1)] backdrop-blur-2xl">
            
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-1 text-white">ورود به تریدمون</h2>
              <p className="text-xs text-gray-400">
                {step === 1 ? "برای ادامه، شماره موبایلت را وارد کن." : `کد ارسال شده به ${phone} را وارد کن.`}
              </p>
            </div>

            {error && <div className="mb-4 rounded-lg bg-red-500/10 p-3 text-xs text-red-500">{error}</div>}

            {step === 1 ? (
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">شماره موبایل</label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60] focus-within:shadow-[0_0_10px_rgba(214,173,96,0.2)]">
                    <Input
                      type="tel"
                      placeholder="0912 000 0000"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      onKeyDown={handleKeyDown}
                      className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12"
                      maxLength={11}
                      dir="ltr"
                    />
                  </div>
                </div>
                
                <Button onClick={handleSendOtp} disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)] transition-all">
                  {loading ? "در حال ارسال..." : "دریافت کد ورود"}
                </Button>
                
                <div className="text-center mt-2">
                  <p className="text-[10px] text-[#d6ad60] bg-[#d6ad60]/10 rounded-md py-1.5 inline-block px-3 border border-[#d6ad60]/20">
                    🎁 با اولین ورود، ۳ روز اشتراک رایگان هدیه بگیر!
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-xs font-medium text-gray-400">کد تایید</label>
                    <button type="button" onClick={() => setStep(1)} className="flex items-center gap-1 text-xs text-[#d6ad60] hover:underline">
                      ویرایش شماره <ArrowLeft className="h-3 w-3" />
                    </button>
                  </div>
                  
                  <div className="flex justify-between gap-2" dir="ltr">
                    {codeDigits.map((digit, index) => (
                      <Input
                        key={index}
                        ref={(el) => { codeInputs.current[index] = el; }}
                        type="text"
                        inputMode="numeric"
                        value={digit}
                        onChange={(e) => handleCodeChange(index, e.target.value)}
                        onKeyDown={(e) => handleCodeKeyDown(index, e)}
                        className="h-14 w-12 rounded-xl text-center text-xl font-bold bg-black/40 border-white/10 text-white focus-visible:ring-[#d6ad60] transition-all"
                        maxLength={1}
                        autoComplete="one-time-code"
                      />
                    ))}
                  </div>
                </div>
                
                <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)] transition-all">
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

          <div className="mt-5 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-center">
            <p className="text-[10px] text-yellow-500/80 leading-relaxed">
              ⚠️ تحلیل‌های تریدمون صرفاً جنبه آموزشی دارند. تصمیم نهایی و مسئولیت سود یا ضرر با خودتونه.
            </p>
          </div>

          <div className="mt-6 flex items-center justify-center gap-6 opacity-80">
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="rounded-lg border border-[#10b981] bg-[#10b981]/10 px-6 py-1.5 text-sm font-bold text-[#10b981] shadow-[0_0_20px_#10b98140]"
            >
              LONG
            </motion.div>
            <motion.div
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="rounded-lg border border-[#ef4444] bg-[#ef4444]/10 px-6 py-1.5 text-sm font-bold text-[#ef4444] shadow-[0_0_20px_#ef444440]"
            >
              SHORT
            </motion.div>
          </div>

        </div>
      </div>

      {/* 🔴 لوگوی صرافی‌ها — فقط در موبایل (زیر LONG/SHORT) */}
      <div className="relative z-10 w-full px-4 pb-8 lg:hidden">
        <p className="text-[10px] text-gray-400 mb-3 text-center">پشتیبانی از صرافی‌های معتبر</p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {EXCHANGES.map((ex, i) => (
            <div key={i} className={`flex flex-col items-center gap-1 ${!ex.active ? "opacity-40" : ""}`}>
              <div className={`h-8 w-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden p-1 ${!ex.active ? "grayscale" : ""}`}>
                <img src={ex.logo} alt={ex.name} className="h-full w-full object-contain" onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  const parent = (e.target as HTMLImageElement).parentElement;
                  if (parent && !parent.querySelector('.fallback-text')) {
                    const span = document.createElement('span');
                    span.className = 'fallback-text text-[7px] text-gray-300 font-bold';
                    span.innerText = ex.name.substring(0, 2);
                    parent.appendChild(span);
                  }
                }} />
              </div>
              <span className="text-[7px] text-gray-400">{ex.name}</span>
            </div>
          ))}
        </div>
      </div>

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
      </footer>
    </main>
  );
}