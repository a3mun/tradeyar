"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "@/lib/api";
import { getUser } from "@/lib/auth";

interface StrategyStat {
  real_win_rate: number;
  real_direction_accuracy: number;
  real_loss_rate: number;
  total: number;
  win_rate: number;
  loss_rate: number;
  direction_accuracy: number;
  has_override: { win_rate: boolean; direction_accuracy: boolean };
}

interface SiteStats {
  total_signals: number;
  by_strategy: {
    scalp: StrategyStat;
    swing: StrategyStat;
    position: StrategyStat;
  };
}

function DonutChart({ value, size = 80, strokeWidth = 10, color = "#22c55e", label }: { value: number; size?: number; strokeWidth?: number; color?: string; label?: string; }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, value));
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgba(255,255,255,0.08)" strokeWidth={strokeWidth} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={color} strokeWidth={strokeWidth} fill="none" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" style={{ transition: "stroke-dashoffset 0.6s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-base font-bold" style={{ color }}>{pct.toFixed(0)}٪</span>
        {label && <span className="text-[8px] text-muted-foreground">{label}</span>}
      </div>
    </div>
  );
}

export function StatisticsBox() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<"scalp" | "swing" | "position">("scalp");
  const [stats, setStats] = useState<SiteStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = getUser();
    setIsAdmin(Boolean(user?.is_admin));
  }, []);

  useEffect(() => {
    if (!isAdmin) { setLoading(false); return; }

    let cancelled = false;
    setLoading(true);

    api.get<SiteStats & { ok: boolean }>("/backtest/site-stats")
      .then((res) => {
        if (cancelled) return;
        setStats(res.data);
      })
      .catch(() => {
        if (cancelled) return;
        setStats(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [isAdmin]);

  if (isAdmin === false) {
    return (
      <div className="py-6 text-center">
        <BarChart3 className="mx-auto mb-2 h-8 w-8 text-muted-foreground/40" />
        <p className="text-[11px] text-muted-foreground">این آمار فقط برای مدیران نمایش داده می‌شود.</p>
      </div>
    );
  }

  if (loading) return <div className="flex items-center justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;

  if (!stats || !stats.by_strategy) return <div className="py-6 text-center text-[11px] text-muted-foreground">آماری یافت نشد</div>;

  const currentStat = stats.by_strategy[activeTab];

  // 🔴 منطق اصلاح‌شده:
  let winRate = currentStat.win_rate;
  let lossRate = currentStat.loss_rate;

  // اگه ادمین win_rate رو دستکاری کرده باشه، loss_rate میشه ۱۰۰ - win_rate
  if (currentStat.has_override.win_rate) {
    lossRate = 100 - winRate;
  } 
  // اگه دستکاری نکرده، loss_rate واقعی (از بک‌اند) رو نشون بده. 
  // ولی اگه winRate صفر بود (یعنی هنوز هیچ TP نداریم)، lossRate هم صفر باشه تا ۱۰۰٪ الکی نشون داده نشه.
  else if (winRate === 0) {
    lossRate = 0;
  }

  const directionAcc = currentStat.direction_accuracy;
  // دقت پیش‌بینی: اگه صفر بود، غلط هم صفر (نه ۱۰۰)
  const directionWrong = directionAcc > 0 ? (100 - directionAcc) : 0;

  const tabs = [
    { key: "scalp", label: "⚡ اسکالپ" },
    { key: "swing", label: "📊 سوئینگ" },
    { key: "position", label: "🏛 پوزیشن" },
  ] as const;

  return (
    <div className="space-y-3">
      <p className="text-center text-[10px] text-muted-foreground mb-2">
        📌 مبنای این آمار بر اساس عملکرد ۱۰۰ سیگنال اخیر است.
      </p>

      <div className="flex items-center justify-center gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-3 py-1.5 text-[10px] font-medium transition ${
              activeTab === tab.key
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2 mt-2">
        <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-2 text-center">
          <p className="mb-1 text-[9px] text-muted-foreground">✅ نرخ برد و باخت</p>
          <div className="flex items-center justify-center gap-2">
            <DonutChart value={winRate} color="#22c55e" label="برد" />
            <div className="space-y-1 text-right text-[9px]">
              <div className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-green-500" /><span className="text-muted-foreground">برد:</span><span className="num font-bold text-green-500">{winRate.toFixed(0)}٪</span></div>
              <div className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-red-500" /><span className="text-muted-foreground">باخت:</span><span className="num font-bold text-red-500">{lossRate.toFixed(0)}٪</span></div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2 text-center">
          <p className="mb-1 text-[9px] text-muted-foreground">🎯 دقت پیش‌بینی</p>
          <div className="flex items-center justify-center gap-2">
            <DonutChart value={directionAcc} color="#a78bfa" label="درست" />
            <div className="space-y-1 text-right text-[9px]">
              <div className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-purple-500" /><span className="text-muted-foreground">درست:</span><span className="num font-bold text-purple-500">{directionAcc.toFixed(0)}٪</span></div>
              <div className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-orange-500" /><span className="text-muted-foreground">غلط:</span><span className="num font-bold text-orange-500">{directionWrong.toFixed(0)}٪</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}