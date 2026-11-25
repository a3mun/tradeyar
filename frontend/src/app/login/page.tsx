
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, setUser, getToken, getUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, useInView } from "framer-motion";
import { PublicFooter } from "@/components/layout/PublicFooter";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowLeftRight,
  BarChart3,
  Brain,
  Check,
  CreditCard,
  Filter,
  Globe,
  Layers,
  Target,
  Zap,
  ShieldCheck,
  Activity,
  CandlestickChart,
} from "lucide-react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// تبدیل اعداد فارسی و عربی به انگلیسی
function normalizeDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)))
    .replace(/\D/g, "");
}

function AnimatedNumber({
  value,
  suffix = "",
}: {
  value: number;
  suffix?: string;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
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
    <span ref={ref} className="num tabular-nums">
      {count}
      {suffix}
    </span>
  );
}

// آمار فعلی محصول
// در صورت اتصال API آمار، مقادیر این بخش را از پاسخ API دریافت کنید.
const STATS = [
  {
    label: "اندیکاتور تکنیکال",
    value: 25,
    suffix: "+",
  },
  {
    label: "بازار و منبع معاملاتی",
    value: 6,
    suffix: "",
  },
  {
    label: "دقت پیش‌بینی ثبت‌شده",
    value: 78,
    suffix: "٪",
  },
  {
    label: "تحقق اهداف ثبت‌شده",
    value: 62,
    suffix: "٪",
  },
];

const FEATURES = [
  {
    icon: Brain,
    title: "مشاور هوشمند AI",
    desc: "تحلیل و بررسی شرایط بازار با هوش مصنوعی",
  },
  {
    icon: Filter,
    title: "اسکنر فرصت‌های بازار",
    desc: "شناسایی فرصت‌های احتمالی در نمادها",
  },
  {
    icon: CandlestickChart,
    title: "تحلیل تکنیکال و سیگنال",
    desc: "بررسی ساختار بازار و ارائه سیگنال‌های معاملاتی",
  },
  {
    icon: ShieldCheck,
    title: "راستی‌آزمایی سیگنال‌ها",
    desc: "ارزیابی و بررسی مستمر عملکرد سیگنال‌ها",
  },
  {
    icon: Zap,
    title: "سه استراتژی معاملاتی",
    desc: "اسکالپ، سوئینگ و پوزیشن",
  },
  {
    icon: Target,
    title: "دو پروفایل مدیریت ریسک",
    desc: "حالت جسورانه و محتاطانه",
  },
  {
    icon: Layers,
    title: "اسپات و فیوچرز",
    desc: "تحلیل و بررسی بازارهای اسپات و تعهدی",
  },
  {
    icon: ArrowLeftRight,
    title: "مقایسه قیمت صرافی‌ها",
    desc: "بررسی و مقایسه قیمت بازارهای رمزارزی",
  },
  {
    icon: BarChart3,
    title: "بورس تهران و فارکس",
    desc: "بررسی سهام، طلا، نفت و شاخص‌ها",
  },
  {
    icon: Globe,
    title: "افزونه اختصاصی کروم",
    desc: "تحلیل زنده XAU/USD در دریا گلد و آلفا گلد",
  },
];


const EXCHANGES_COMING_SOON = [
  { name: "Ramzinex", logo: "/logos/ramzinex.png" },
  { name: "Toobit", logo: "/logos/toobit.png" },
  { name: "BingX", logo: "/logos/bingx.png" },
  { name: "Bit24", logo: "/logos/bit24.png" },
  { name: "Aban Tether", logo: "/logos/aban.png", removed: true },
];

const EXCHANGES_MAJOR = [
  { name: "نوبیتکس", logo: "/logos/nobitex.png" },
  { name: "بیت‌پین", logo: "/logos/bitpin.png" },
  { name: "والکس", logo: "/logos/wallex.png" },
  { name: "تبدیل", logo: "/logos/tabdeal.png" },
];

const EXCHANGES_GOLD = [
  { name: "آلفا گلد", logo: "/logos/alfagold.png" },
  { name: "دریا گلد", logo: "/logos/daryagold.png" },
];

export default function LoginPage() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(0);

  const [loginMode, setLoginMode] = useState<"otp" | "password">("otp");

  const [candleHeights, setCandleHeights] = useState<
    {
      id: number;
      base: number;
      peak: number;
      color: string;
    }[]
  >([]);

  const codeInputs = useRef<(HTMLInputElement | null)[]>([]);
  const codeFormRef = useRef<HTMLFormElement>(null);

  const [codeDigits, setCodeDigits] = useState([
    "",
    "",
    "",
    "",
    "",
  ]);

  useEffect(() => {
    const token = getToken();
    const user = getUser();

    if (token && user) {
      router.replace("/");
    }
  }, [router]);

  // کندل‌های پس‌زمینه
  useEffect(() => {
    setCandleHeights(
      Array.from({ length: 7 }).map((_, i) => ({
        id: i,
        base: 15 + Math.random() * 35,
        peak: 40 + Math.random() * 50,
        color:
          i % 2 === 0
            ? "bg-[#10b981]/30"
            : "bg-[#ef4444]/30",
      }))
    );
  }, []);

  // شمارش معکوس ارسال مجدد کد
  useEffect(() => {
    if (timer <= 0) return;

    const t = setTimeout(() => {
      setTimer((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearTimeout(t);
  }, [timer]);

  const handlePhoneChange = (value: string) => {
    setPhone(normalizeDigits(value).slice(0, 11));
  };

  const validatePhone = () => {
    if (!/^09\d{9}$/.test(phone)) {
      setError("لطفاً شماره موبایل معتبر وارد کنید.");
      return false;
    }

    return true;
  };

  // ارسال کد پیامکی
  const handleSendOtp = async () => {
    if (!validatePhone()) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/auth/send-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ phone }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(
          data.detail || "خطا در ارسال کد تایید."
        );
      }

      setCodeDigits(["", "", "", "", ""]);
      setStep(2);
      setTimer(120);

      setTimeout(() => {
        codeInputs.current[0]?.focus();
      }, 100);
    } catch (err: any) {
      setError(err.message || "ارتباط با سرور برقرار نشد.");
    } finally {
      setLoading(false);
    }
  };

  // ورود با کد پیامکی
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();

    const fullCode = codeDigits.join("");

    if (fullCode.length !== 5) {
      setError("لطفاً کد ۵ رقمی ارسال شده را کامل وارد کنید.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/auth/verify-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone,
          code: fullCode,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(
          data.detail || "کد وارد شده نامعتبر است."
        );
      }

      setToken(data.access_token);
      setUser(data.user);

      router.push(
        data.user?.is_new
          ? "/dashboard?welcome=true"
          : "/"
      );
    } catch (err: any) {
      setError(err.message || "خطا در تایید کد ورود.");
    } finally {
      setLoading(false);
    }
  };

  // ورود با رمز عبور
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validatePhone()) return;

    if (!password || password.length < 6) {
      setError("رمز عبور باید حداقل ۶ کاراکتر باشد.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone,
          password,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(
          data.detail || "شماره یا رمز عبور اشتباه است."
        );
      }

      setToken(data.access_token);
      setUser(data.user);

      router.push(
        data.user?.is_new
          ? "/dashboard?welcome=true"
          : "/"
      );
    } catch (err: any) {
      setError(err.message || "خطا در ورود به حساب.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Enter" && step === 1) {
      e.preventDefault();
      handleSendOtp();
    }
  };

  // ورود کد و پشتیبانی از Paste کردن کد کامل
  const handleCodeChange = (
    index: number,
    value: string
  ) => {
    const digits = normalizeDigits(value);

    if (!digits) {
      const next = [...codeDigits];
      next[index] = "";
      setCodeDigits(next);
      return;
    }

    const next = [...codeDigits];

    if (digits.length > 1) {
      const pasted = digits.slice(0, 5).split("");

      pasted.forEach((digit, i) => {
        next[i] = digit;
      });

      setCodeDigits(next);

      const nextEmpty = next.findIndex((d) => !d);

      if (nextEmpty !== -1) {
        codeInputs.current[nextEmpty]?.focus();
      } else {
        setTimeout(() => {
          codeFormRef.current?.requestSubmit();
        }, 100);
      }

      return;
    }

    next[index] = digits.slice(-1);
    setCodeDigits(next);

    if (index < 4) {
      codeInputs.current[index + 1]?.focus();
    }

    if (next.every((d) => d !== "")) {
      setTimeout(() => {
        codeFormRef.current?.requestSubmit();
      }, 100);
    }
  };

  const handleCodeKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (
      e.key === "Backspace" &&
      !codeDigits[index] &&
      index > 0
    ) {
      codeInputs.current[index - 1]?.focus();
    }

    if (
      e.key === "ArrowLeft" &&
      index > 0
    ) {
      codeInputs.current[index - 1]?.focus();
    }

    if (
      e.key === "ArrowRight" &&
      index < 4
    ) {
      codeInputs.current[index + 1]?.focus();
    }
  };

  const changeLoginMode = (
    mode: "otp" | "password"
  ) => {
    setLoginMode(mode);
    setError("");
    setPassword("");
  };

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#030712] text-white">
      {/* پس‌زمینه متحرک */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <svg
          className="absolute inset-0 h-full w-full opacity-60"
          viewBox="0 0 1200 800"
          preserveAspectRatio="none"
        >
          <motion.path
            initial={{
              pathLength: 0,
              opacity: 0,
            }}
            animate={{
              pathLength: 1,
              opacity: 0.4,
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "easeInOut",
            }}
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
              initial={{
                height: `${candle.base}%`,
              }}
              animate={{
                height: [
                  `${candle.base}%`,
                  `${candle.peak}%`,
                  `${candle.base}%`,
                ],
              }}
              transition={{
                duration: 4 + (candle.id % 5),
                repeat: Infinity,
                ease: "easeInOut",
                delay: candle.id * 0.1,
              }}
              className={`w-9 rounded-t-sm sm:w-12 ${candle.color}`}
            />
          ))}
        </div>

        <div className="absolute inset-0 bg-gradient-to-br from-[#030712]/80 via-[#030712]/60 to-[#030712]/95" />
      </div>

      {/* لوگو */}
      <header className="relative z-10 flex items-center justify-center p-4 sm:p-6">
        <Link
          href="/"
          className="flex items-center gap-3 transition-opacity hover:opacity-80"
          aria-label="صفحه اصلی تریدمون"
        >
          <img
            src="/icon-512-login.png"
            alt="لوگوی تریدمون"
            className="h-14 w-auto rounded-xl object-contain sm:h-16"
          />
        </Link>
      </header>

      {/* تیتر اصلی */}
      <section className="relative z-10 mx-auto flex w-full max-w-6xl flex-col items-center px-4 pb-8 pt-4 text-center">
        <h1 className="font-display font-bold leading-tight tracking-tight">
          <span className="block text-3xl text-white sm:text-4xl lg:text-5xl">
            تحلیل بازارهای مالی
          </span>

          <span className="mt-3 block text-lg font-medium sm:text-xl lg:text-2xl">
            <span className="text-white">
            </span>{" "}
            <span className="text-[#d6ad60]">
             معامله هوشمند از اینجا شروع میشه!
            </span>
          </span>
        </h1>

        <p className="mt-3 max-w-2xl text-xs leading-7 text-gray-400 sm:text-sm">
          دستیار تحلیل تکنیکال و بررسی سیگنال‌های معاملاتی
          در بازار رمزارزها، بورس تهران و فارکس؛ همراه با
          اسکنر فرصت‌ها و مشاور هوشمند هوش مصنوعی.
        </p>
      </section>

      {/* محتوای اصلی */}
      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col items-start gap-8 p-4 py-4 sm:p-6 lg:flex-row lg:justify-between">

        {/* ستون معرفی امکانات */}
        <section className="flex w-full flex-col gap-4 lg:w-1/2">
          {/* آمار */}
          <div className="grid w-full grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-2.5">
            {STATS.map((stat, i) => (
              <div
                key={i}
                className="flex h-full flex-col items-center justify-center rounded-xl border border-white/10 bg-[#051118]/80 py-3 backdrop-blur-sm"
              >
                <span className="text-lg font-bold leading-none text-[#d6ad60] sm:text-xl">
                  <AnimatedNumber
                    value={stat.value}
                    suffix={stat.suffix}
                  />
                </span>

                <span className="mt-2 text-center text-[9px] leading-tight text-gray-400 sm:text-[10px]">
                  {stat.label}
                </span>
              </div>
            ))}
          </div>

          {/* قابلیت‌ها */}
          <div
            className="grid flex-1 grid-cols-2 gap-2 sm:gap-2.5"
            dir="rtl"
          >
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="group flex h-full items-start gap-2 rounded-xl border border-white/10 bg-[#051118]/80 p-2 backdrop-blur-sm transition-all hover:border-[#d6ad60]/40 hover:bg-white/[0.03] sm:gap-2.5 sm:p-3"
              >
                <div className="shrink-0 rounded-lg bg-[#d6ad60]/15 p-1.5">
                  <feature.icon className="h-3.5 w-3.5 text-[#d6ad60]" />
                </div>

                <div className="min-w-0 flex-1 text-right">
                  <p className="text-[10.5px] font-bold leading-tight text-white sm:text-xs">
                    {feature.title}
                  </p>

                  <p className="mt-1 line-clamp-2 text-[8.5px] leading-snug text-gray-400 sm:text-[10px]">
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* توضیح آماری */}
          <p className="px-1 text-[9px] leading-5 text-gray-500">
          </p>
        </section>

        {/* ستون ورود */}
        <section className="relative flex w-full max-w-sm flex-col gap-3 lg:w-[400px]">
          {/* انتخاب روش ورود */}
          <div className="flex gap-1 rounded-xl border border-white/10 bg-[#051118]/80 p-1 backdrop-blur-sm">
            <button
              type="button"
              onClick={() => changeLoginMode("otp")}
              className={`h-9 flex-1 rounded-lg text-xs font-bold transition-all ${
                loginMode === "otp"
                  ? "bg-[#d6ad60] text-[#051118]"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              ورود پیامکی
            </button>

            <button
              type="button"
              onClick={() => changeLoginMode("password")}
              className={`h-9 flex-1 rounded-lg text-xs font-bold transition-all ${
                loginMode === "password"
                  ? "bg-[#d6ad60] text-[#051118]"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              ورود با رمز
            </button>
          </div>

          <form
            ref={codeFormRef}
            onSubmit={
              loginMode === "password"
                ? handlePasswordLogin
                : handleVerifyOtp
            }
            className="relative w-full rounded-2xl border border-[#d6ad60]/30 bg-[#051118]/80 p-6 shadow-[0_8px_40px_rgba(0,0,0,0.6)] backdrop-blur-sm"
          >
            <div className="mb-6 text-center">
              <h2 className="mb-1 font-display text-2xl font-bold text-white">
                ورود به تریدمون
              </h2>

              <p className="text-xs text-gray-400">
                {loginMode === "password"
                  ? "شماره موبایل و رمز عبور خود را وارد کنید."
                  : step === 1
                    ? "برای ادامه، شماره موبایلت را وارد کن."
                    : `کد ارسال‌شده به ${phone} را وارد کن.`}
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400"
              >
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
                      inputMode="numeric"
                      autoComplete="tel"
                      placeholder="0912 000 0000"
                      value={phone}
                      onChange={(e) =>
                        handlePhoneChange(e.target.value)
                      }
                      className="h-12 border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0"
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
                      autoComplete="current-password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) =>
                        setPassword(e.target.value)
                      }
                      className="h-12 border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0"
                      dir="ltr"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] shadow-[0_0_20px_rgba(214,173,96,0.3)] hover:opacity-90"
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
                      inputMode="numeric"
                      autoComplete="tel"
                      placeholder="0912 000 0000"
                      value={phone}
                      onChange={(e) =>
                        handlePhoneChange(e.target.value)
                      }
                      onKeyDown={handleKeyDown}
                      className="h-12 border-0 bg-transparent text-center text-lg text-white shadow-none focus-visible:ring-0"
                      maxLength={11}
                      dir="ltr"
                    />
                  </div>
                </div>

                <Button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] shadow-[0_0_20px_rgba(214,173,96,0.3)] hover:opacity-90"
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
                      onClick={() => {
                        setStep(1);
                        setError("");
                        setCodeDigits(["", "", "", "", ""]);
                      }}
                      className="flex items-center gap-1 text-xs text-[#d6ad60] hover:underline"
                    >
                      ویرایش شماره
                      <ArrowLeft className="h-3 w-3" />
                    </button>
                  </div>

                  <div
                    className="flex justify-between gap-2"
                    dir="ltr"
                  >
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
                        onKeyDown={(e) =>
                          handleCodeKeyDown(index, e)
                        }
                        className="h-14 w-full max-w-[48px] rounded-xl border-white/10 bg-black/40 text-center text-xl font-bold text-white focus-visible:ring-[#d6ad60]"
                        maxLength={5}
                        autoComplete="one-time-code"
                      />
                    ))}
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#051118] shadow-[0_0_20px_rgba(214,173,96,0.3)] hover:opacity-90"
                >
                  {loading ? "در حال بررسی..." : "ورود به حساب"}
                </Button>

                <div className="text-center text-xs">
                  {timer > 0 ? (
                    <span className="text-gray-500">
                      ارسال مجدد در{" "}
                      {Math.floor(timer / 60)}:
                      {String(timer % 60).padStart(2, "0")}
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={loading}
                      className="text-[#d6ad60] hover:underline disabled:opacity-50"
                    >
                      ارسال مجدد کد
                    </button>
                  )}
                </div>
              </div>
            )}
          </form>

          {/* پلن اشتراک */}
          <Link href="/subscription" className="block">
            <div className="group flex items-center justify-between rounded-xl border border-[#d6ad60]/30 bg-[#051118]/80 p-3 backdrop-blur-sm transition-all hover:border-[#d6ad60]/60">
              <div className="flex items-center gap-2.5">
                <div className="rounded-lg bg-[#d6ad60]/15 p-1.5">
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

              <ArrowLeft className="h-4 w-4 text-[#d6ad60] transition-transform group-hover:-translate-x-1" />
            </div>
          </Link>

          <p className="text-center text-[10px] leading-5 text-gray-500">
            با ورود به تریدمون، به حساب کاربری خود دسترسی پیدا
            می‌کنید. کاربران جدید نیز از دوره آزمایشی سه‌روزه
            امکانات فعال بهره‌مند می‌شوند.
          </p>
        </section>
      </div>


{/* بازارها، صرافی‌ها و افزونه طلا */}
<section className="relative z-10 w-full px-4 pb-4">
  <div className="mx-auto max-w-6xl flex flex-col gap-4 border-t border-white/10 pt-4">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

      {/* ستون ۱: منابع فعال */}
      <div className="space-y-2 flex flex-col items-center md:items-start">
        <p className="text-[10px] font-bold text-gray-300">
          بازارها و منابع فعال
        </p>

        <div className="flex flex-wrap justify-center md:justify-start gap-2">
          {EXCHANGES_MAJOR.map((ex, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div className="h-8 w-8 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = "none";
                    const parent = target.parentElement;

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

          {/* بورس تهران */}
          <div className="flex flex-col items-center gap-1">
            <div className="h-8 w-8 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
              <img
                src="/logos/tsetmc.png"
                alt="بورس تهران"
                className="h-full w-full object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            </div>
            <span className="text-[7px] text-gray-400">بورس تهران</span>
          </div>

          {/* فارکس */}
          <div className="flex flex-col items-center gap-1">
            <div className="h-8 w-8 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
              <img
                src="/logos/biquote.png"
                alt="فارکس"
                className="h-full w-full object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            </div>
            <span className="text-[7px] text-gray-400">فارکس</span>
          </div>
        </div>
      </div>

      {/* ستون ۲: به‌زودی */}
      <div className="space-y-2 flex flex-col items-center md:items-start">
        <p className="text-[10px] font-bold text-gray-500">
          به‌زودی
        </p>

        <div className="flex flex-wrap justify-center md:justify-start gap-2">
          {EXCHANGES_COMING_SOON.filter((ex) => !ex.removed).map((ex, i) => (
            <div key={i} className="flex flex-col items-center gap-1 opacity-50">
              <div className="relative h-7 w-7 rounded-full bg-[#051118]/80 border border-white/10 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm grayscale">
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = "none";
                    const parent = target.parentElement;

                    if (parent && !parent.querySelector(".fallback-text")) {
                      const span = document.createElement("span");
                      span.className = "fallback-text text-[6px] text-gray-500 font-bold";
                      span.innerText = ex.name.substring(0, 2);
                      parent.appendChild(span);
                    }
                  }}
                />
              </div>
              <span className="text-[6px] text-gray-500">{ex.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ستون ۳: افزونه طلا */}
      <div className="space-y-2 flex flex-col items-center md:items-start">
        <p className="text-[10px] font-bold text-[#d6ad60]">
          افزونه کروم تحلیل انس طلا
        </p>

        <div className="flex flex-wrap justify-center md:justify-start gap-2">
          {EXCHANGES_GOLD.map((ex, i) => (
            <div key={`gold-${i}`} className="flex flex-col items-center gap-1">
              <div className="h-8 w-8 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30 flex items-center justify-center overflow-hidden p-1 backdrop-blur-sm">
                <img
                  src={ex.logo}
                  alt={ex.name}
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = "none";
                    const parent = target.parentElement;

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
</section>

<PublicFooter />
</main>

  );
}