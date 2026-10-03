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
import { Scanner } from "@/components/scan/Scanner";
import { BacktestStats } from "@/components/backtest/BacktestStats";
import { SignalHistory } from "@/components/backtest/SignalHistory";
import { useSignalData } from "@/hooks/useSignalData";

export default function HomePage() {
  const { data } = useSignalData();

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="w-full overflow-hidden">
        <Marquee />
      </div>

      <div className="container mx-auto flex gap-6 px-4 py-6">
        <Sidebar />

        <main className="min-w-0 flex-1 space-y-4">
          <SymbolSelector />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <SignalCard />
            <TFTable />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <DeepAnalysis />
            </div>
            <div className="space-y-4">
              {data?.checklist?.items && data.checklist.items.length > 0 && (
                <Checklist data={data.checklist} />
              )}
              <FearGreed />
              <PriceComparison />
            </div>
          </div>

          <Scanner />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <BacktestStats />
            <SignalHistory />
          </div>


        </main>
      </div>

      <Footer />
    </div>
  );
}