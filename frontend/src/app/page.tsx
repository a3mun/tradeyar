"use client";

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
  const { data } = useSignalData();
  const { ticker, source, timeframe, marketType, riskProfile } = useAppStore();

  const coherent = sourceSupportsPair(source, ticker);

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
          {/* ═══ ۱. جستجو + ۶ نماد (همیشه بالا، تمام عرض) ═══ */}
          <SymbolSelector />

          {/* ═══ ۲. واچ‌لیست ═══ */}
          <WatchlistCard />

          {/*
            ═══════════════════════════════════════════════════════
            🎯 چیدمان اصلی — موبایل با order-*، دسکتاپ دو ستونه
            ═══════════════════════════════════════════════════════
            • موبایل: grid-cols-1 + contents → order-* کار می‌کنه
            • دسکتاپ: xl:flex xl:flex-col → دو ستونه
          */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2 xl:items-start">
            {/* ═══════════════════════════════════════════════
                🅰️ ستون چپ دسکتاپ
                در موبایل: contents (بچه‌ها مستقیم زیر grid)
            ═══════════════════════════════════════════════ */}
            <div className="contents xl:flex xl:flex-col xl:gap-3 sm:xl:gap-4">
              {/* ۱. کارت سیگنال */}
              <div className="order-1 xl:order-none">
                <SignalCard
                  key={[
                    ticker,
                    source,
                    timeframe,
                    marketType,
                    riskProfile,
                  ].join("-")}
                />
              </div>

              {/* ۳. عمق بازار */}
              <div className="order-3 xl:order-none">
                <OrderBookPanel />
              </div>

              {/* ۵. تحلیل هوش مصنوعی */}
              <div className="order-5 xl:order-none">
                <AIAnalysis />
              </div>

              {/* ۷. تحلیل عمیق */}
              <div className="order-7 xl:order-none">
                <DeepAnalysis />
              </div>

              {/* ۹. اسکنر فرصت‌ها */}
              <div className="order-9 xl:order-none">
                {coherent ? (
                  <Scanner />
                ) : (
                  <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-500">
                    ⚠️ اسکنر برای این جفت (صرافی، نماد) فعال نیست.
                  </div>
                )}
              </div>
            </div>

            {/* ═══════════════════════════════════════════════
                🅱️ ستون راست دسکتاپ
                در موبایل: contents (بچه‌ها مستقیم زیر grid)
            ═══════════════════════════════════════════════ */}
            <div className="contents xl:flex xl:flex-col xl:gap-3 sm:xl:gap-4">
              {/* ۲. جدول تایم‌فریم */}
              <div className="order-2 xl:order-none">
                <TFTable />
              </div>

              {/* ۴. ترس و طمع + حمایت و مقاومت */}
              <div className="order-4 xl:order-none">
                <div className="grid grid-cols-2 gap-3">
                  <FearGreed />
                  <SupportResistance />
                </div>
              </div>

              {/* ۶. چک‌لیست */}
              {data?.checklist?.items && data.checklist.items.length > 0 && (
                <div className="order-6 xl:order-none">
                  <Checklist data={data.checklist} />
                </div>
              )}

              {/* ۸. مقایسه قیمت */}
              <div className="order-8 xl:order-none">
                <PriceComparison />
              </div>

              {/* ۱۰. راستی‌آزمایی */}
              <div className="order-10 xl:order-none">
                <BacktestPanel />
              </div>
            </div>
          </div>
        </main>
      </div>

      <Footer />
    </div>
  );
}