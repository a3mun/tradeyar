"use client";

import { useState } from "react";
import { CheckCircle2, Settings, ChevronDown } from "lucide-react";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import { BacktestStats } from "./BacktestStats";
import { SignalHistory } from "./SignalHistory";
import { BacktestFilters } from "./BacktestFilters";

type Tab = "stats" | "history";

export function BacktestPanel() {
  const [tab, setTab] = useState<Tab>("stats");
  const [source, setSource] = useState("");
  const [profile, setProfile] = useState("");
  const [time, setTime] = useState("all");
  const [filtersOpen, setFiltersOpen] = useState(false);

  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5" />
          راستی‌آزمایی
        </span>
      }
      subtitle="آمار و تاریخچه سیگنال‌ها"
      actions={
        // ═══ 🔴 دکمه تنظیمات — خارج از button اصلی ═══
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setFiltersOpen((v) => !v);
          }}
          className={`flex items-center gap-1 rounded-md border px-2 py-0.5 text-[9px] font-normal transition-colors ${
            filtersOpen
              ? "border-primary/40 bg-primary/10 text-primary"
              : "border-border bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          }`}
          aria-expanded={filtersOpen}
          aria-label="تنظیمات فیلترها"
          title="تنظیمات"
        >
          <Settings className="h-2.5 w-2.5" />
          تنظیمات
          <ChevronDown
            className={`h-2.5 w-2.5 transition-transform ${
              filtersOpen ? "rotate-180" : ""
            }`}
          />
        </button>
      }
    >
      <div className="space-y-3">
        {filtersOpen && (
          <div className="rounded-md border border-border/40 bg-muted/10 p-3">
            <BacktestFilters
              source={source}
              onSourceChange={setSource}
              profile={profile}
              onProfileChange={setProfile}
              time={time}
              onTimeChange={setTime}
            />
          </div>
        )}

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

        {tab === "stats" && (
          <BacktestStats source={source} profile={profile} time={time} />
        )}
        {tab === "history" && (
          <SignalHistory source={source} profile={profile} />
        )}
      </div>
    </CollapsibleCard>
  );
}