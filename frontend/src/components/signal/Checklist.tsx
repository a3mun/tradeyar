"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Info } from "lucide-react";
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

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span>✅ چک‌لیست معاملاتی</span>
          <Badge
            variant="outline"
            className={`num ${COLOR_MAP[data.final_color] || "text-muted-foreground"}`}
          >
            {data.percentage}%
          </Badge>
        </CardTitle>
        <p className="text-[10px] text-muted-foreground">{data.final}</p>
        <p className="text-[9px] text-muted-foreground/70 flex items-center gap-1 mt-1">
          <Info className="h-2.5 w-2.5" />
          امتیاز ۰-۱۰۰: چقدر شرایط برای ورود مساعده
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {data.items.map((item, idx) => {
          const colorClass =
            COLOR_MAP[item.color] || "text-muted-foreground border-border";
          return (
            <div
              key={`${item.group}-${idx}`}
              className={`rounded-lg border p-2.5 ${colorClass}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 space-y-1">
                  <p className="text-xs font-bold">
                    {item.icon} {item.label}
                  </p>
                  <p className="text-[10px] opacity-80">{item.detail}</p>

                  {item.reasons && item.reasons.length > 0 && (
                    <ul className="mt-1 space-y-0.5 pr-3">
                      {item.reasons.map((r, i) => (
                        <li key={i} className="text-[9px] opacity-70 list-disc">
                          {r}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <span className="num text-[10px] font-bold opacity-60">
                  وزن {Math.round(item.weight)}%
                </span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}