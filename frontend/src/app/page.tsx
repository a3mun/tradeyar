"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { motion } from "framer-motion";
import { Lock, CreditCard, LayoutDashboard, Home } from "lucide-react";
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
import { BacktestPanel } from "@/components/backtest/BacktestPanel";
import { SupportResistance } from "@/components/signal/SupportResistance";
import { AIAnalysis } from "@/components/signal/AIAnalysis";
import { useSignalData } from "@/hooks/useSignalData";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { StickyMiniHeader } from "@/components/layout/StickyMiniHeader";

export default function HomePage() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  // ⬅️ چک کردن لاگین و اشتراک
  useEffect(() => {
    const token = getToken();
    const user = getUser();

    if (!token || !user) {
      router.replace("/login");
      return;
    }

    // ادمین‌ها همیشه دسترسی دارن
    if (user.is_admin) {
      setHasAccess(true);
      setIsChecking(false);
      return;
    }

    // چک کردن اشتراک
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
        const sub = data.subscription;
        // ⬅️ تغییر: چک هم status هم end_date (defense in depth)
        const endDate = sub?.end_date ? new Date(sub.end_date) : null;
        const now = new Date();
        const isExpired = endDate ? endDate.getTime() < now.getTime() : false;

        if (sub && sub.status === "active" && !isExpired) {
          setHasAccess(true);
        } else {
          setHasAccess(false);
        }
      })
      .catch(() => {
        setHasAccess(false);
      })
      .finally(() => {
        setIsChecking(false);
      });
  }, [router]);

  const { data } = useSignalData();
  const { ticker, source, timeframe, marketType, riskProfile } = useAppStore();

  const coherent = sourceSupportsPair(source, ticker);

  // ⬅️ در حال چک کردن
  if (isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#d6ad60]"></div>
      </div>
    );
  }

  // ⬅️ کاربر بدون اشتراک: صفحه اصلی بمونه، ولی کارت خرید اشتراک ببینه
  if (!hasAccess) {
    return (
      <div className="min-h-screen bg-[#07111f] text-white">
        <Header />
        <main className="container mx-auto max-w-2xl px-4 py-12 sm:py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-6 sm:p-10 text-center shadow-2xl"
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
                  <CreditCard className="h-4 w-4" /> خرید / تمدید اشتراک
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="outline" className="h-11 w-full sm:w-auto gap-2 border-white/20 text-white hover:bg-white/5">
                  <LayoutDashboard className="h-4 w-4" /> داشبورد من
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

      <div className="container mx-auto flex gap-6 px-4 py-4 sm:py-6">
        <Sidebar />

        <main className="min-w-0 flex-1 space-y-3 sm:space-y-4">
          <SymbolSelector />
          <WatchlistCard />

          <div className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2 xl:items-start">
            <div className="contents xl:flex xl:flex-col xl:gap-3 sm:xl:gap-4">
              <div className="order-1 xl:order-none">
                <SignalCard key={[ticker, source, timeframe, marketType, riskProfile].join("-")} />
              </div>
              <div className="order-3 xl:order-none"><OrderBookPanel /></div>
              <div className="order-5 xl:order-none"><AIAnalysis /></div>
              <div className="order-7 xl:order-none"><DeepAnalysis /></div>
              <div className="order-9 xl:order-none">
                {coherent ? <Scanner /> : (
                  <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-500">
                    ⚠️ اسکنر برای این جفت (صرافی، نماد) فعال نیست.
                  </div>
                )}
              </div>
            </div>

            <div className="contents xl:flex xl:flex-col xl:gap-3 sm:xl:gap-4">
              <div className="order-2 xl:order-none"><TFTable /></div>
              <div className="order-4 xl:order-none">
                <div className="grid grid-cols-2 gap-3">
                  <FearGreed />
                  <SupportResistance />
                </div>
              </div>
              {data?.checklist?.items && data.checklist.items.length > 0 && (
                <div className="order-6 xl:order-none">
                  <Checklist data={data.checklist} />
                </div>
              )}
              <div className="order-8 xl:order-none"><PriceComparison /></div>
              <div className="order-10 xl:order-none"><BacktestPanel /></div>
            </div>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
}