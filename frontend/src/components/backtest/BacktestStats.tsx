"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, TrendingUp, Target, RefreshCw, Trash2, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { BacktestResponse } from "@/lib/types";

export function BacktestStats() {
  const [data, setData] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [timeFilter, setTimeFilter] = useState("all");
  const [trapStats, setTrapStats] = useState<{
    total: number;
    accuracy: number;
  } | null>(null);

  // ═══ محاسبه آمار تله‌ها ═══
  useEffect(() => {
    api
      .get("/backtest/history", { params: { limit: 500 } })
      .then((res) => {
        const items = res.data.items || [];
        const traps = items.filter((i: any) => i.had_trap);
        if (traps.length === 0) return;
        const withResult = traps.filter((i: any) => i.result);
        if (withResult.length === 0) return;
        // تله درست بوده اگه سیگنال باخت داده باشه
        const correct = withResult.filter((i: any) => i.result === "loss").length;
        setTrapStats({
          total: traps.length,
          accuracy: (correct / withResult.length) * 100,
        });
      })
      .catch(() => {});
  }, [data]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      // ─── بررسی خودکار ───
      await api.post("/backtest/run").catch(() => {});
      const res = await api.get("/backtest", {
        params: { time_filter: timeFilter },
      });
      setData(res.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeFilter]);

  const handleRun = async () => {
    setRunning(true);
    try {
      await api.post("/backtest/run");
      fetchStats();
    } catch {}
    setRunning(false);
  };

  const handleReset = async () => {
    if (!confirm("همه سیگنال‌ها پاک می‌شن. مطمئنی؟")) return;
    try {
      await api.delete("/backtest/reset");
      fetchStats();
    } catch {}
  };

  const handleDownload = () => {
    api.get("/backtest/history", { params: { limit: 1000 } }).then((res) => {
      const blob = new Blob([JSON.stringify(res.data.items, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `trademun_signals_${Date.now()}.json`;
      a.click();
    });
  };

  const s = data?.stats;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4" />
              راستی‌آزمایی
            </CardTitle>
            <p className="text-[9px] text-muted-foreground mt-0.5">
              بررسی خودکار روی هر بار باز شدن
            </p>
          </div>
          <Select
            value={timeFilter}
            onValueChange={(v) => v && setTimeFilter(v)}
          >
            <SelectTrigger className="h-7 w-24 text-[10px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه</SelectItem>
              <SelectItem value="7d">۷ روز</SelectItem>
              <SelectItem value="30d">۳۰ روز</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <Skeleton className="h-32 w-full" />
        ) : !s || s.total === 0 ? (
          <p className="py-6 text-center text-xs text-muted-foreground">
            هنوز سیگنالی ثبت نشده — بعد از اولین تحلیل، اینجا آمار نمایش داده می‌شه
          </p>
        ) : (
          <>
            {/* ═══ آمار ═══ */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-lg bg-muted/30 p-2">
                <p className="text-[9px] text-muted-foreground">کل</p>
                <p className="num text-base font-bold">{s.total}</p>
              </div>
              <div className="rounded-lg bg-green-500/5 p-2">
                <p className="text-[9px] text-muted-foreground">برد</p>
                <p className="num text-base font-bold text-green-500">{s.wins}</p>
              </div>
              <div className="rounded-lg bg-red-500/5 p-2">
                <p className="text-[9px] text-muted-foreground">باخت</p>
                <p className="num text-base font-bold text-red-500">{s.losses}</p>
              </div>
              <div className="rounded-lg bg-yellow-500/5 p-2">
                <p className="text-[9px] text-muted-foreground">انتظار</p>
                <p className="num text-base font-bold text-yellow-500">{s.pending}</p>
              </div>
            </div>

            {/* ═══ آمار تله‌ها ═══ */}
            {trapStats && trapStats.total > 0 && (
              <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-2.5">
                <p className="text-[10px] font-medium text-orange-400 mb-1.5">
                  ⚠️ دقت هشدار تله‌ها
                </p>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground">
                    {trapStats.total} سیگنال با تله
                  </span>
                  <span className="num text-orange-400 font-bold">
                    {trapStats.accuracy.toFixed(0)}% درست
                  </span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-3 text-center">
                <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground">
                  <TrendingUp className="h-3 w-3" />
                  نرخ برد
                </div>
                <p className="num mt-1 text-lg font-bold text-green-500">
                  {s.win_rate.toFixed(1)}%
                </p>
              </div>
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-center">
                <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground">
                  <Target className="h-3 w-3" />
                  Profit Factor
                </div>
                <p className="num mt-1 text-lg font-bold text-blue-500">
                  {s.profit_factor.toFixed(2)}
                </p>
              </div>
            </div>
          </>
        )}

        {/* ═══ اکشن‌ها ═══ */}
        <div className="grid grid-cols-3 gap-1.5">
          <Button onClick={handleRun} disabled={running} size="sm" variant="default">
            <RefreshCw className={`h-3.5 w-3.5 ${running ? "animate-spin" : ""}`} />
            بررسی
          </Button>
          <Button onClick={handleDownload} size="sm" variant="outline">
            <Download className="h-3.5 w-3.5" />
            JSON
          </Button>
          <Button onClick={handleReset} size="sm" variant="outline">
            <Trash2 className="h-3.5 w-3.5" />
            ریست
          </Button>
        </div>

        {/* ═══ توضیح سیستم ═══ */}
        <div className="rounded-lg bg-muted/20 p-3 space-y-2 text-[10px] text-muted-foreground">
          <p className="font-medium text-foreground">ℹ️ چطور کار می‌کنه؟</p>
          <ul className="space-y-1 pr-3 list-disc opacity-80">
            <li>سیگنال‌های LONG/SHORT خودکار ثبت می‌شن</li>
            <li>سیستم هر ۳۰ دقیقه بررسی می‌کنه که به SL/TP رسیدن</li>
            <li>هر سیگنال یه مهلت داره (بر اساس TF)</li>
            <li>بعد از مهلت → منقضی می‌شه</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
