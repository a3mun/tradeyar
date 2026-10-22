"use client";

/**
 * BacktestPanel — راستی‌آزمایی (نسخه ۳.۳ · فاز ۱۰.۹)
 * ============================================================
 * 🔴 تغییرات:
 *   • حذف کامل قفل اشتراک (همیشه در دسترس)
 */

import { useState } from "react";
import { CheckCircle2, Settings, ChevronDown } from "lucide-react";
import { AccordionSection } from "@/components/ui/accordion-section";
import { BacktestStats } from "./BacktestStats";
import { SignalHistory } from "./SignalHistory";
import { BacktestFilters } from "./BacktestFilters";

type Tab = "stats" | "history";

export function BacktestPanel() {
  const [tab, setTab] = useState<Tab>("stats");
  const [source, setSource] = useState("");
  const [profile, setProfile] = useState("");
  const [time, setTime] = useState("all");
  const [limit, setLimit] = useState(500);
  const [filtersOpen, setFiltersOpen] = useState(false);

  return (
    <AccordionSection
      title="راستی‌آزمایی"
      icon={<CheckCircle2 className="h-3.5 w-3.5" />}
      preview="آمار و تاریخچه سیگنال‌های ثبت‌شده"
      tone="primary"
      pulse
      defaultOpen={true} // 🔴 همیشه باز
    >
      <div className="space-y-3">
        {/* ═══ ردیف تنظیمات + تب‌ها ═══ */}
        <div className="flex items-center gap-2 mb-3">
          <button
            type="button"
            onClick={() => setFiltersOpen((v) => !v)}
            className={`flex shrink-0 items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors ${
              filtersOpen
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
            }`}
          >
            <Settings className="h-3 w-3" />
            تنظیمات
            <ChevronDown
              className={`h-3 w-3 transition-transform ${
                filtersOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          <div className="flex flex-1 gap-1 rounded-md border border-border/40 bg-muted/20 p-0.5">
            <button
              onClick={() => setTab("stats")}
              className={`flex-1 rounded px-3 py-1 text-[10px] font-medium transition-all ${
                tab === "stats"
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted/40"
              }`}
            >
              📊 آمار
            </button>
            <button
              onClick={() => setTab("history")}
              className={`flex-1 rounded px-3 py-1 text-[10px] font-medium transition-all ${
                tab === "history"
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-muted/40"
              }`}
            >
              📜 تاریخچه
            </button>
          </div>
        </div>

        {/* فیلترها */}
        {filtersOpen && (
          <div className="rounded-md border border-border/40 bg-muted/10 p-3 mb-3">
            <BacktestFilters
              source={source}
              onSourceChange={setSource}
              profile={profile}
              onProfileChange={setProfile}
              time={time}
              onTimeChange={setTime}
              limit={limit}
              onLimitChange={setLimit}
            />
          </div>
        )}

        {/* محتوا */}
        {tab === "stats" && (
          <BacktestStats 
            source={source} 
            profile={profile} 
            time={time} 
            limit={limit} 
          />
        )}
        {tab === "history" && (
          <SignalHistory source={source} profile={profile} />
        )}
      </div>
    </AccordionSection>
  );
}