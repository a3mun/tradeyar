"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { motion } from "framer-motion";
import { Lock, CreditCard, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";

import { Header } from "@/components/layout/Header";
import { Marquee } from "@/components/layout/Marquee";
import { Sidebar } from "@/components/layout/Sidebar";
import { Footer } from "@/components/layout/Footer";
import { SymbolSelector } from "@/components/signal/SymbolSelector";
import { SignalCard } from "@/components/signal/SignalCard";
import { TFTable } from "@/components/signal/TFTable";
import { Checklist } from "@/components/signal/Checklist";
import { DeepAnalysis } from "@/components/signal/DeepAnalysis";
import { FearGreed } from "@/components/signal/FearGreed";
import { PriceComparison } from "@/components/signal/PriceComparison";
import { OrderBookPanel } from "@/components/signal/OrderBookPanel";
import { WatchlistCard } from "@/components/signal/WatchlistCard";
import { Scanner } from "@/components/scan/Scanner";
import { StatisticsBox } from "@/components/signal/StatisticsBox";
import { SupportResistance } from "@/components/signal/SupportResistance";
import { AIAnalysis } from "@/components/signal/AIAnalysis";
import { EconomicCalendarPlaceholder } from "@/components/signal/EconomicCalendarPlaceholder";
import { PositionSizeCalculatorPlaceholder } from "@/components/signal/PositionSizeCalculatorPlaceholder";
import { FundamentalAnalysisPlaceholder } from "@/components/signal/FundamentalAnalysisPlaceholder";

import { useSignalData } from "@/hooks/useSignalData";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { StickyMiniHeader } from "@/components/layout/StickyMiniHeader";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { ProOverlay } from "@/components/ui/pro-overlay";

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

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    fetch(`${apiUrl}/subscription/my`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        const sub = data.subscription;
        const endDate = sub?.end_date ? new Date(sub.end_date) : null;
        const now = new Date();

        const isExpired = endDate ? endDate.getTime() < now.getTime() : false;

        if (sub && sub.status === "active" && !isExpired) {
          setHasAccess(true);
          if (sub.plan && sub.plan !== "free") {
            setPlan("pro");
          }
          localStorage.setItem("trademun_subscription", JSON.stringify(sub));
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
            className="rounded-3xl border border-[#dad60]/20 bg-gradient-to-br from-[#051118] to-[#051118] p-6 sm:p-10 text-center shadow-2xl"
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

        <main className="min-w-0 flex-1 space-y-4 sm:space-y-6"> {/* 🔴 space افزایش یافت */}
          <SymbolSelector />
          <WatchlistCard />

          <div className="grid grid-cols-1 lg:grid-cols-2 items-start gap-4 sm:gap-6"> {/* 🔴 gap افزایش یافت */}
            {/* ═══════════════ LEFT COLUMN ═══════════════ */}
            <div className="contents lg:flex lg:flex-col lg:gap-4 lg:min-w-0">
              <div className="order-1 lg:order-none min-w-0">
                <SignalCard />
              </div>

              <div className="order-4 lg:order-none min-w-0">
                <OrderBookPanel />
              </div>

              <div className="order-5 lg:order-none min-w-0">
                <CollapsibleSection
                  id="ai-analysis"
                  title="مشاور هوشمند"
                  icon="🧠"
                  subtitle="تحلیل و بررسی با هوش مصنوعی"
                  isLocked={!isPro}
                >
                  <ProOverlay feature="مشاور هوشمند">
                    <AIAnalysis />
                  </ProOverlay>
                </CollapsibleSection>
              </div>

              <div className="order-6 lg:order-none min-w-0">
                <CollapsibleSection
                  id="deep-analysis"
                  title="تحلیل تکنیکال"
                  icon="💬"
                  subtitle="بررسی عمیق سیگنال"
                >
                  <DeepAnalysis />
                </CollapsibleSection>
              </div>

              <div className="order-8 lg:order-none min-w-0">
                <CollapsibleSection
                  id="fundamental-analysis"
                  title="تحلیل بنیادین (فاندامنتال)"
                  icon="🏛️"
                  subtitle="بررسی بنیادین بازار — به زودی"
                >
                  <FundamentalAnalysisPlaceholder />
                </CollapsibleSection>
              </div>

              <div className="order-9 lg:order-none min-w-0">
                {coherent ? (
                  <CollapsibleSection
                    id="scanner"
                    title="اسکنر فرصت‌ها"
                    icon="🔍"
                    subtitle="شناسایی فرصت‌های بازار"
                    isLocked={!isPro}
                  >
                    <ProOverlay feature="اسکنر فرصت‌ها">
                      <Scanner />
                    </ProOverlay>
                  </CollapsibleSection>
                ) : (
                  <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-500">
                    ⚠️ اسکنر برای این جفت (صرافی، نماد) فعال نیست.
                  </div>
                )}
              </div>
            </div>

            {/* ═══════════════ RIGHT COLUMN ═══════════════ */}
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
                  icon="✅"
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
                  icon="💰"
                  subtitle="مقایسه قیمت لحظه‌ای ۴ صرافی"
                >
                  <PriceComparison />
                </CollapsibleSection>
              </div>

              <div className="order-11 lg:order-none min-w-0">
                <CollapsibleSection
                  id="position-calculator"
                  title="ماشین‌حساب سود و ضرر"
                  icon="🧮"
                  subtitle="محاسبه حجم پوزیشن — به زودی"
                >
                  <PositionSizeCalculatorPlaceholder />
                </CollapsibleSection>
              </div>

              <div className="order-12 lg:order-none min-w-0">
                <CollapsibleSection
                  id="economic-calendar"
                  title="تقویم اقتصادی فارکس"
                  icon="📅"
                  subtitle="رویدادهای مهم اقتصادی — به زودی"
                >
                  <EconomicCalendarPlaceholder />
                </CollapsibleSection>
              </div>

              <div className="order-13 lg:order-none min-w-0">
                <CollapsibleSection
                  id="statistics"
                  title="آمار عملکرد"
                  icon="📊"
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