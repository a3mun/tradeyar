"use client";

/**
 * صفحه‌ی اصلی Trademun — چیدمان نسخه ۲.۰
 * ============================================================
 * ═══ چیدمان دسکتاپ ═══
 *
 *   SymbolSelector (شامل Popular)
 *   ─────────────────────────────
 *   WatchlistCard (نوار بسته، باز شدنی)
 *   ─────────────────────────────
 *   TFTable        | SignalCard
 *   ─────────────────────────────
 *   OrderBookPanel | FearGreed
 *   ─────────────────────────────
 *   DeepAnalysis   | Checklist
 *                  | PriceComparison
 *   ─────────────────────────────
 *   Scanner
 *   ─────────────────────────────
 *   BacktestStats  | SignalHistory
 *
 * ═══ چیدمان موبایل ═══
 *   SymbolSelector
 *   WatchlistCard (نوار بسته)
 *   SignalCard
 *   OrderBookPanel
 *   TFTable
 *   Checklist (نوار بسته)
 *   DeepAnalysis
 *   PriceComparison
 *   FearGreed
 *   Scanner
 *   BacktestStats
 *   SignalHistory (نوار بسته)
 *
 * ═══ نکته ═══
 *   **بستن کشو محاسبه را متوقف نمی‌کند.** چک‌لیست از
 *   ``useSignalData`` میاد، راستی‌آزمایی از اسکجولر backend.
 *   کشو فقط ``hidden`` می‌کنه، unmount نمی‌کنه.
 */

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
import { useSignalData } from "@/hooks/useSignalData";
import { useAppStore } from "@/store/useAppStore";
import { sourceSupportsPair } from "@/lib/sources";
import { StickyMiniHeader } from "@/components/layout/StickyMiniHeader";


export default function HomePage() {
  const { data } = useSignalData();
  const { ticker, source } = useAppStore();

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
          {/* ═══ جستجو + ۶ نماد برتر ═══ */}
          <SymbolSelector />

          {/* ═══ واچ‌لیست — نوار بسته در موبایل، باز در دسکتاپ ═══ */}
          <WatchlistCard />

          {/*
            ═══ هسته‌ی تحلیل ═══
            موبایل: SignalCard اول، بعد TFTable
            دسکتاپ: TFTable چپ، SignalCard راست
          */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2">
            <div className="order-first xl:order-2">
              <SignalCard />
            </div>
            <div className="order-last xl:order-1">
              <TFTable />
            </div>
          </div>

          {/* ═══ عمق بازار + ترس و طمع ═══ */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2">
            <OrderBookPanel />
            <FearGreed />
          </div>

          {/*
            ═══ تحلیل عمیق | چک‌لیست + مقایسه قیمت ═══
            دسکتاپ:
              ستون چپ: DeepAnalysis
              ستون راست: Checklist، بعدش PriceComparison
            موبایل:
              Checklist (نوار بسته) → DeepAnalysis → PriceComparison
          */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2">
            {/* ─── ستون چپ ─── */}
            <div className="order-2 xl:order-1">
              <DeepAnalysis />
            </div>

            {/* ─── ستون راست ─── */}
            <div className="order-1 xl:order-2 space-y-3 sm:space-y-4">
              {data?.checklist?.items && data.checklist.items.length > 0 && (
                <Checklist data={data.checklist} />
              )}
              <PriceComparison />
            </div>
          </div>

          {/* ═══ اسکنر فرصت‌ها ═══ */}
          {coherent ? (
            <Scanner />
          ) : (
            <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-500">
              ⚠️ اسکنر برای این جفت (صرافی، نماد) فعال نیست —
              صرافی انتخاب‌شده این بازار را ندارد.
              برای فعال شدن، صرافی یا نماد را عوض کن.
            </div>
          )}

          {/* ═══ راستی‌آزمایی — تمام عرض ═══ */}
          <BacktestPanel />
        </main>
      </div>

      <Footer />
    </div>
  );
}