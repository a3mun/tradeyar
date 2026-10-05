"use client";

/**
 * Checklist — چک‌لیست معاملاتی (نسخه ۱.۹)
 * ============================================================
 * 🔴 کشویی شد چون در موبایل ۱۰ آیتم بلند، صفحه را می‌بلعید و
 *    کاربر مبتدی نمی‌دانست کجا مهم است.
 *
 * ⚠️ بستن کشو، **محاسبه‌ی چک‌لیست را متوقف نمی‌کند** — چک‌لیست
 *    از داده‌ی تحلیل (`useSignalData`) می‌آید که مستقل poll
 *    می‌شود. کشو فقط نمایش را کنترل می‌کند.
 *
 * پیش‌نمایش در حالت بسته: امتیاز کل + آیتم‌های قرمز (هشدارها)
 * چون آن‌ها چیزی هستند که کاربر باید **حتماً** ببیند.
 */

import { Info, AlertTriangle } from "lucide-react";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import type { ChecklistData } from "@/lib/types";

interface Props {
  data: ChecklistData;
}

const COLOR_MAP: Record<string, string> = {
  green: "text-green-500 border-green-500/30 bg-green-500/5",
  red: "text-red-500 border-red-500/30 bg-red-500/5",
  yellow: "text-yellow-500 border-yellow-500/30 bg-yellow-500/5",
};

export function Checklist({ data }: Props) {
  if (!data || !data.items || data.items.length === 0) return null;

  // ─── آیتم‌های هشدار (قرمز) — در پیش‌نمایش بسته ───
  const warnings = data.items.filter((i) => i.color === "red");
  const greens = data.items.filter((i) => i.color === "green").length;

  const scoreColor =
    COLOR_MAP[data.final_color] || "text-muted-foreground border-border";

  return (
    <CollapsibleCard
      title={
        <span className="flex items-center gap-1.5">
          ✅ چک‌لیست معاملاتی
        </span>
      }
      badge={
        <span
          className={`num rounded-full border px-2 py-0.5 text-[9px] font-bold ${scoreColor}`}
        >
          {data.percentage}%
        </span>
      }
      subtitle={`${data.final} · ${greens} تأیید${
        warnings.length ? ` · ${warnings.length} هشدار` : ""
      }`}
    >
      {/* ─── خلاصه ─── */}
      <div className="mb-2 space-y-1">
        <p className="text-[10px] font-medium">{data.final}</p>
        <p className="flex items-center gap-1 text-[9px] text-muted-foreground/70">
          <Info className="h-2.5 w-2.5" />
          امتیاز ۰-۱۰۰: چقدر شرایط برای ورود مساعده
        </p>

        {/* ─── هشدارها برجسته ─── */}
        {warnings.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {warnings.slice(0, 3).map((w, i) => (
              <span
                key={i}
                className="flex items-center gap-0.5 rounded-full bg-red-500/15 px-1.5 py-0.5 text-[8px] text-red-400"
              >
                <AlertTriangle className="h-2 w-2" />
                {w.label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ─── آیتم‌ها ─── */}
      <div className="space-y-1.5">
        {data.items.map((item, idx) => {
          const colorClass =
            COLOR_MAP[item.color] || "text-muted-foreground border-border";
          return (
            <div
              key={`${item.group}-${idx}`}
              className={`rounded-lg border p-2 ${colorClass}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 space-y-0.5">
                  <p className="text-[11px] font-bold">
                    {item.icon} {item.label}
                  </p>
                  <p className="text-[9px] opacity-80">{item.detail}</p>

                  {item.reasons && item.reasons.length > 0 && (
                    <ul className="mt-1 space-y-0.5 pr-3">
                      {item.reasons.map((r, i) => (
                        <li key={i} className="list-disc text-[8px] opacity-70">
                          {r}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <span className="num shrink-0 text-[9px] font-bold opacity-60">
                  {Math.round(item.weight)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </CollapsibleCard>
  );
}