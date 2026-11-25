
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getToken, getUser } from "@/lib/auth";
import { motion } from "framer-motion";
import {
  Lock,
  CreditCard,
  LayoutDashboard,
  Brain,
  MessageSquare,
  Landmark,
  Search,
  CheckCircle2,
  Wallet,
  Calculator,
  Calendar,
  BarChart3,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { TradingPsychologyBanner } from "@/components/signal/TradingPsychologyBanner";
import { Header } from "@/components/layout/Header";
import { Marquee } from "@/components/layout/Marquee";
import { Sidebar } from "@/components/layout/Sidebar";
import { Footer } from "@/components/layout/Footer";
import { SymbolSelector } from "@/components/signal/SymbolSelector";
import { SignalCard } from "@/components/signal/SignalCard";
import { TFTable } from "@/components/signal/TFTable";
import { FearGreed } from "@/components/signal/FearGreed";
import { OrderBookPanel } from "@/components/signal/OrderBookPanel";
import { WatchlistCard } from "@/components/signal/WatchlistCard";
import { SupportResistance } from "@/components/signal/SupportResistance";

import { useSignalData } from "@/hooks/useSignalData";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { StickyMiniHeader } from "@/components/layout/StickyMiniHeader";
import { CollapsibleSection } from "@/components/ui/collapsible-section";

// نمایش هنگام دریافت فایل هر بخش
const SectionChunkLoading = () => (
  <div className="p-5 text-center text-xs text-slate-400">
    در حال بارگذاری بخش...
  </div>
);

// بارگذاری تنبل کامپوننت‌های داخل منوهای کشویی

const AIAnalysis = dynamic(
  () =>
    import("@/components/signal/AIAnalysis").then(
      (mod) => mod.AIAnalysis
    ),
  { loading: SectionChunkLoading }
);

const DeepAnalysis = dynamic(
  () =>
    import("@/components/signal/DeepAnalysis").then(
      (mod) => mod.DeepAnalysis
    ),
  { loading: SectionChunkLoading }
);

const FundamentalAnalysisPlaceholder = dynamic(
  () =>
    import("@/components/signal/FundamentalAnalysisPlaceholder").then(
      (mod) => mod.FundamentalAnalysisPlaceholder
    ),
  { loading: SectionChunkLoading }
);

const Scanner = dynamic(
  () =>
    import("@/components/scan/Scanner").then(
      (mod) => mod.Scanner
    ),
  { loading: SectionChunkLoading }
);

const Checklist = dynamic(
  () =>
    import("@/components/signal/Checklist").then(
      (mod) => mod.Checklist
    ),
  { loading: SectionChunkLoading }
);

const PriceComparison = dynamic(
  () =>
    import("@/components/signal/PriceComparison").then(
      (mod) => mod.PriceComparison
    ),
  { loading: SectionChunkLoading }
);

const PositionSizeCalculator = dynamic(
  () =>
    import("@/components/signal/PositionSizeCalculatorPlaceholder").then(
      (mod) => mod.PositionSizeCalculatorPlaceholder
    ),
  { loading: SectionChunkLoading }
);

const EconomicCalendarPlaceholder = dynamic(
  () =>
    import("@/components/signal/EconomicCalendarPlaceholder").then(
      (mod) => mod.EconomicCalendarPlaceholder
    ),
  { loading: SectionChunkLoading }
);

const StatisticsBox = dynamic(
  () =>
    import("@/components/signal/StatisticsBox").then(
      (mod) => mod.StatisticsBox
    ),
  { loading: SectionChunkLoading }
);

export default function HomePage() {
  const router = useRouter();

  const [isChecking, setIsChecking] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  const [plan, setPlan] = useState<"free" | "pro" | "admin">("free");
  const isPro = plan === "pro" || plan === "admin";

  const { data } = useSignalData();

  const { ticker, source } = useAppStore();

  useEffect(() => {
    const token = getToken();
    const user = getUser();

    if (!token || !user) {
      router.replace("/login");
      return;
    }

    if (user.is_admin) {
      setHasAccess(true);
      setPlan("admin");
      setIsChecking(false);
      return;
    }

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    fetch(`${apiUrl}/subscription/my`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        const sub = data.subscription;
        const endDate = sub?.end_date ? new Date(sub.end_date) : null;
        const now = new Date();

        const isExpired = endDate
          ? endDate.getTime() < now.getTime()
          : false;

        if (sub && sub.status === "active" && !isExpired) {
          setHasAccess(true);

          if (sub.plan && sub.plan !== "free") {
            setPlan("pro");
          }

          localStorage.setItem(
            "trademun_subscription",
            JSON.stringify(sub)
          );
        } else {
          setHasAccess(false);
          localStorage.removeItem("trademun_subscription");
        }
      })
      .catch(() => {
        setHasAccess(false);
        localStorage.removeItem("trademun_subscription");
      })
      .finally(() => {
        setIsChecking(false);
      });
  }, [router]);

  const coherent = sourceSupportsPair(source, ticker);

  if (isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#051118]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#d6ad60]" />
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="min-h-screen bg-[#07111f] text-white">
        <Header />

        <main className="container mx-auto max-w-2xl px-4 py-12 sm:py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#051118] to-[#051118] p-6 sm:p-10 text-center shadow-2xl"
          >
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[#d6ad60]/10">
              <Lock className="h-8 w-8 text-[#d6ad60]" />
            </div>

            <h2 className="mb-3 text-2xl sm:text-3xl font-bold">
              دسترسی به تحلیل‌ها نیازمند اشتراک فعال است
            </h2>

            <p className="mb-6 text-sm leading-relaxed text-gray-400">
              برای مشاهده سیگنال‌ها، تحلیل هوش مصنوعی، اسکنر بازار و بررسی قیمت لحظه‌ای،
              از داشبورد خود اشتراک تهیه کن یا درخواست تمدید بده.
            </p>

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/dashboard">
                <Button className="h-11 w-full sm:w-auto gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold hover:opacity-90">
                  <CreditCard className="h-4 w-4" />
                  خرید / تمدید اشتراک
                </Button>
              </Link>

              <Link href="/dashboard">
                <Button
                  variant="outline"
                  className="h-11 w-full sm:w-auto gap-2 border-white/20 text-white hover:bg-white/5"
                >
                  <LayoutDashboard className="h-4 w-4" />
                  داشبورد من
                </Button>
              </Link>
            </div>
          </motion.div>
        </main>

        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <StickyMiniHeader />

      <div className="w-full overflow-hidden">
        <Marquee />
      </div>

      <div className="container mx-auto flex flex-col lg:flex-row gap-6 px-4 py-4 sm:py-6">
        <Sidebar />

        <main className="min-w-0 flex-1 space-y-4 sm:space-y-6">
          <SymbolSelector />
          <WatchlistCard />

          <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-4 sm:gap-6">

            {/* ستون چپ */}
            <div className="contents lg:flex lg:flex-col lg:gap-4 lg:min-w-0">

              <div className="order-1 lg:order-none min-w-0">
                <SignalCard />
              </div>

              <div className="order-4 lg:order-none min-w-0">
                <OrderBookPanel />
              </div>

              <div className="order-4 lg:order-none min-w-0">
                <TradingPsychologyBanner />
              </div>

              <div className="order-5 lg:order-none min-w-0">
                <CollapsibleSection
                  id="ai-analysis"
                  title="مشاور هوشمند"
                  icon={<Brain className="h-4 w-4" />}
                  subtitle="تحلیل و بررسی با هوش مصنوعی"
                >
                    <AIAnalysis />
                </CollapsibleSection>
              </div>

              <div className="order-6 lg:order-none min-w-0">
                <CollapsibleSection
                  id="deep-analysis"
                  title="تحلیل تکنیکال"
                  icon={<MessageSquare className="h-4 w-4" />}
                  subtitle="بررسی عمیق سیگنال"
                >
                  <DeepAnalysis />
                </CollapsibleSection>
              </div>

              <div className="order-8 lg:order-none min-w-0">
                <CollapsibleSection
                  id="fundamental-analysis"
                  title="تحلیل بنیادین (فاندامنتال)"
                  icon={<Landmark className="h-4 w-4" />}
                  subtitle="بررسی عوامل اقتصادی و محرک‌های بازار - به زودی"
                >
                  <FundamentalAnalysisPlaceholder />
                </CollapsibleSection>
              </div>

              <div className="order-9 lg:order-none min-w-0">
                {coherent ? (
                  <CollapsibleSection
                    id="scanner"
                    title="اسکنر فرصت‌ها"
                    icon={<Search className="h-4 w-4" />}
                    subtitle="شناسایی فرصت‌های بازار"
                  >
                      <Scanner />
                  </CollapsibleSection>
                ) : (
                  <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-500">
                    ⚠️ اسکنر برای این جفت (صرافی، نماد) فعال نیست.
                  </div>
                )}
              </div>
            </div>

            {/* ستون راست */}
            <div className="contents lg:flex lg:flex-col lg:gap-4 lg:min-w-0">

              <div className="order-2 lg:order-none min-w-0">
                <TFTable />
              </div>

              <div className="order-3 lg:order-none min-w-0">
                <div className="grid grid-cols-2 gap-3 sm:gap-4 min-w-0">
                  <FearGreed />
                  <SupportResistance />
                </div>
              </div>

              <div className="order-7 lg:order-none min-w-0">
                <CollapsibleSection
                  id="checklist"
                  title="چک‌لیست اندیکاتورها"
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  subtitle="بررسی نهایی وضعیت اندیکاتورها"
                >
                  {data ? (
                    <Checklist data={data.checklist} />
                  ) : (
                    <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">
                      در حال دریافت چک‌لیست...
                    </div>
                  )}
                </CollapsibleSection>
              </div>

              <div className="order-10 lg:order-none min-w-0">
                <CollapsibleSection
                  id="price-comparison"
                  title="مقایسه قیمت صرافی‌ها"
                  icon={<Wallet className="h-4 w-4" />}
                  subtitle="مقایسه قیمت لحظه‌ای ۴ صرافی"
                >
                  <PriceComparison />
                </CollapsibleSection>
              </div>

              <div className="order-11 lg:order-none min-w-0">
                <CollapsibleSection
                  id="position-calculator"
                  title="ماشین‌حساب سود و ضرر"
                  icon={<Calculator className="h-4 w-4" />}
                  subtitle="مدیریت سرمایه، حجم معامله و محاسبه سود و زیان"
                >
                  <PositionSizeCalculator />
                </CollapsibleSection>
              </div>

              <div className="order-12 lg:order-none min-w-0">
                <CollapsibleSection
                  id="economic-calendar"
                  title="تقویم اقتصادی فارکس"
                  icon={<Calendar className="h-4 w-4" />}
                  subtitle="رویدادهای مهم اقتصاد جهان"
                >
                  <EconomicCalendarPlaceholder />
                </CollapsibleSection>
              </div>

              <div className="order-13 lg:order-none min-w-0">
                <CollapsibleSection
                  id="statistics"
                  title="آمار عملکرد"
                  icon={<BarChart3 className="h-4 w-4" />}
                  subtitle="خلاصه عملکرد و دقت پیش‌بینی"
                >
                  <StatisticsBox />
                </CollapsibleSection>
              </div>

            </div>
          </div>
        </main>
      </div>

      <Footer />
    </div>
  );
}
