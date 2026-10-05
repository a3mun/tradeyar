"use client";

/**
 * AnalysisUnavailable — حالت جایگزین وقتی تحلیل ممکن نیست
 * ============================================================
 * چه زمانی استفاده می‌شود:
 *   • صرافی «به‌زودی» (تبدیل، رمزینکس، توبیت، بینگ‌ایکس)
 *   • خطای شبکه یا نبود داده برای نماد
 *
 * ⚠️ برای آبان‌تتر استفاده **نمی‌شود** — آنجا زنجیره‌ی fallback
 *    کندل را از صرافی دیگر می‌گیرد و تحلیل انجام می‌شود. شفافیت
 *    از طریق بج `source_used` در SignalCard می‌آید.
 *
 * اصول UX برای کاربر مبتدی:
 *   • هرگز پیام فنی («None returned») نشان نده
 *   • همیشه یک «قدم بعدی» بده
 *   • از لحن سرزنش‌آمیز پرهیز کن
 */

import { BarChart3, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";
import { SOURCE_BY_KEY } from "@/lib/sources";
import type { Source } from "@/lib/types";

interface Props {
  /** پیام اصلی */
  message: string;
  /** پیشنهاد عملی */
  suggestion?: string;
  /** صرافی‌های پیشنهادی */
  alternatives?: Source[];
  /** نوع حالت */
  variant?: "planned" | "no-data";
  /** کارت فشرده */
  compact?: boolean;
}

/** صرافی‌هایی که همیشه کندل دارند */
export const OHLCV_SOURCES: Source[] = ["nobitex", "bitpin", "wallex"];

export function AnalysisUnavailable({
  message,
  suggestion,
  alternatives = OHLCV_SOURCES,
  variant = "no-data",
  compact = false,
}: Props) {
  const { ticker, timeframe, setSource } = useAppStore();

  const Icon = variant === "planned" ? Clock : BarChart3;

  const tone =
    variant === "planned"
      ? "border-yellow-500/30 bg-yellow-500/5 text-yellow-500"
      : "border-border bg-muted/20 text-muted-foreground";

  return (
    <Card className={tone}>
      <CardContent className={compact ? "p-3" : "py-6 text-center"}>
        <div
          className={`flex ${compact ? "items-start gap-2" : "flex-col items-center gap-3"}`}
        >
          <Icon className={compact ? "mt-0.5 h-4 w-4 shrink-0" : "h-8 w-8"} />

          <div className={compact ? "flex-1" : ""}>
            <p className={`font-medium ${compact ? "text-[11px]" : "text-sm"}`}>
              {message}
            </p>
            {suggestion && (
              <p
                className={`mt-1 text-muted-foreground ${
                  compact ? "text-[10px]" : "text-xs"
                }`}
              >
                {suggestion}
              </p>
            )}
          </div>
        </div>

        {/* ═══ دکمه‌های صرافی جایگزین ═══ */}
        {alternatives.length > 0 && (
          <div
            className={`${compact ? "mt-2" : "mt-4"} flex flex-wrap items-center justify-center gap-1.5`}
          >
            <span className="text-[10px] text-muted-foreground">
              تحلیل با:
            </span>
            {alternatives.slice(0, 3).map((alt) => {
              const meta = SOURCE_BY_KEY[alt];
              if (!meta) return null;
              return (
                <Button
                  key={alt}
                  size="sm"
                  variant="outline"
                  className="h-6 gap-1 px-2 text-[10px]"
                  onClick={() => setSource(alt)}
                  title={`تحلیل ${ticker} در ${timeframe} با ${meta.label}`}
                >
                  <span>{meta.icon}</span>
                  {meta.label}
                </Button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
