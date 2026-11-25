"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  ArrowRight,
  Check,
  CheckCircle2,
  Copy,
  ShieldCheck,
  Zap,
  Gift,
  CreditCard,
  Wallet,
  Sparkles,
  Clock,
  Info,
  LayoutDashboard,
  AlertTriangle,
  XCircle,
  RefreshCw,
  TrendingUp,
  BarChart3,
  BrainCircuit,
  ScanSearch,
  Activity,
  CandlestickChart,
  Globe2,
  Layers3,
  Database,
  Puzzle,
  Ticket,
  LockKeyhole,
  ChevronLeft,
  Star,
} from "lucide-react";

import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getToken } from "@/lib/auth";

const CARD_NUMBER = "5859-4710-1084-0910";
const CARD_HOLDER = "";
const PENDING_KEY = "trademun_pending_request";

type PaymentMethod = "zibal" | "card";

type Plan = {
  id: string;
  title: string;
  price: number | string;
  oldPrice: number | string;
  discount: number;
  days: number;
  popular: boolean;
};

const PLAN_TITLES: Record<string, string> = {
  "1_month": "یک‌ماهه",
  "3_months": "سه‌ماهه",
  "6_months": "شش‌ماهه",
  "12_months": "یک‌ساله",
  "1_year": "یک‌ساله",
};

const PLAN_DAYS: Record<string, number> = {
  "1_month": 30,
  "3_months": 90,
  "6_months": 180,
  "12_months": 365,
  "1_year": 365,
};

const numberFormat = new Intl.NumberFormat("fa-IR");

function formatPrice(value: unknown) {
  const number = Number(value);

  if (!Number.isFinite(number) || number < 0) {
    return "—";
  }

  return numberFormat.format(number);
}

function getPlanTitle(id: string) {
  return PLAN_TITLES[id] || id.replace(/_/g, " ");
}

function getPlanDays(id: string) {
  return PLAN_DAYS[id] || 30;
}

const featureGroups = [
  {
    title: "تحلیل بازارهای مالی",
    description: "بررسی بازارهای مختلف از یک محیط واحد",
    icon: CandlestickChart,
    features: [
      "تحلیل تکنیکال رمزارزها در صرافی‌های ایرانی",
      "تحلیل فارکس، طلا، نفت و شاخص‌ها",
      "تحلیل تکنیکال بورس تهران",
      "مقایسه قیمت صرافی‌ها",
      "بررسی عمق بازار",
    ],
  },
  {
    title: "سیگنال و ابزارهای معاملاتی",
    description: "ابزارهایی برای بررسی دقیق‌تر موقعیت‌های معاملاتی",
    icon: Activity,
    features: [
      "کارت سیگنال و جدول تایم‌فریم‌ها",
      "سیگنال‌های زنده بازار",
      "سناریوهای پیش‌روی بازار",
      "نقاط حمایت و مقاومت",
      "چک‌لیست اندیکاتورها",
      "شاخص ترس و طمع بازار",
      "آمار عملکرد سیگنال‌ها",
    ],
  },
  {
    title: "هوش مصنوعی و تحلیل هوشمند",
    description: "ابزارهای هوشمند برای کمک به بررسی بازار",
    icon: BrainCircuit,
    features: [
      "اسکنر فرصت‌های معاملاتی",
      "مشاوره هوشمند با استفاده از هوش مصنوعی",
      "کپی و دریافت داده‌های خام",
    ],
  },
];

const proFeatures = [
  {
    icon: Puzzle,
    title: "افزونه اختصاصی کروم",
    description: "دریافت افزونه‌های مرتبط با دریا گلد و آلفا گلد",
  },
  {
    icon: Ticket,
    title: "درخواست افزونه سفارشی",
    description: "ثبت درخواست از طریق تیکت پشتیبانی",
  },
];

export default function SubscriptionPage() {
  const router = useRouter();

  const [selectedPlan, setSelectedPlan] = useState("3_months");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("zibal");
  const [paymentTime, setPaymentTime] = useState("");
  const [note, setNote] = useState("");

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isErrorOpen, setIsErrorOpen] = useState(false);

  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState(false);

  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const token = getToken();

  const selectedPlanData = plans.find(
    (plan) => plan.id === selectedPlan
  );

  const loadPlans = useCallback(async () => {
    setPlansLoading(true);
    setPlansError(false);

    try {
      const response = await fetch(`${apiUrl}/admin/pricing`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("دریافت اطلاعات قیمت‌گذاری ناموفق بود.");
      }

      const data = await response.json();

      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("ساختار اطلاعات قیمت‌گذاری معتبر نیست.");
      }

      const formatted: Plan[] = Object.entries(data).map(
        ([id, value]: [string, any]) => ({
          id,
          title: getPlanTitle(id),
          price: value?.price ?? 0,
          oldPrice: value?.old_price ?? 0,
          discount: Number(value?.discount ?? 0) || 0,
          days: getPlanDays(id),
          popular: Boolean(value?.popular),
        })
      );

      setPlans(formatted);

      if (formatted.length > 0) {
        setSelectedPlan((current) => {
          if (formatted.some((plan) => plan.id === current)) {
            return current;
          }

          return (
            formatted.find((plan) => plan.popular)?.id ||
            formatted[0].id
          );
        });
      }
    } catch (error) {
      console.error("Subscription pricing error:", error);
      setPlansError(true);
    } finally {
      setPlansLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      localStorage.getItem(PENDING_KEY) === "true"
    ) {
      setSuccess(true);
    }

    loadPlans();

    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, [loadPlans]);

  const showError = (message: string) => {
    setErrorMessage(message);
    setIsErrorOpen(true);
  };

  const copyCard = async () => {
    try {
      await navigator.clipboard.writeText(
        CARD_NUMBER.replace(/-/g, "")
      );

      setCopied(true);

      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }

      copyTimeoutRef.current = setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch {
      showError(
        "کپی شماره کارت انجام نشد. لطفاً شماره کارت را به‌صورت دستی کپی کنید."
      );
    }
  };

  const openConfirm = () => {
    if (!token) {
      router.push("/login");
      return;
    }

    if (!selectedPlanData) {
      showError("لطفاً ابتدا یک مدت اشتراک معتبر انتخاب کنید.");
      return;
    }

    if (
      !Number.isFinite(Number(selectedPlanData.price)) ||
      Number(selectedPlanData.price) <= 0
    ) {
      showError(
        "قیمت این اشتراک در حال حاضر معتبر نیست. لطفاً کمی بعد دوباره تلاش کنید."
      );
      return;
    }

    setIsConfirmOpen(true);
  };

  // منطق اصلی پرداخت حفظ شده است.
  const executePayment = async () => {
    setIsConfirmOpen(false);

    if (paymentMethod === "card" && !paymentTime.trim()) {
      showError(
        "لطفاً زمان واریز را وارد کنید (مثال: 1404/10/25 - 16:42)"
      );
      return;
    }

    setLoading(true);

    try {
      const endpoint =
        paymentMethod === "zibal"
          ? "/subscription/pay/zibal"
          : "/subscription/request";

      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          plan: selectedPlan,
          receipt_note: note,
          payment_time:
            paymentMethod === "zibal" ? "online" : paymentTime,
          payment_method: paymentMethod,
          amount: selectedPlanData?.price,
          plan_price_at_purchase: selectedPlanData?.price,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data?.detail || "پرداخت یا ثبت درخواست با خطا مواجه شد."
        );
      }

      if (paymentMethod === "zibal" && data.payment_url) {
        window.location.href = data.payment_url;
      } else {
        if (typeof window !== "undefined") {
          localStorage.setItem(PENDING_KEY, "true");
        }

        setSuccess(true);
      }
    } catch (err: any) {
      showError(
        err?.message || "ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید."
      );
    } finally {
      setLoading(false);
    }
  };

  const isCardPayment = paymentMethod === "card";

  return (
    <div
      className="flex min-h-screen flex-col overflow-hidden bg-[#030712] text-white"
      dir="rtl"
    >
      <Header />

      <main className="relative flex-1">
        {/* پس‌زمینه تزئینی */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-[520px] overflow-hidden"
        >
          <div className="absolute -top-48 left-1/2 h-[420px] w-[700px] -translate-x-1/2 rounded-full bg-[#d6ad60]/[0.07] blur-[120px]" />
          <div className="absolute right-[-180px] top-40 h-72 w-72 rounded-full bg-blue-500/[0.04] blur-[100px]" />
        </div>

        <div className="relative mx-auto w-full max-w-6xl px-4 pb-16 pt-5 sm:px-6 sm:pt-8 lg:px-8">
          {/* بازگشت */}
          <div className="mb-7">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.035] px-3.5 py-2 text-xs text-gray-400 transition hover:border-[#d6ad60]/30 hover:bg-white/[0.07] hover:text-white"
            >
              <ArrowRight className="h-3.5 w-3.5" />
              بازگشت
            </Link>
          </div>

          {/* هدر اصلی و سئو */}
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-9 max-w-3xl text-center"
          >
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/[0.07] px-3.5 py-1.5 text-[11px] font-medium text-[#e5c786]">
              <Sparkles className="h-3.5 w-3.5" />
              تجربه حرفه‌ای تحلیل بازار
            </div>

            <h1 className="text-2xl font-black leading-[1.7] tracking-tight text-white sm:text-3xl md:text-4xl">
              با دیدی دقیق‌تر،
              <span className="text-[#d6ad60]"> هوشمندتر معامله کنید</span>
            </h1>

            <p className="mx-auto mt-4 max-w-2xl text-sm leading-8 text-gray-400 sm:text-[15px]">
              تریدمون مجموعه‌ای از ابزارهای تحلیل تکنیکال، بررسی بازارهای
              مالی، سیگنال‌ها و ابزارهای هوشمند را در یک محیط یکپارچه
              در اختیار شما قرار می‌دهد. امکانات را تجربه کنید و متناسب
              با مدت استفاده‌تان اشتراک حرفه‌ای تهیه کنید.
            </p>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-3 text-[11px] text-gray-400">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-[#d6ad60]" />
                پرداخت امن
              </span>
              <span className="flex items-center gap-1.5">
                <Activity className="h-4 w-4 text-[#d6ad60]" />
                ابزارهای متنوع بازار
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-[#d6ad60]" />
                دسترسی یکپارچه
              </span>
            </div>
          </motion.section>

          {/* پیشنهاد سه روز رایگان */}
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
            className="relative mb-7 overflow-hidden rounded-2xl border border-emerald-400/20 bg-gradient-to-l from-[#0c211e] via-[#0a1b1d] to-[#09131c] p-4 sm:p-5"
          >
            <div className="absolute -left-10 -top-16 h-40 w-40 rounded-full bg-emerald-400/[0.07] blur-3xl" />

            <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3.5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-emerald-400/20 bg-emerald-400/10">
                  <Gift className="h-5 w-5 text-emerald-300" />
                </div>

                <div>
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-bold text-white sm:text-base">
                      ۳ روز رایگان برای شروع
                    </h2>
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300">
                      بدون پرداخت اولیه
                    </span>
                  </div>

                  <p className="max-w-xl text-xs leading-6 text-gray-400">
                    بعد از ثبت‌نام، سه روز فرصت دارید امکانات فعال
                    تریدمون را تجربه کنید و با فضای ابزارها و تحلیل‌ها
                    آشنا شوید.
                  </p>
                </div>
              </div>

              <Link
                href="/dashboard"
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-2.5 text-xs font-bold text-emerald-200 transition hover:bg-emerald-400/15"
              >
                شروع رایگان
                <ChevronLeft className="h-4 w-4" />
              </Link>
            </div>
          </motion.section>

          {/* امکانات */}
          <section className="mb-10">
            <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="mb-1 text-[10px] font-bold tracking-wider text-[#d6ad60]">
                  امکانات تریدمون
                </p>
                <h2 className="text-lg font-extrabold text-white sm:text-xl">
                  ابزارهای موردنیاز بازار، در یک جا
                </h2>
              </div>

              <p className="text-[11px] text-gray-500">
                امکانات فعال در دوره آشنایی نیز قابل تجربه هستند.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {featureGroups.map((group, index) => {
                const Icon = group.icon;

                return (
                  <motion.div
                    key={group.title}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.12 + index * 0.07 }}
                    className="rounded-2xl border border-white/[0.07] bg-[#08121e]/90 p-4 transition duration-300 hover:border-[#d6ad60]/25 hover:bg-[#0b1926]"
                  >
                    <div className="mb-4 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#d6ad60]/15 bg-[#d6ad60]/[0.08]">
                        <Icon className="h-5 w-5 text-[#d6ad60]" />
                      </div>

                      <div>
                        <h3 className="text-sm font-bold text-white">
                          {group.title}
                        </h3>
                        <p className="mt-1 text-[10px] text-gray-500">
                          {group.description}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2.5 border-t border-white/[0.06] pt-4">
                      {group.features.map((feature) => (
                        <div
                          key={feature}
                          className="flex items-start gap-2 text-xs leading-5 text-gray-300"
                        >
                          <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* موردی که هنوز عرضه نشده */}
            <div className="mt-3 flex flex-col gap-2 rounded-xl border border-white/[0.06] bg-white/[0.025] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2.5">
                <Globe2 className="h-4 w-4 text-gray-500" />
                <span className="text-xs text-gray-400">
                  تحلیل بنیادین بازار
                </span>
              </div>
              <span className="w-fit rounded-full border border-amber-400/15 bg-amber-400/[0.06] px-2.5 py-1 text-[10px] font-medium text-amber-300">
                به‌زودی
              </span>
            </div>
          </section>

          {/* امکانات تکمیلی اشتراک حرفه‌ای */}
          <section className="mb-10 overflow-hidden rounded-2xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#101b29] to-[#07121d] p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#d6ad60]/10">
                <Star className="h-5 w-5 text-[#d6ad60]" />
              </div>

              <div>
                <h2 className="text-sm font-bold text-white">
                  امکانات تکمیلی اشتراک حرفه‌ای
                </h2>
                <p className="mt-1 text-[10px] text-gray-500">
                  ابزارها و خدمات اختصاصی برای کاربران حرفه‌ای
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {proFeatures.map((feature) => {
                const Icon = feature.icon;

                return (
                  <div
                    key={feature.title}
                    className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-black/20 p-3.5"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#d6ad60]/10">
                      <Icon className="h-4 w-4 text-[#d6ad60]" />
                    </div>

                    <div>
                      <h3 className="text-xs font-bold text-gray-100">
                        {feature.title}
                      </h3>
                      <p className="mt-1 text-[10px] leading-5 text-gray-500">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* انتخاب اشتراک */}
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18 }}
            className="mb-8"
            id="subscription-plans"
          >
            <div className="mb-5 text-center">
              <p className="mb-1 text-[10px] font-bold tracking-wider text-[#d6ad60]">
                اشتراک حرفه‌ای
              </p>

              <h2 className="text-xl font-black text-white sm:text-2xl">
                مدت اشتراک خود را انتخاب کنید
              </h2>

              <p className="mt-2 text-xs leading-6 text-gray-500">
                یک اشتراک، دسترسی به مجموعه امکانات حرفه‌ای تریدمون
              </p>
            </div>

            <div className="rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-br from-[#101c2a] to-[#07131e] p-4 shadow-[0_15px_60px_rgba(0,0,0,0.2)] sm:p-6">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/10">
                    <Zap className="h-5 w-5 text-[#d6ad60]" />
                  </div>

                  <div>
                    <h3 className="text-base font-extrabold text-[#e5c786]">
                      اشتراک حرفه‌ای تریدمون
                    </h3>
                    <p className="mt-1 text-[10px] text-gray-500">
                      دسترسی به امکانات حرفه‌ای در طول مدت اشتراک
                    </p>
                  </div>
                </div>

                <span className="flex w-fit items-center gap-1.5 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/[0.08] px-3 py-1.5 text-[10px] font-bold text-[#e5c786]">
                  <Sparkles className="h-3 w-3" />
                  همه امکانات در یک پلن
                </span>
              </div>

              {plansLoading ? (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {[1, 2, 3, 4].map((item) => (
                    <div
                      key={item}
                      className="h-32 animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.035]"
                    />
                  ))}
                </div>
              ) : plansError ? (
                <div className="rounded-xl border border-red-400/15 bg-red-400/[0.04] p-5 text-center">
                  <AlertTriangle className="mx-auto mb-2 h-6 w-6 text-red-400" />
                  <p className="text-xs text-gray-300">
                    دریافت قیمت اشتراک‌ها با مشکل مواجه شد.
                  </p>
                  <Button
                    onClick={loadPlans}
                    variant="outline"
                    className="mt-3 h-9 border-white/10 text-xs text-gray-200 hover:bg-white/5"
                  >
                    <RefreshCw className="ml-2 h-3.5 w-3.5" />
                    تلاش مجدد
                  </Button>
                </div>
              ) : plans.length === 0 ? (
                <div className="rounded-xl border border-white/[0.07] bg-black/20 p-5 text-center">
                  <Info className="mx-auto mb-2 h-6 w-6 text-gray-500" />
                  <p className="text-xs text-gray-400">
                    در حال حاضر گزینه‌ای برای خرید اشتراک موجود نیست.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {plans.map((plan) => {
                    const isSelected = selectedPlan === plan.id;
                    const hasDiscount =
                      Number(plan.discount) > 0;
                    const hasOldPrice =
                      Number(plan.oldPrice) > Number(plan.price);

                    return (
                      <button
                        key={plan.id}
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => setSelectedPlan(plan.id)}
                        className={`relative flex min-h-[142px] flex-col rounded-xl p-3 text-right transition-all duration-200 sm:p-4 ${
                          isSelected
                            ? "border border-[#d6ad60] bg-[#d6ad60]/[0.09] shadow-[0_0_25px_rgba(214,173,96,0.08)] ring-1 ring-[#d6ad60]/20"
                            : "border border-white/[0.07] bg-black/20 hover:border-[#d6ad60]/30 hover:bg-white/[0.035]"
                        }`}
                      >
                        {plan.popular && (
                          <span className="absolute -top-2.5 right-3 flex items-center gap-1 rounded-full bg-[#d6ad60] px-2.5 py-1 text-[9px] font-extrabold text-[#07111f] shadow-lg">
                            <Sparkles className="h-2.5 w-2.5" />
                            پرفروش
                          </span>
                        )}

                        <div className="mb-3 flex w-full items-center justify-between gap-1">
                          <span
                            className={`text-xs font-bold sm:text-sm ${
                              isSelected ? "text-[#e5c786]" : "text-white"
                            }`}
                          >
                            {plan.title}
                          </span>

                          {isSelected && (
                            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[#d6ad60]">
                              <Check className="h-2.5 w-2.5 text-[#07111f]" />
                            </span>
                          )}
                        </div>

                        <div className="mt-auto">
                          <div className="flex flex-wrap items-baseline gap-1">
                            <span className="text-base font-black text-white sm:text-lg">
                              {formatPrice(plan.price)}
                            </span>
                            <span className="text-[9px] text-gray-500">
                              تومان
                            </span>
                          </div>

                          {hasOldPrice && (
                            <p className="mt-1 text-[10px] text-gray-500 line-through">
                              {formatPrice(plan.oldPrice)} تومان
                            </p>
                          )}

                          {hasDiscount && (
                            <span className="mt-2 inline-flex rounded-md border border-emerald-400/15 bg-emerald-400/[0.07] px-2 py-1 text-[9px] font-bold text-emerald-300">
                              {formatPrice(plan.discount)}٪ تخفیف
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {selectedPlanData && !plansLoading && !plansError && (
                <div className="mt-4 flex flex-col gap-3 rounded-xl border border-white/[0.06] bg-black/20 p-3.5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <Clock className="h-4 w-4 text-[#d6ad60]" />
                    مدت این اشتراک:
                    <span className="font-bold text-white">
                      {numberFormat.format(selectedPlanData.days)} روز
                    </span>
                  </div>

                  <div className="flex items-center justify-between gap-2 sm:justify-end">
                    <span className="text-[10px] text-gray-500">
                      مبلغ قابل پرداخت
                    </span>
                    <span className="text-sm font-extrabold text-[#e5c786]">
                      {formatPrice(selectedPlanData.price)}
                      <span className="mr-1 text-[10px] font-normal text-gray-400">
                        تومان
                      </span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          </motion.section>

          {/* پرداخت */}
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.22 }}
            className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#08121e] shadow-xl shadow-black/20"
            id="payment"
          >
            <div className="border-b border-white/[0.06] px-4 py-4 sm:px-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#d6ad60]/10">
                  <ShieldCheck className="h-5 w-5 text-[#d6ad60]" />
                </div>

                <div>
                  <h2 className="text-sm font-bold text-white">
                    تکمیل خرید اشتراک
                  </h2>
                  <p className="mt-1 text-[10px] text-gray-500">
                    روش پرداخت موردنظر خود را انتخاب کنید.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 sm:p-6">
              {success ? (
                <div className="flex flex-col items-center gap-4 py-7">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full border border-emerald-400/20 bg-emerald-400/10">
                    <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                  </div>

                  <div className="max-w-md text-center">
                    <h3 className="text-base font-extrabold text-white">
                      درخواست شما با موفقیت ثبت شد
                    </h3>

                    <p className="mt-2 text-xs leading-7 text-gray-400">
                      درخواست شما برای بررسی ثبت شده است. پس از تأیید،
                      اشتراک فعال می‌شود و از طریق داشبورد و پیامک
                      مطلع خواهید شد.
                    </p>
                  </div>

                  <div className="w-full max-w-md rounded-xl border border-[#d6ad60]/15 bg-[#d6ad60]/[0.05] p-3 text-center">
                    <p className="flex items-center justify-center gap-2 text-[10px] text-gray-400">
                      <Clock className="h-3.5 w-3.5 text-[#d6ad60]" />
                      زمان بررسی درخواست معمولاً کمتر از ۲۴ ساعت است.
                    </p>
                  </div>

                  <div className="mt-2 flex w-full max-w-md flex-col gap-2 sm:flex-row">
                    <Link href="/dashboard" className="flex-1">
                      <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] hover:opacity-90">
                        <LayoutDashboard className="h-4 w-4" />
                        رفتن به داشبورد
                      </Button>
                    </Link>

                    <Link href="/" className="flex-1">
                      <Button
                        variant="outline"
                        className="h-11 w-full border-white/10 text-sm text-gray-300 hover:bg-white/5"
                      >
                        بازگشت به خانه
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : !token ? (
                <div className="mx-auto max-w-lg rounded-xl border border-white/[0.07] bg-black/20 p-5 text-center sm:p-7">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[#d6ad60]/10">
                    <LockKeyhole className="h-5 w-5 text-[#d6ad60]" />
                  </div>

                  <h3 className="text-sm font-bold text-white">
                    یک قدم تا شروع تجربه تریدمون
                  </h3>

                  <p className="mx-auto mt-2 max-w-sm text-xs leading-6 text-gray-400">
                    برای خرید اشتراک یا شروع دوره سه‌روزه رایگان،
                    ابتدا وارد حساب کاربری شوید یا ثبت‌نام کنید.
                  </p>

                  <div className="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
                    <Link href="/login">
                      <Button className="h-11 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-7 text-sm font-bold text-[#07111f] hover:opacity-90 sm:w-auto">
                        ثبت‌نام و شروع رایگان
                      </Button>
                    </Link>

                    <Link href="/login">
                      <Button
                        variant="outline"
                        className="h-11 w-full border-white/10 px-7 text-sm text-gray-300 hover:bg-white/5 sm:w-auto"
                      >
                        ورود به حساب
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mb-4">
                    <h3 className="mb-1 text-xs font-bold text-gray-200">
                      روش پرداخت را انتخاب کنید
                    </h3>
                    <p className="text-[10px] text-gray-500">
                      پس از انتخاب روش پرداخت، جزئیات سفارش را تأیید کنید.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      aria-pressed={paymentMethod === "zibal"}
                      onClick={() => setPaymentMethod("zibal")}
                      className={`relative flex items-center gap-3 rounded-xl border p-4 text-right transition ${
                        paymentMethod === "zibal"
                          ? "border-[#d6ad60]/70 bg-[#d6ad60]/[0.07] ring-1 ring-[#d6ad60]/20"
                          : "border-white/[0.07] bg-black/20 hover:border-white/15"
                      }`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#d6ad60]/10">
                        <Wallet className="h-5 w-5 text-[#d6ad60]" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold text-white">
                          پرداخت آنلاین
                        </p>
                        <p className="mt-1 text-[10px] text-gray-500">
                          از طریق درگاه زیبال
                        </p>
                      </div>

                      {paymentMethod === "zibal" && (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-[#d6ad60]" />
                      )}
                    </button>

                    <button
                      type="button"
                      aria-pressed={paymentMethod === "card"}
                      onClick={() => setPaymentMethod("card")}
                      className={`relative flex items-center gap-3 rounded-xl border p-4 text-right transition ${
                        paymentMethod === "card"
                          ? "border-[#d6ad60]/70 bg-[#d6ad60]/[0.07] ring-1 ring-[#d6ad60]/20"
                          : "border-white/[0.07] bg-black/20 hover:border-white/15"
                      }`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#d6ad60]/10">
                        <CreditCard className="h-5 w-5 text-[#d6ad60]" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold text-white">
                          کارت‌به‌کارت
                        </p>
                        <p className="mt-1 text-[10px] text-gray-500">
                          ثبت درخواست و بررسی توسط پشتیبانی
                        </p>
                      </div>

                      {paymentMethod === "card" && (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-[#d6ad60]" />
                      )}
                    </button>
                  </div>

                  <div className="mt-5 rounded-xl border border-white/[0.06] bg-black/20 p-4">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="text-xs text-gray-400">
                        خلاصه سفارش
                      </span>
                      <span className="rounded-full bg-[#d6ad60]/10 px-2.5 py-1 text-[9px] font-bold text-[#d6ad60]">
                        اشتراک حرفه‌ای
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-3 text-xs">
                      <span className="text-gray-400">
                        {selectedPlanData?.title || "مدت اشتراک"}
                      </span>
                      <span className="font-bold text-white">
                        {selectedPlanData
                          ? formatPrice(selectedPlanData.price)
                          : "—"}{" "}
                        تومان
                      </span>
                    </div>

                    <div className="my-3 border-t border-dashed border-white/[0.08]" />

                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-bold text-gray-300">
                        مبلغ نهایی
                      </span>
                      <span className="text-lg font-black text-[#e5c786]">
                        {selectedPlanData
                          ? formatPrice(selectedPlanData.price)
                          : "—"}
                        <span className="mr-1 text-[10px] font-normal text-gray-400">
                          تومان
                        </span>
                      </span>
                    </div>
                  </div>

                  <Button
                    onClick={openConfirm}
                    disabled={
                      loading ||
                      plansLoading ||
                      plansError ||
                      !selectedPlanData
                    }
                    className="mt-4 h-12 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-extrabold text-[#07111f] shadow-lg shadow-[#d6ad60]/10 transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {loading
                      ? "در حال پردازش..."
                      : `ادامه و تأیید خرید ${selectedPlanData?.title || ""}`}
                    <ChevronLeft className="mr-2 h-4 w-4" />
                  </Button>

                  <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[10px] text-gray-500">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                    اطلاعات پرداخت شما از طریق مسیر امن پرداخت پردازش می‌شود.
                  </p>
                </>
              )}
            </div>
          </motion.section>

          {/* توضیح تکمیلی */}
          <section className="mt-8 rounded-xl border border-white/[0.05] bg-white/[0.02] p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#d6ad60]" />
              <div>
                <h2 className="text-xs font-bold text-gray-300">
                  درباره اشتراک تریدمون
                </h2>
                <p className="mt-1 text-[11px] leading-7 text-gray-500">
                  تریدمون ابزارهایی برای تحلیل تکنیکال بازار رمزارزها،
                  فارکس و بورس تهران، بررسی سیگنال‌ها، مشاهده عمق بازار
                  و استفاده از ابزارهای هوشمند ارائه می‌کند. اطلاعات و
                  تحلیل‌های این پلتفرم جنبه کمکی و تحلیلی دارند و به‌تنهایی
                  تضمین‌کننده نتیجه معاملات نیستند.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>

      <PublicFooter />

      {/* دیالوگ تأیید خرید */}
      <Dialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <DialogContent className="max-h-[90vh] max-w-md overflow-y-auto border-white/10 bg-[#08121e] text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-[#e5c786]">
              <ShieldCheck className="h-5 w-5" />
              تأیید نهایی خرید
            </DialogTitle>
          </DialogHeader>

          {selectedPlanData && (
            <div className="space-y-4 py-2">
              <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/[0.06] p-4 text-center">
                <p className="text-[11px] text-gray-400">
                  اشتراک انتخاب‌شده
                </p>

                <p className="mt-1 text-lg font-extrabold text-white">
                  {selectedPlanData.title}
                </p>

                <p className="mt-2 text-2xl font-black text-[#e5c786]">
                  {formatPrice(selectedPlanData.price)}
                  <span className="mr-1.5 text-xs font-normal text-gray-400">
                    تومان
                  </span>
                </p>
              </div>

              {paymentMethod === "zibal" && (
                <div className="space-y-2">
                  <div className="rounded-lg border border-amber-400/15 bg-amber-400/[0.05] p-3 text-[11px] leading-6 text-amber-200">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="mt-1 h-3.5 w-3.5 shrink-0" />
                      <span>
                        برای بازشدن صحیح درگاه پرداخت، لطفاً وی‌پی‌ان خود
                        را خاموش کنید.
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-blue-400/15 bg-blue-400/[0.05] p-3 text-[11px] leading-6 text-blue-200">
                    <div className="flex items-start gap-2">
                      <Info className="mt-1 h-3.5 w-3.5 shrink-0" />
                      <span>
                        پس از تکمیل پرداخت، به‌طور خودکار به سایت
                        بازمی‌گردید.
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-orange-400/15 bg-orange-400/[0.05] p-3 text-[11px] leading-6 text-orange-200">
                    <div className="flex items-start gap-2">
                      <Clock className="mt-1 h-3.5 w-3.5 shrink-0" />
                      <span>
                        در صورت پرداخت ناموفق، مبلغ معمولاً تا ۷۲ ساعت
                        توسط بانک عودت داده می‌شود. در صورت بروز مشکل،
                        تیکت پشتیبانی ثبت کنید.
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {isCardPayment && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/[0.05] p-4">
                    <p className="mb-2 text-center text-[10px] text-gray-400">
                      اطلاعات کارت مقصد
                    </p>

                    <p
                      dir="ltr"
                      className="text-center font-mono text-base font-bold tracking-wider text-white"
                    >
                      {CARD_NUMBER}
                    </p>


                    <div className="mt-3 flex justify-center">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={copyCard}
                        className="h-8 gap-1.5 rounded-full border-white/10 px-4 text-[10px] text-[#e5c786] hover:bg-[#d6ad60]/10"
                      >
                        {copied ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                        {copied ? "کپی شد" : "کپی شماره کارت"}
                      </Button>
                    </div>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-[11px] text-gray-400">
                      زمان واریز <span className="text-red-400">*</span>
                    </label>

                    <Input
                      placeholder="1404/10/25 - 16:42"
                      value={paymentTime}
                      onChange={(e) => setPaymentTime(e.target.value)}
                      className="h-10 border-white/[0.08] bg-black/30 text-center text-sm text-white placeholder:text-gray-600"
                      dir="ltr"
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-[11px] text-gray-400">
                      کد پیگیری (اختیاری)
                    </label>

                    <Input
                      placeholder="کد پیگیری تراکنش"
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      className="h-10 border-white/[0.08] bg-black/30 text-center text-sm text-white placeholder:text-gray-600"
                    />
                  </div>

                  <p className="rounded-lg border border-blue-400/10 bg-blue-400/[0.04] p-3 text-[10px] leading-6 text-gray-400">
                    پس از ثبت درخواست، اطلاعات واریز توسط پشتیبانی بررسی
                    می‌شود و پس از تأیید، اشتراک شما فعال خواهد شد.
                  </p>
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsConfirmOpen(false)}
                  className="h-11 flex-1 border-white/10 text-xs text-gray-300 hover:bg-white/5"
                >
                  بازگشت
                </Button>

                <Button
                  type="button"
                  onClick={executePayment}
                  disabled={
                    loading ||
                    (paymentMethod === "card" && !paymentTime.trim())
                  }
                  className="h-11 flex-1 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-xs font-extrabold text-[#07111f] hover:opacity-90 disabled:opacity-50"
                >
                  {loading
                    ? "در حال پردازش..."
                    : paymentMethod === "zibal"
                      ? "تأیید و پرداخت"
                      : "تأیید و ثبت درخواست"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* دیالوگ خطا */}
      <Dialog open={isErrorOpen} onOpenChange={setIsErrorOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#08121e] text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <XCircle className="h-5 w-5" />
              خطا در انجام درخواست
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <p className="text-sm leading-7 text-gray-300">
              {errorMessage}
            </p>

            <div className="rounded-lg border border-blue-400/15 bg-blue-400/[0.05] p-3 text-[11px] leading-6 text-blue-200">
              اگر مشکل ادامه داشت، می‌توانید از طریق تیکت پشتیبانی
              با ما در ارتباط باشید.
            </div>

            <div className="flex gap-2">
              <Link href="/dashboard/tickets" className="flex-1">
                <Button className="h-10 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-xs font-bold text-[#07111f]">
                  ثبت تیکت پشتیبانی
                </Button>
              </Link>

              <Button
                variant="outline"
                onClick={() => setIsErrorOpen(false)}
                className="h-10 flex-1 border-white/10 text-xs text-gray-300 hover:bg-white/5"
              >
                بستن
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}