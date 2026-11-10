"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, setUser, getToken, getUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, useInView } from "framer-motion";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Info, HelpCircle, Phone } from "lucide-react";
import {
  ArrowLeft,
  ArrowLeftRight,
  Zap,
  Brain,
  Globe,
  Send,
  CreditCard,
  AlertTriangle,
  Check,
  Target,
  Layers,
  Filter,
  BarChart3,
} from "lucide-react";


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

// 🔴 آمار — ۴ کارت بالا (تراز با بخش پایین)
// ⚠️ اعداد «دقت پیش‌بینی» و «دقت رسیدن به هدف» از backtest میان.
//    هر هفته بعد از backtest، این دو عدد رو آپدیت کن:
//      - win_rate → «دقت پیش‌بینی روند»
//      - tp_hit_rate → «دقت رسیدن به هدف»
const STATS = [
  { label: "اندیکاتور تکنیکال", value: 32, suffix: "" },
  { label: "صرافی ایرانی", value: 4, suffix: "" },
  // 🎯 از backtest — دقت پیش‌بینی جهت روند (win_rate)
  // ⚠️ هر هفته آپدیت کن از /backtest → stats.win_rate
  { label: "دقت پیش‌بینی روند", value: 78, suffix: "٪" },
  // 🎯 از backtest — نرخ رسیدن به TP (tp_hit_rate)
  // ⚠️ هر هفته آپدیت کن از /backtest → stats.tp_hit_rate
  { label: "دقت رسیدن به هدف", value: 62, suffix: "٪" },
];

// 🔴 ۱۰ بخش — ترتیب دقیق (تبلیغاتی و منطقی)
const FEATURES = [
  // ردیف ۱
  {
    icon: Brain,
    title: "مشاور هوشمند AI",
    desc: "تحلیل با AI + کپی داده‌های خام",
  },
  {
    icon: Filter,
    title: "اسکنر فرصت‌ها",
    desc: "پیدا کردن پرسودترین نمادها",
  },
  // ردیف ۲
  {
    icon: Zap,
    title: "سه استراتژی معاملاتی",
    desc: "اسکالپ سریع، سوئینگ متعادل، پوزیشن بلندمدت",
  },
  {
    icon: Target,
    title: "دو پروفایل ریسک",
    desc: "جسورانه برای سود بیشتر، محتاطانه برای امنیت",
  },
  // ردیف ۳
  {
    icon: Layers,
    title: "اسپات و فیوچرز (تعهدی)",
    desc: "پشتیبانی از هر دو بازار",
  },
  {
    icon: Globe,
    title: "افزونه کروم",
    desc: "تحلیل زنده XAU/USD در دریا گلد و آلفا گلد",
  },
  // ردیف ۴
  {
    icon: ArrowLeftRight,
    title: "مقایسه صرافی‌ها",
    desc: "قیمت لحظه‌ای ۴ صرافی ایرانی",
  },
  {
    icon: BarChart3,
    title: "بررسی بورس تهران",
    desc: "تحلیل بازار سهام و صندوق‌های بورسی",
  },
  // ردیف ۵
  {
    icon: AlertTriangle,
    title: "هشدار تله‌ها",
    desc: "تشخیص تله صعودی، نزولی و شکست جعلی",
  },
  {
    icon: Check,
    title: "راستی‌آزمایی خودکار",
    desc: "ثبت و ارزیابی مستمر همه سیگنال‌ها",
  },
];

const EXCHANGES_MAJOR = [
  { name: "نوبیتکس", logo: "/logos/nobitex.png" },
  { name: "بیت‌پین", logo: "/logos/bitpin.png" },
  { name: "والکس", logo: "/logos/wallex.png" },
  { name: "تبدیل", logo: "/logos/tabdeal.png" },
  { name: "بورس تهران", logo: "/logos/tsetmc.png" },
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

  const [floatingSignals, setFloatingSignals] = useState<any[]>([]);
  const [candleHeights, setCandleHeights] = useState<any[]>([]);

  const codeInputs = useRef<(HTMLInputElement | null)[]>([]);
  const [codeDigits, setCodeDigits] = useState(["", "", "", "", ""]);

  useEffect(() => {
    setCandleHeights(
      Array.from({ length: 15 }).map((_, i) => ({
        id: i,
        start: 20 + ((i * 7) % 40),
        peak: 50 + ((i * 11) % 40),
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
    if (!phone || phone.length < 11)
      return setError("لطفاً شماره موبایل خود را به درستی وارد کنید.");
    setLoading(true);
    setError("");
    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
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
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
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
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, password }),
      });
      const data = await res.json();
      if (!res.ok)
        throw new Error(data.detail || "شماره یا رمز عبور اشتباه است.");
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

  const handleCodeKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace" && !codeDigits[index] && index > 0)
      codeInputs.current[index - 1]?.focus();
  };

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#07111f] text-white">
      {/* SEO sr-only — با شعار کامل */}
      <div className="sr-only" aria-hidden="true">
        <h1>
          تحلیل بازارهای مالی با تریدمون — معامله هوشمند، از اینجا شروع می‌شه! تریدمون نشه؟
        </h1>
        <h2>
          تریدمون: تحلیل تکنیکال حرفه‌ای با ۳۲ اندیکاتور، ۳ استراتژی معاملاتی،
          مشاور AI، اسکنر بازار و مقایسه صرافی‌های ایرانی
        </h2>
        <p>
          با ورود به تریدمون، به موتور تحلیل حرفه‌ای با ۳۲ اندیکاتور تکنیکال
          دسترسی پیدا می‌کنید. سه استراتژی معاملاتی (اسکالپ، سوئینگ، پوزیشن)،
          مشاور هوشمند با AI و دسترسی به داده‌های خام، اسکنر فرصت‌ها، مقایسه
          لحظه‌ای قیمت ۴ صرافی ایرانی (نوبیتکس، بیت‌پین، والکس، تبدیل)، تحلیل
          اختصاصی انس طلا (XAU/USD) از طریق افزونه کروم، مدیریت ریسک هوشمند،
          چک‌لیست معاملاتی، سناریوهای پیش‌بینی بازار، راستی‌آزمایی خودکار سیگنال،
          شاخص ترس و طمع، عمق بازار و پروفایل ریسک شخصی‌سازی شده. ۳ روز رایگان
          با اولین ورود.
        </p>
      </div>

      {/* پس‌زمینه انیمیشن */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <svg
          className="absolute inset-0 h-full w-full opacity-70"
          viewBox="0 0 1200 800"
          preserveAspectRatio="none"
        >
          <motion.path
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.6 }}
            transition={{
              duration: 8,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "easeInOut",
            }}
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
              animate={{
                height: [
                  `${candle.start}%`,
                  `${candle.peak}%`,
                  `${candle.start}%`,
                ],
              }}
              transition={{
                duration: 5 + (candle.id % 3),
                repeat: Infinity,
                ease: "easeInOut",
                delay: candle.id * 0.1,
              }}
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
              scale: [1, 1.3, 1],
            }}
            transition={{
              duration: signal.duration,
              repeat: Infinity,
              ease: "linear",
              delay: signal.delay,
            }}
            className="absolute rounded-full bg-[#d6ad60] shadow-[0_0_15px_#d6ad60]"
            style={{
              width: `${signal.size * 4}px`,
              height: `${signal.size * 4}px`,
            }}
          />
        ))}
        <div className="absolute inset-0 bg-gradient-to-br from-[#07111f]/80 via-[#07111f]/60 to-[#07111f]/95" />
      </div>

      {/* هدر */}
      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6">
        <Link
          href="/"
          className="flex items-center gap-3 transition-opacity hover:opacity-80"
        >
          <img
            src="/icon-512.png"
            alt="Trademun"
            className="h-14 w-auto sm:h-16 rounded-xl object-contain"
          />
        </Link>
        <div className="flex items-center gap-2 text-xs text-gray-400 bg-white/5 py-1 px-3 rounded-full border border-white/10">
          <div className="h-2 w-2 animate-pulse rounded-full bg-[#10b981]" />
          دستیار هوشمند بازار
        </div>
      </header>

      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center gap-8 p-4 py-8 sm:p-6 lg:flex-row lg:items-center lg:justify-between lg:pt-16">
        {/* ستون محتوا */}
        <div className="flex w-full flex-col items-center lg:items-start lg:w-1/2 text-center lg:text-right">

          {/* تیتر اصلی + شعار در یک h1 */}
          <h1 className="font-display font-bold leading-tight mt-2 tracking-tight">
            {/* خط اول: تحلیل بازارهای مالی */}
            <span className="block text-3xl sm:text-4xl lg:text-5xl text-white">
              تحلیل بازارهای مالی
            </span>
            {/* خط دوم: شعار (Lalezar، کوچک‌تر) */}
            <span className="mt-2 block text-lg sm:text-xl lg:text-2xl font-medium">
              <span className="text-white">
                معامله هوشمند، از اینجا شروع می‌شه!
              </span>{" "}
              <span className="text-[#d6ad60]">تریدمون نشه؟</span>
            </span>
          </h1>

          {/* آمار — ۴ کارت بالا */}
          <div className="mt-6 grid w-full max-w-2xl grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-2.5">
            {STATS.map((stat, i) => (
              <div
                key={i}
                className="flex h-full flex-col items-center justify-center rounded-xl border border-white/10 bg-[#0d1b2d] py-2.5"
              >
                <span className="text-lg font-bold text-[#d6ad60] leading-none">
                  <AnimatedNumber value={stat.value} suffix={stat.suffix} />
                </span>
                <span className="text-[9px] text-gray-400 mt-1.5 text-center leading-tight">
                  {stat.label}
                </span>
              </div>
            ))}
          </div>

          {/* ۱۰ ویژگی — ۲ ستونه، تم طلایی */}
          <div className="mt-6 grid w-full max-w-2xl grid-cols-2 gap-2 sm:gap-2.5">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="group flex h-full items-start gap-2 rounded-xl border border-white/10 bg-[#0d1b2d] p-2 transition-all hover:border-[#d6ad60]/40 hover:bg-white/[0.03] sm:gap-2.5 sm:p-3"
              >
                <div className="shrink-0 rounded-lg bg-[#d6ad60]/15 p-1.5">
                  <f.icon className="h-3.5 w-3.5 text-[#d6ad60]" />
                </div>
                <div className="text-right min-w-0 flex-1">
                  <p className="text-[10.5px] sm:text-xs font-bold text-white leading-tight">
                    {f.title}
                  </p>
                  <p className="text-[8.5px] sm:text-[10px] text-gray-400 mt-0.5 leading-snug line-clamp-2">
                    {f.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* صرافی‌ها (دسکتاپ) */}
          <div className="mt-8 w-full max-w-lg hidden lg:block">
            <p className="text-[10px] text-gray-400 mb-3 text-right">
              پشتیبانی از صرافی‌های معتبر ایرانی
            </p>
            <div className="flex flex-wrap items-center justify-start gap-3">
              {EXCHANGES_MAJOR.map((ex, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <div className="h-9 w-9 rounded-full bg-[#0d1b2d] border border-white/10 flex items-center justify-center overflow-hidden p-1">
                    <img
                      src={ex.logo}
                      alt={ex.name}
                      className="h-full w-full object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                        const parent = (e.target as HTMLImageElement)
                          .parentElement;
                        if (parent && !parent.querySelector(".fallback-text")) {
                          const span = document.createElement("span");
                          span.className =
                            "fallback-text text-[8px] text-gray-300 font-bold";
                          span.innerText = ex.name.substring(0, 2);
                          parent.appendChild(span);
                        }
                      }}
                    />
                  </div>
                  <span className="text-[8px] text-gray-400">{ex.name}</span>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-center gap-2">
              <span className="text-[9px] text-gray-500">در آینده نزدیک:</span>
            </div>
            <div className="flex flex-wrap items-center justify-start gap-3 mt-2 opacity-50">
              {EXCHANGES_COMING_SOON.map((ex, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <div
                    className={`relative h-8 w-8 rounded-full bg-[#0d1b2d] border border-white/10 flex items-center justify-center overflow-hidden p-1 ${
                      ex.removed ? "opacity-40" : "grayscale"
                    }`}
                  >
                    <img
                      src={ex.logo}
                      alt={ex.name}
                      className={`h-full w-full object-contain ${
                        ex.removed ? "opacity-50" : ""
                      }`}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                        const parent = (e.target as HTMLImageElement)
                          .parentElement;
                        if (parent && !parent.querySelector(".fallback-text")) {
                          const span = document.createElement("span");
                          span.className =
                            "fallback-text text-[7px] text-gray-500 font-bold";
                          span.innerText = ex.name.substring(0, 2);
                          parent.appendChild(span);
                        }
                      }}
                    />
                  </div>
                  <span
                    className={`text-[7px] ${
                      ex.removed
                        ? "text-gray-600 line-through"
                        : "text-gray-500"
                    }`}
                  >
                    {ex.name}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center gap-2">
              <AlertTriangle className="h-3 w-3 text-[#d6ad60]" />
              <p className="text-[10px] text-[#d6ad60]">
                تحلیل اختصاصی انس طلا (فقط از طریق افزونه تریدمون)
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-start gap-3 mt-3">
              {EXCHANGES_GOLD.map((ex, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <div className="h-9 w-9 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30 flex items-center justify-center overflow-hidden p-1">
                    <img
                      src={ex.logo}
                      alt={ex.name}
                      className="h-full w-full object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                        const parent = (e.target as HTMLImageElement)
                          .parentElement;
                        if (parent && !parent.querySelector(".fallback-text")) {
                          const span = document.createElement("span");
                          span.className =
                            "fallback-text text-[8px] text-[#d6ad60] font-bold";
                          span.innerText = ex.name.substring(0, 2);
                          parent.appendChild(span);
                        }
                      }}
                    />
                  </div>
                  <span className="text-[8px] text-[#d6ad60]">{ex.name}</span>
                </div>
              ))}
            </div>
            <p className="text-[8px] text-gray-500 mt-3 leading-relaxed text-right">
              ⚠️ تریدمون هیچ سفارش یا تراکنشی در این پلتفرم‌ها انجام نمی‌دهد و
              صرفاً تحلیل داده‌های انس طلا را از طریق افزونه ارائه می‌کند.
            </p>
          </div>
        </div>

        {/* ستون فرم ورود */}
        <div className="relative w-full max-w-sm lg:w-[400px] lg:sticky lg:top-24">
          <div className="flex gap-1 p-1 mb-3 bg-[#0d1b2d] border border-white/10 rounded-xl">
            <button
              onClick={() => {
                setLoginMode("otp");
                setError("");
              }}
              className={`flex-1 h-9 rounded-lg text-xs font-bold transition-all ${
                loginMode === "otp"
                  ? "bg-[#d6ad60] text-[#07111f]"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              کد پیامکی
            </button>
            <button
              onClick={() => {
                setLoginMode("password");
                setError("");
              }}
              className={`flex-1 h-9 rounded-lg text-xs font-bold transition-all ${
                loginMode === "password"
                  ? "bg-[#d6ad60] text-[#07111f]"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              رمز عبور
            </button>
          </div>

          <form
            onSubmit={
              loginMode === "password" ? handlePasswordLogin : handleVerifyOtp
            }
            className="relative w-full rounded-2xl border border-[#d6ad60]/20 bg-[#0d1b2d] p-6 shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
          >
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-1 text-white font-display">
                {loginMode === "password"
                  ? "ورود با رمز"
                  : "ورود به تریدمون"}
              </h2>
              <p className="text-xs text-gray-400">
                {loginMode === "password"
                  ? "شماره موبایل و رمز عبور خود را وارد کنید."
                  : step === 1
                  ? "برای ادامه، شماره موبایلت را وارد کن."
                  : `کد ارسال شده به ${phone} را وارد کن.`}
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-500/10 p-3 text-xs text-red-500 border border-red-500/20">
                {error}
              </div>
            )}

            {loginMode === "password" ? (
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">
                    شماره موبایل
                  </label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <Input
                      type="tel"
                      placeholder="0912 000 0000"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12"
                      maxLength={11}
                      dir="ltr"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">
                    رمز عبور
                  </label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
                    <Input
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0 h-12"
                      dir="ltr"
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]"
                >
                  {loading ? "در حال ورود..." : "ورود به حساب"}
                </Button>
              </div>
            ) : step === 1 ? (
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-400">
                    شماره موبایل
                  </label>
                  <div className="flex flex-row-reverse items-center rounded-xl border border-white/10 bg-black/40 px-3 transition-colors focus-within:border-[#d6ad60]">
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
                <Button
                  onClick={handleSendOtp}
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]"
                >
                  {loading ? "در حال ارسال..." : "دریافت کد ورود"}
                </Button>
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-xs font-medium text-gray-400">
                      کد تایید
                    </label>
                    <button
                      type="button"
                      onClick={() => setStep(1)}
                      className="flex items-center gap-1 text-xs text-[#d6ad60] hover:underline"
                    >
                      ویرایش شماره <ArrowLeft className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="flex justify-between gap-2" dir="ltr">
                    {codeDigits.map((digit, index) => (
                      <Input
                        key={index}
                        ref={(el) => {
                          codeInputs.current[index] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        value={digit}
                        onChange={(e) =>
                          handleCodeChange(index, e.target.value)
                        }
                        onKeyDown={(e) => handleCodeKeyDown(index, e)}
                        className="h-14 w-full max-w-[48px] rounded-xl text-center text-xl font-bold bg-black/40 border-white/10 text-white focus-visible:ring-[#d6ad60]"
                        maxLength={1}
                        autoComplete="one-time-code"
                      />
                    ))}
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90 shadow-[0_0_20px_rgba(214,173,96,0.3)]"
                >
                  {loading ? "در حال بررسی..." : "ورود به حساب"}
                </Button>
                <div className="text-center text-xs">
                  {timer > 0 ? (
                    <span className="text-gray-500">
                      ارسال مجدد در {Math.floor(timer / 60)}:
                      {String(timer % 60).padStart(2, "0")}
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      className="text-[#d6ad60] hover:underline"
                    >
                      ارسال مجدد کد
                    </button>
                  )}
                </div>
              </div>
            )}
          </form>

          <Link href="/subscription" className="mt-4 block">
            <div className="group flex items-center justify-between rounded-xl border border-[#d6ad60]/30 bg-[#0d1b2d] p-3 hover:border-[#d6ad60]/60 transition-all">
              <div className="flex items-center gap-2.5">
                <div className="bg-[#d6ad60]/15 p-1.5 rounded-lg">
                  <CreditCard className="h-4 w-4 text-[#d6ad60]" />
                </div>
                <div>
                  <p className="text-xs font-bold text-white">
                    مشاهده پلن‌های اشتراک
                  </p>
                  <p className="text-[10px] text-gray-400">
                    مقایسه امکانات و قیمت‌ها
                  </p>
                </div>
              </div>
              <ArrowLeft className="h-4 w-4 text-[#d6ad60] group-hover:-translate-x-1 transition-transform" />
            </div>
          </Link>

          <div className="mt-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
            <p className="text-[11px] font-bold text-emerald-400 flex items-center justify-center gap-1.5">
              🎁 با اولین ورود، ۳ روز اشتراک رایگان هدیه بگیر!
            </p>
            <p className="text-[9px] text-emerald-500/70 mt-0.5">
              بدون نیاز به کارت بانکی
            </p>
          </div>



          <div className="mt-4 rounded-xl border border-yellow-500/20 bg-[#0d1b2d] p-3 text-center">
            <p className="text-[10px] text-yellow-500/80 leading-relaxed">
              ⚠️ تحلیل‌های تریدمون صرفاً جنبه آموزشی دارند. تصمیم نهایی و
              مسئولیت سود یا ضرر با خودتونه.
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

      {/* موبایل: صرافی‌ها */}
      <div className="relative z-10 w-full px-4 pb-8 lg:hidden">
        <p className="text-[10px] text-gray-400 mb-3 text-center">
          پشتیبانی از صرافی‌های معتبر ایرانی
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {EXCHANGES_MAJOR.map((ex, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div className="h-9 w-9 rounded-full bg-[#0d1b2d] border border-white/10 flex items-center justify-center overflow-hidden p-1">
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                    const parent = (e.target as HTMLImageElement).parentElement;
                    if (parent && !parent.querySelector(".fallback-text")) {
                      const span = document.createElement("span");
                      span.className =
                        "fallback-text text-[8px] text-gray-300 font-bold";
                      span.innerText = ex.name.substring(0, 2);
                      parent.appendChild(span);
                    }
                  }}
                />
              </div>
              <span className="text-[8px] text-gray-400">{ex.name}</span>
            </div>
          ))}
        </div>
        <div className="mt-5 flex items-center justify-center gap-2">
          <span className="text-[9px] text-gray-500">در آینده نزدیک:</span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-2 opacity-50">
          {EXCHANGES_COMING_SOON.map((ex, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div
                className={`relative h-8 w-8 rounded-full bg-[#0d1b2d] border border-white/10 flex items-center justify-center overflow-hidden p-1 ${
                  ex.removed ? "opacity-40" : "grayscale"
                }`}
              >
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className={`h-full w-full object-contain ${
                    ex.removed ? "opacity-50" : ""
                  }`}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                    const parent = (e.target as HTMLImageElement).parentElement;
                    if (parent && !parent.querySelector(".fallback-text")) {
                      const span = document.createElement("span");
                      span.className =
                        "fallback-text text-[7px] text-gray-500 font-bold";
                      span.innerText = ex.name.substring(0, 2);
                      parent.appendChild(span);
                    }
                  }}
                />
              </div>
              <span
                className={`text-[7px] ${
                  ex.removed
                    ? "text-gray-600 line-through"
                    : "text-gray-500"
                }`}
              >
                {ex.name}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-5 flex items-center justify-center gap-2">
          <AlertTriangle className="h-3 w-3 text-[#d6ad60]" />
          <p className="text-[10px] text-[#d6ad60]">
            تحلیل اختصاصی انس طلا (فقط از طریق افزونه تریدمون)
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-3">
          {EXCHANGES_GOLD.map((ex, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div className="h-9 w-9 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30 flex items-center justify-center overflow-hidden p-1">
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                    const parent = (e.target as HTMLImageElement).parentElement;
                    if (parent && !parent.querySelector(".fallback-text")) {
                      const span = document.createElement("span");
                      span.className =
                        "fallback-text text-[8px] text-[#d6ad60] font-bold";
                      span.innerText = ex.name.substring(0, 2);
                      parent.appendChild(span);
                    }
                  }}
                />
              </div>
              <span className="text-[8px] text-[#d6ad60]">{ex.name}</span>
            </div>
          ))}
        </div>
        <p className="text-[8px] text-gray-500 mt-3 leading-relaxed text-center">
          ⚠️ تریدمون هیچ سفارش یا تراکنشی در این پلتفرم‌ها انجام نمی‌دهد و
          صرفاً تحلیل داده‌های انس طلا را از طریق افزونه ارائه می‌کند.
        </p>
      </div>

      <PublicFooter />
    </main>
  );
}