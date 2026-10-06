"use client";

/**
 * BacktestPanel — پنل یکپارچه راستی‌آزمایی
 * ============================================================
 * نسخه ۱.۰ · فاز ۷
 *
 * ═══ ساختار ═══
 *   ┌──────────────────────────────┐
 *   │ [آمار] [تاریخچه]             │  ← Tab
 *   ├──────────────────────────────┤
 *   │ [همه] [نوبیتکس] [بیت‌پین] ...  │  ← فیلتر صرافی
 *   ├──────────────────────────────┤
 *   │ محتوای تب                    │
 *   └──────────────────────────────┘
 *
 * ═══ یکپارچگی ═══
 *   • هر دو تب از یه منبع (backtest endpoints)
 *   • فیلتر صرافی مشترک
 *   • رنگ‌بندی یکسان
 *   • بدون تکرار درخواست
 */

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { BacktestStats } from "./BacktestStats";
import { SignalHistory } from "./SignalHistory";

type Tab = "stats" | "history";

const SOURCES = [
  { key: "", label: "همه" },
  { key: "nobitex", label: "نوبیتکس" },
  { key: "bitpin", label: "بیت‌پین" },
  { key: "wallex", label: "والکس" },
  { key: "tabdeal", label: "تبدیل" },
  { key: "tsetmc", label: "بورس" },
];

export function BacktestPanel() {
  const [tab, setTab] = useState<Tab>("stats");
  const [source, setSource] = useState<string>("");

  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5" />
          راستی‌آزمایی
        </span>
      }
      subtitle="آمار و تاریخچه سیگنال‌ها"
      
    >
      <div className="space-y-3">
        {/* ═══ تب‌بندی ═══ */}
        <div className="flex gap-1 border-b border-border">
          <button
            onClick={() => setTab("stats")}
            className={`flex-1 rounded-t-md px-3 py-2 text-xs font-medium transition-all ${
              tab === "stats"
                ? "border-b-2 border-primary bg-primary/5 text-primary"
                : "text-muted-foreground hover:bg-muted/30"
            }`}
          >
            📊 آمار
          </button>
          <button
            onClick={() => setTab("history")}
            className={`flex-1 rounded-t-md px-3 py-2 text-xs font-medium transition-all ${
              tab === "history"
                ? "border-b-2 border-primary bg-primary/5 text-primary"
                : "text-muted-foreground hover:bg-muted/30"
            }`}
          >
            📜 تاریخچه
          </button>
        </div>

        {/* ═══ فیلتر صرافی ═══ */}
        <div className="grid grid-cols-3 gap-1 sm:grid-cols-6">
          {SOURCES.map((s) => (
            <button
              key={s.key}
              onClick={() => setSource(s.key)}
              className={`rounded-md border py-1 text-[10px] font-medium transition-all ${
                source === s.key
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:bg-muted/50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* ═══ محتوای تب ═══ */}
        {tab === "stats" && <BacktestStats source={source} />}
        {tab === "history" && <SignalHistory source={source} />}
      </div>
    </CollapsibleCard>
  );
}