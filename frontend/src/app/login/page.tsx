"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, setUser, getToken, getUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, useInView } from "framer-motion";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { AlertTriangle, ArrowLeft, ArrowLeftRight, BarChart3, Brain, Check, CreditCard, Filter, Globe, Layers, Target, Zap } from "lucide-react";

// 🔴 SEO: اضافه کردن اسکیمای FAQ برای ریچ‌اسنیپت
const FAQ_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "تریدمون چیست و چه کاربردی دارد؟",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "تریدمون یک دستیار هوشمند تحلیل بازارهای مالی است که با ۳۲ اندیکاتور تکنیکال، سه استراتژی معاملاتی و مشاور هوش مصنوعی، به شما در تحلیل کریپتو، فارکس و بورس کمک می‌کند."
      }
    },
    {
      "@type": "Question",
      "name": "آیا استفاده از تریدمون رایگان است؟",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "با اولین ورود، ۳ روز اشتراک رایگان هدیه می‌گیرید. برای ادامه استفاده، می‌توانید یکی از پلن‌های اشتراک را از صفحه پلن‌ها تهیه کنید."
      }
    },
    {
      "@type": "Question",
      "name": "تریدمون از چه صرافی‌هایی پشتیبانی می‌کند؟",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "تریدمون از نوبیتکس، بیت‌پین، والکس، تبدیل، بورس تهران و بازار فارکس (طلا، نفت، شاخص‌ها) پشتیبانی می‌کند. همچنین افزونه اختصاصی کروم برای تحلیل انس طلا (XAU/USD) در دریا گلد و آلفا گلد ارائه شده است."
      }
    }
  ]
};

function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (!isInView) return;
    let start = 0;
    const duration = 1500;
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

  return (
    <span ref={ref} className="num">
      {count}
      {suffix}
    </span>
  );
}

const STATS = [
  { label: "اندیکاتور تکنیکال", value: 32, suffix: "" },
  { label: "صرافی", value: 6, suffix: "" },
  { label: "دقت پیش‌بینی", value: 78, suffix: "٪" },
  { label: "دقت به هدف", value: 62, suffix: "٪" },
];

const FEATURES = [
  { icon: Brain, title: "مشاور هوشمند AI", desc: "تحلیل لحظه‌ای با هوش مصنوعی" },
  { icon: Filter, title: "اسکنر فرصت‌ها", desc: "پیدا کردن پرسودترین نمادها" },
  { icon: Zap, title: "سه استراتژی", desc: "اسکالپ، سوئینگ، پوزیشن" },
  { icon: Target, title: "دو پروفایل ریسک", desc: "جسورانه و محتاطانه" },
  { icon: Layers, title: "اسپات و فیوچرز", desc: "پشتیبانی از هر دو بازار" },
  { icon: Globe, title: "افزونه کروم", desc: "تحلیل زنده XAU/USD" },
  { icon: ArrowLeftRight, title: "مقایسه صرافی‌ها", desc: "مقایسه قیمت ۴ صرافی ایرانی" },
  { icon: BarChart3, title: "بورس تهران", desc: "تحلیل سهام و صندوق‌ها" },
  { icon: AlertTriangle, title: "هشدار تله‌ها", desc: "تشخیص تله و شکست جعلی" },
  { icon: Check, title: "راستی‌آزمایی", desc: "ارزیابی مستمر سیگنال‌ها" },
];

const EXCHANGES_MAJOR = [
  { name: "نوبیتکس", logo: "/logos/nobitex.png" },
  { name: "بیت‌پین", logo: "/logos/bitpin.png" },
  { name: "والکس", logo: "/logos/wallex.png" },
  { name: "تبدیل", logo: "/logos/tabdeal.png" },
  { name: "بورس تهران", logo: "/logos/tsetmc.png" },
  { name: "فارکس", logo: "/logos/biquote.png" },
];

const EXCHANGES_COMING_SOON = [
  { name: "رمزینکس", logo: "/logos/ramzinex.png", removed: false },
  { name: "توبیت", logo: "/logos/toobit.png", removed: false },
  { name: "بینگ‌ایکس", logo: "/logos/bingx.png", removed: false },
  { name: "بیت۲۴", logo: "/logos/bit24.png", removed: false },
  { name: "آبان‌تتر", logo: "/logos/abantether.png", removed: true },
];

const EXCHANGES_GOLD = [
  { name: "آلفا گلد", logo: "/logos/alfagold.png" },
  { name: "دریا گلد", logo: "/logos/daryagold.png" },
];

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    const user = getUser();
    if (token && user) router.replace("/");
  }, [router]);

  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(0);

  const [loginMode, setLoginMode] = useState<"otp" | "password">("otp");
  const [password, setPassword] = useState("");

  const [candleHeights, setCandleHeights] = useState<any[]>([]);

  const codeInputs = useRef<(HTMLInputElement | null)[]>([]);
  const [codeDigits, setCodeDigits] = useState(["", "", "", "", ""]);

  // 🔴 تنظیم کندل‌های پس‌زمینه (کمتر و پهن‌تر)
  useEffect(() => {
    setCandleHeights(
      Array.from({ length: 7 }).map((_, i) => ({
        id: i,
        base: 15 + Math.random() * 35,
        peak: 40 + Math.random() * 50,
        color: i % 2 === 0 ? "bg-[#10b981]/30" : "bg-[#ef4444]/30",
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
    if (!phone || phone.length < 11)
      return setError("لطفاً شماره موبایل خود را به درستی وارد کنید.");
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

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    const fullCode = codeDigits.join("");
    if (fullCode.length < 5)
      return setError("لطفاً کد ۵ رقمی ارسال شده را کامل وارد کنید.");
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
      router.push(data.user?.is_new ? "/dashboard?welcome=true" : "/");
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || phone.length < 11)
      return setError("شماره موبایل را درست وارد کنید.");
    if (!password || password.length < 6)
      return setError("رمز عبور باید حداقل ۶ حرف باشد.");
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "شماره یا رمز عبور اشتباه است.");
      setToken(data.access_token);
      setUser(data.user);
      router.push(data.user?.is_new ? "/dashboard?welcome=true" : "/");
    } catch (err: any) {
      setError(err.message);
    } finally {
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
    if (value && index < 4) codeInputs.current[index + 1]?.focus();
    if (newDigits.every((d) => d !== "") && index === 4) {
      setTimeout(() => {
        const form = document.querySelector("form");
        if (form) form.requestSubmit();
      }, 100);
    }
  };

  const handleCodeKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !codeDigits[index] && index > 0)
      codeInputs.current[index - 1]?.focus();
  };

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#030712] text-white">
      {/* 🔴 SEO: اسکیمای FAQ */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_SCHEMA) }}
      />

      {/* 🔴 سئو مخفی */}
      <div className="sr-only" aria-hidden="true">
        <h1>تحلیل بازارهای مالی با تریدمون — معامله هوشمند، از اینجا شروع می‌شه! تریدمون نشه؟</h1>
        <h2>تریدمون: تحلیل تکنیکال حرفه‌ای با ۳۲ اندیکاتور، ۳ استراتژی معاملاتی, مشاور AI، اسکنر بازار و مقایسه صرافی‌های ایرانی</h2>
        <p>با ورود به تریدمون، به موتور تحلیل حرفه‌ای با ۳۲ اندیکاتور تکنیکال دسترسی پیدا می‌کنید. سه استراتژی معاملاتی (اسکالپ، سوئینگ، پوزیشن), مشاور هوشمند با AI و دسترسی به داده‌های خام، اسکنر فرصت‌ها، مقایسه لحظه‌ای قیمت صرافی‌های ایرانی (نوبیتکس، بیت‌پین، والکس، تبدیل) و بررسی بازار فارکس و کالا (طلا، نقره، نفت)، تحلیل اختصاصی انس طلا (XAU/USD) از طریق افزونه کروم، مدیریت ریسک هوشمند، چک‌لیست معاملاتی، سناریوهای پیش‌بینی بازار، راستی‌آزمایی خودکار سیگنال، شاخص ترس و طمع، عمق بازار و پروفایل ریسک شخصی‌سازی شده. ۳ روز رایگان با اولین ورود.</p>
      </div>

      {/* 🔴 پس‌زمینه انیمیشن (نمودار شمعی و خط طلایی) */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <svg className="absolute inset-0 h-full w-full opacity-60" viewBox="0 0 1200 800" preserveAspectRatio="none">
          <motion.path
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.4 }}
            transition={{ duration: 10, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
            d="M-30 580 C100 520 120 620 230 500 S360 560 450 420 S590 490 690 320 S840 390 920 250 S1080 300 1240 110"
            fill="none"
            stroke="#d6ad60"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>

        <div className="absolute inset-0 flex items-end justify-around gap-1 px-2 opacity-30">
          {candleHeights.map((candle) => (
            <motion.div
              key={candle.id}
              initial={{ height: `${candle.base}%` }}
              animate={{ height: [`${candle.base}%`, `${candle.peak}%`, `${candle.base}%`] }}
              transition={{ duration: 4 + (candle.id % 5), repeat: Infinity, ease: "easeInOut", delay: candle.id * 0.1 }}
              className={`w-9 sm:w-12 rounded-t-sm ${candle.color}`}
            />
          ))}
        </div>

        <div className="absolute inset-0 bg-gradient-to-br from-[#030712]/80 via-[#030712]/60 to-[#030712]/95" />
      </div>

      {/* هدر (لوگو وسط‌چین) */}
      <header className="relative z-10 flex items-center justify-center p-4 sm:p-6">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img src="/icon-512-login.png" alt="Trademun" className="h-14 w-auto sm:h-16 rounded-xl object-contain" />
        </Link>
      </header>

      {/* تیتر وسط‌چین */}
      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col items-center px-4 pt-4 pb-8 text-center">
        <h1 className="font-display font-bold leading-tight tracking-tight">
          <span className="block text-3xl sm:text-4xl lg:text-5xl text-white">تحلیل بازارهای مالی</span>
          <span className="mt-2 block text-lg sm:text-xl lg:text-2xl font-medium">
            <span className="text-white">معامله هوشمند، از اینجا شروع می‌شه!</span>{" "}
            <span className="text-[#d6ad60]">تریدمون نشه؟</span>
          </span>
        </h1>
      </div>

      {/* 🔴 بخش اصلی: دو ستونه (ویژگی‌ها + فرم) */}
      {/* 🔴 تغییر: items-stretch به items-start تغییر کرد تا ستون‌ها مستقل بشن */}
      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col items-start gap-8 p-4 py-4 sm:p-6 lg:flex-row lg:justify-between">
        
        {/* ستون چپ (ویژگی‌ها + آمار) */}
        <div className="flex w-full flex-col lg:w-1/2 gap-4">
          {/* آمار */}
          <div className="grid w-full grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-2.5">
            {STATS.map((stat, i) => (
              <div key={i} className="flex h-full flex-col items-center justify-center rounded-xl border border-white/10 bg-[#051118]/80 backdrop-blur-sm py-2.5">
                <span className="text-lg font-bold text-[#d6ad60] leading-none">
                  <AnimatedNumber value={stat.value} suffix={stat.suffix} />
                </span>
                <span className="text-[9px] text-gray-400 mt-1.5 text-center leading-tight">{stat.label}</span>
              </div>
            ))}
          </div>

          {/* ۱۰ ویژگی */}
          <div className="grid grid-cols-2 gap-2 sm:gap-2.5 flex-1" dir="rtl">
            {FEATURES.map((f, i) => (
              <div key={i} className="group flex items-start gap-2 rounded-xl border border-white/10 bg-[#051118]/80 backdrop-blur-sm p-2 transition-all hover:border-[#d6ad60]/40 hover:bg-white/[0.03] sm:gap-2.5 sm:p-3 h-full">
                <div className="shrink-0 rounded-lg bg-[#d6ad60]/15 p-1.5">
                  <f.icon className="h-3.5 w-3.5 text-[#d6ad60]" />
                </div>
                <div className="text-right min-w-0 flex-1">
                  <p className="text-[10.5px] sm:text-xs font-bold text-white leading-tight">{f.title}</p>
                  <p className="text-[8.5px] sm:text-[10px] text-gray-400 mt-0.5 leading-snug line-clamp-2">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ستون راست (فرم ورود + پلن + هشدار) */}
        <div className="relative w-full max-w-sm lg:w-[400px] flex flex-col gap-3">
          <div className="flex gap-1 p-1 bg-[#051118]/80 backdrop-blur-sm border border-white/10 rounded-xl">
            <button onClick={() => { setLoginMode("otp"); setError(""); }}
              className={`flex-1 h-9 rounded-lg text-xs font-bold transition-all ${loginMode === "otp" ? "bg-[#d6ad60] text-[#051118]" : "text-gray-400 hover:text-white"}`}>
              ورود پیامکی
            </button>
            <button onClick={() => { setLoginMode("password"); setError(""); }}
              className={`flex-1 h-9 rounded-lg text-xs font-bold transition-all ${loginMode === "password" ? "bg-[#d6ad60] text-[#051118]" : "text-gray-400 hover:text-white"}`}>
             ورود با رمز
            </button>
          </div>

          <form onSubmit={loginMode === "password" ? handlePasswordLogin : handleVerifyOtp} className="relative w-full rounded-2xl border border-[#d6ad60]/30 bg-[#051118]/80 backdrop-blur-sm p-6 shadow-[0_8px_40px_rgba(0,0,0,0.6)]">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-1 text-white font-display">
                {loginMode === "password" ? "ورود به تریدمون" : "ورود به تریدمون"}
              </h2>
              <p className="text-xs text-gray-400">
                {loginMode === "password" ? "شماره موبایل و رمز عبور خود را وارد کنید." : step === 1 ? "برای ادامه، شماره موبایلت را وارد کن." : `کد ارسال شده به ${phone} را وارد کن.`}
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-500/10 p-3 text-xs text-red-500 border border-red-500/20">{error}</div>
            )}

            {loginMode === "password" ? (
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">شماره موبایل</label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <Input type="tel" placeholder="0912 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12" maxLength={11} dir="ltr" />
                  </div>
                </div>
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">رمز عبور</label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <Input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12" dir="ltr" />
                  </div>
                </div>
                <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]">
                  {loading ? "در حال ورود..." : "ورود به حساب"}
                </Button>
              </div>
            ) : step === 1 ? (
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">شماره موبایل</label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <Input type="tel" placeholder="0912 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} onKeyDown={handleKeyDown} className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12" maxLength={11} dir="ltr" />
                  </div>
                </div>
                <Button onClick={handleSendOtp} disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]">
                  {loading ? "در حال ارسال..." : "دریافت کد ورود"}
                </Button>
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
                      <Input key={index} ref={(el) => { codeInputs.current[index] = el; }} type="text" inputMode="numeric" value={digit}
                        onChange={(e) => handleCodeChange(index, e.target.value)} onKeyDown={(e) => handleCodeKeyDown(index, e)}
                        className="h-14 w-full max-w-[48px] rounded-xl text-center text-xl font-bold bg-black/40 border-white/10 text-white focus-visible:ring-[#d6ad60]" maxLength={1} autoComplete="one-time-code" />
                    ))}
                  </div>
                </div>
                <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]">
                  {loading ? "در حال بررسی..." : "ورود به حساب"}
                </Button>
                <div className="text-center text-xs">
                  {timer > 0 ? (
                    <span className="text-gray-500">ارسال مجدد در {Math.floor(timer / 60)}:{String(timer % 60).padStart(2, "0")}</span>
                  ) : (
                    <button type="button" onClick={handleSendOtp} className="text-[#d6ad60] hover:underline">ارسال مجدد کد</button>
                  )}
                </div>
              </div>
            )}
          </form>

          <Link href="/subscription" className="block">
            <div className="group flex items-center justify-between rounded-xl border border-[#d6ad60]/30 bg-[#051118]/80 backdrop-blur-sm p-3 hover:border-[#d6ad60]/60 transition-all">
              <div className="flex items-center gap-2.5">
                <div className="bg-[#d6ad60]/15 p-1.5 rounded-lg"><CreditCard className="h-4 w-4 text-[#d6ad60]" /></div>
                <div>
                  <p className="text-xs font-bold text-white">مشاهده پلن‌های اشتراک</p>
                  <p className="text-[10px] text-gray-400">مقایسه امکانات و قیمت‌ها</p>
                </div>
              </div>
              <ArrowLeft className="h-4 w-4 text-[#d6ad60] group-hover:-translate-x-1 transition-transform" />
            </div>
          </Link>

        </div>
      </div>

      {/* 🔴 نوار افقی پایین: بازارها + افزونه (تفکیک شده) */}
      <div className="relative z-10 w-full px-4 pb-4">
        <div className="mx-auto max-w-6xl flex flex-col gap-4 border-t border-white/10 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {/* ستون ۱: صرافی‌های فعال */}
            <div className="space-y-2 flex flex-col items-center md:items-start">
              <p className="text-[10px] font-bold text-gray-300">صرافی‌های پشتیبانی شده</p>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                {EXCHANGES_MAJOR.map((ex, i) => (
                  <div key={i} className="flex flex-col items-center gap-1">
                    <div className="h-8 w-8 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
                      <img src={ex.logo} alt={ex.name} className="h-full w-full object-contain"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                          const parent = (e.target as HTMLImageElement).parentElement;
                          if (parent && !parent.querySelector(".fallback-text")) {
                            const span = document.createElement("span");
                            span.className = "fallback-text text-[7px] text-gray-300 font-bold";
                            span.innerText = ex.name.substring(0, 2);
                            parent.appendChild(span);
                          }
                        }}
                      />
                    </div>
                    <span className="text-[7px] text-gray-400">{ex.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* ستون ۲: به زودی */}
            <div className="space-y-2 flex flex-col items-center md:items-start">
              <p className="text-[10px] font-bold text-gray-500">به زودی</p>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                {EXCHANGES_COMING_SOON.map((ex, i) => (
                  <div key={i} className="flex flex-col items-center gap-1 opacity-50">
                    <div className={`relative h-7 w-7 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm ${ex.removed ? "opacity-40" : "grayscale"}`}>
                      <img src={ex.logo} alt={ex.name} className={`h-full w-full object-contain ${ex.removed ? "opacity-50" : ""}`}
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                          const parent = (e.target as HTMLImageElement).parentElement;
                          if (parent && !parent.querySelector(".fallback-text")) {
                            const span = document.createElement("span");
                            span.className = "fallback-text text-[6px] text-gray-500 font-bold";
                            span.innerText = ex.name.substring(0, 2);
                            parent.appendChild(span);
                          }
                        }}
                      />
                    </div>
                    <span className={`text-[6px] ${ex.removed ? "text-gray-600 line-through" : "text-gray-500"}`}>{ex.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* ستون ۳: صرافی‌های طلا */}
            <div className="space-y-2 flex flex-col items-center md:items-start">
              <p className="text-[10px] font-bold text-[#d6ad60]">صرافی‌های انس طلا (افزونه کروم)</p>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                {EXCHANGES_GOLD.map((ex, i) => (
                  <div key={`gold-${i}`} className="flex flex-col items-center gap-1">
                    <div className="h-8 w-8 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
                      <img src={ex.logo} alt={ex.name} className="h-full w-full object-contain"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                          const parent = (e.target as HTMLImageElement).parentElement;
                          if (parent && !parent.querySelector(".fallback-text")) {
                            const span = document.createElement("span");
                            span.className = "fallback-text text-[7px] text-[#d6ad60] font-bold";
                            span.innerText = ex.name.substring(0, 2);
                            parent.appendChild(span);
                          }
                        }}
                      />
                    </div>
                    <span className="text-[7px] text-[#d6ad60]">{ex.name}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>

      <PublicFooter />
    </main>
  );
}