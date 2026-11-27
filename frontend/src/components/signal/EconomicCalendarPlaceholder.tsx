
"use client";

import { getToken } from "@/lib/auth";
import { handleAuthFailure } from "@/lib/api";

import { useEffect, useRef, useState } from "react";
import {
  CalendarDays,
  Clock,
  RefreshCw,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

type WeekType = "current" | "next";

type CalendarEvent = {
  date?: string;
  day?: string;
  time?: string;
  currency?: string;
  event: string;
  actual?: string | null;
  forecast?: string | null;
  previous?: string | null;
  impact?: "high";
};

type CalendarResponse = {
  ok: boolean;
  events: CalendarEvent[];
  count: number;
  updated_at: string | null;
  source: string;
  source_url: string;
  week: WeekType;
};

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || "https://api.trademun.ir"
).replace(/\/+$/, "");

const DEFAULT_SOURCE_URL =
  "https://iranbroker.net/economic-calendar/";

function formatUpdatedAt(value: string | null) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Tehran",
  }).format(date);
}

function WeekButton({
  week,
  selected,
  loading,
  onClick,
}: {
  week: WeekType;
  selected: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  const label = week === "current" ? "این هفته" : "هفته آینده";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      aria-pressed={selected}
      className={[
        "inline-flex min-h-9 items-center justify-center gap-2 rounded-lg px-4 py-2",
        "text-xs font-bold transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#d6ad60]/60",
        "disabled:cursor-wait",
        selected
          ? "border border-[#d6ad60]/40 bg-[#d6ad60]/15 text-[#e5c47e]"
          : "border border-transparent bg-white/[0.035] text-muted-foreground hover:bg-white/[0.08] hover:text-foreground",
      ].join(" ")}
    >
      {loading && (
        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
      )}
      {label}
    </button>
  );
}

function LoadingRows() {
  return (
    <div
      className="space-y-2 p-3"
      role="status"
      aria-label="در حال دریافت تقویم اقتصادی"
    >
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="flex animate-pulse items-center gap-3 rounded-lg bg-white/[0.025] p-3"
        >
          <div className="h-4 w-12 rounded bg-white/10" />
          <div className="h-4 w-14 rounded bg-white/10" />
          <div className="h-4 flex-1 rounded bg-white/10" />
          <div className="h-4 w-10 rounded bg-white/10" />
        </div>
      ))}
    </div>
  );
}

export function EconomicCalendarPlaceholder() {
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [selectedWeek, setSelectedWeek] =
    useState<WeekType | null>(null);
  const [loadingWeek, setLoadingWeek] =
    useState<WeekType | null>(null);
  const [error, setError] = useState("");

  const requestIdRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const loadingWeekRef = useRef<WeekType | null>(null);

  useEffect(() => {
    return () => {
      requestIdRef.current += 1;
      loadingWeekRef.current = null;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, []);

  const refreshCalendar = async (
    week: WeekType,
    forceRefresh = false
  ) => {
    // جلوگیری از درخواست تکراری برای همان هفته
    if (loadingWeekRef.current === week) return;

    // لغو درخواست قبلی در صورت تغییر هفته
    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    const requestId = ++requestIdRef.current;

    loadingWeekRef.current = week;
    setLoadingWeek(week);
    setSelectedWeek(week);
    setError("");

    try {
      const params = new URLSearchParams({
        week,
        force_refresh: String(forceRefresh),
      });

      const response = await fetch(
        `${API_BASE}/economic-calendar/weekly?${params.toString()}`,
        {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
          headers: {
            Accept: "application/json",
            ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
          },
        }
      );

      // دریافت پاسخ به شکل متن برای مدیریت پاسخ‌های غیر JSON
      const responseText = await response.text();

      let result: CalendarResponse;

      try {
        result = JSON.parse(responseText);
      } catch {
        throw new Error(
          "پاسخ نامعتبر از سرور دریافت شد."
        );
      }

      if (response.status === 401 || response.status === 403) {
        handleAuthFailure(
          response.status,
          (result as unknown as { detail?: unknown }).detail
        );
      }

      if (!response.ok) {
        throw new Error(
          (result as any)?.detail ||
            "دریافت تقویم اقتصادی ناموفق بود."
        );
      }

      if (
        !result?.ok ||
        !Array.isArray(result.events) ||
        result.week !== week
      ) {
        throw new Error(
          "اطلاعات دریافتی از سرور معتبر نیست."
        );
      }

      // فقط آخرین درخواست اجازه تغییر اطلاعات را دارد
      if (requestId !== requestIdRef.current) return;

      setData(result);
    } catch (err) {
      if (
        err instanceof Error &&
        err.name === "AbortError"
      ) {
        return;
      }

      if (requestId !== requestIdRef.current) return;

      setError(
        err instanceof Error
          ? err.message
          : "ارتباط با سرور برقرار نشد."
      );
    } finally {
      if (requestId === requestIdRef.current) {
        loadingWeekRef.current = null;
        controllerRef.current = null;
        setLoadingWeek(null);
      }
    }
  };

  const isLoading = loadingWeek !== null;

  const isShowingPreviousWeek = Boolean(
    data &&
      selectedWeek &&
      data.week !== selectedWeek &&
      isLoading
  );

  const eventCount = data?.events.length ?? 0;

  return (
    <div
      dir="rtl"
      className="relative overflow-hidden rounded-xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#051118] to-[#07111f] p-3 sm:p-4"
    >
      <div className="pointer-events-none absolute inset-0 opacity-[0.045]">
        <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full bg-[#d6ad60] blur-3xl" />
        <div className="absolute -bottom-10 -left-10 h-36 w-36 rounded-full bg-[#60a5fa] blur-3xl" />
      </div>

      <div className="relative space-y-3">
        {/* انتخاب هفته و بروزرسانی */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1 rounded-xl border border-white/[0.07] bg-black/10 p-1">
            <WeekButton
              week="current"
              selected={selectedWeek === "current"}
              loading={loadingWeek === "current"}
              onClick={() => refreshCalendar("current")}
            />

            <WeekButton
              week="next"
              selected={selectedWeek === "next"}
              loading={loadingWeek === "next"}
              onClick={() => refreshCalendar("next")}
            />
          </div>

          <button
            type="button"
            onClick={() => {
              if (selectedWeek) {
                refreshCalendar(selectedWeek, true);
              }
            }}
            disabled={isLoading || !selectedWeek}
            aria-label="بروزرسانی اجباری تقویم اقتصادی"
            title="دریافت اطلاعات تازه"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.035] text-muted-foreground transition hover:border-[#d6ad60]/30 hover:bg-[#d6ad60]/10 hover:text-[#e5c47e] disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#d6ad60]/60"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                isLoading ? "animate-spin" : ""
              }`}
            />
          </button>
        </div>

        {/* وضعیت دریافت */}
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-2 text-[11px]">
          <div className="flex items-center gap-2 text-muted-foreground">
            <CalendarDays className="h-3.5 w-3.5 text-[#d6ad60]" />

            <span>
              {data
                ? `${eventCount.toLocaleString("fa-IR")} رویداد مهم`
                : "رویدادهای مهم اقتصادی"}
            </span>

            {data && (
              <span className="rounded-md border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-400">
                اهمیت بالا
              </span>
            )}
          </div>

          {data?.updated_at && (
            <span className="flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatUpdatedAt(data.updated_at)}
            </span>
          )}
        </div>

        {/* خطا */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs leading-6 text-red-300"
          >
            <AlertCircle className="mt-1 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* نمایش اطلاعات قبلی هنگام دریافت هفته دیگر */}
        {isShowingPreviousWeek && (
          <div
            role="status"
            className="rounded-lg border border-amber-500/15 bg-amber-500/[0.06] px-3 py-2 text-[11px] leading-5 text-amber-300"
          >
            در حال دریافت{" "}
            {selectedWeek === "next" ? "هفته آینده" : "هفته جاری"}؛
            اطلاعات قبلی موقتاً نمایش داده می‌شود.
          </div>
        )}

        {/* جدول رویدادها */}
        <div
          className={`overflow-hidden rounded-lg border border-white/10 transition-opacity ${
            isShowingPreviousWeek ? "opacity-60" : "opacity-100"
          }`}
          aria-busy={isLoading}
        >
          {!data && isLoading ? (
            <LoadingRows />
          ) : data && data.events.length > 0 ? (
            <>
              <div className="flex items-center justify-between border-b border-white/[0.07] bg-white/[0.025] px-3 py-2">
                <span className="text-[11px] font-bold text-[#e5c47e]">
                  {data.week === "next" ? "هفته آینده" : "هفته جاری"}
                </span>

                <span className="text-[10px] text-muted-foreground">
                  ساعت ایران
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-right text-xs">
                  <thead className="bg-white/[0.035] text-muted-foreground">
                    <tr>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        روز
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        ساعت
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        ارز
                      </th>
                      <th className="min-w-[210px] px-3 py-3 font-medium">
                        رویداد
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        واقعی
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        پیش‌بینی
                      </th>
                      <th className="whitespace-nowrap px-3 py-3 font-medium">
                        قبلی
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-white/[0.06]">
                    {data.events.map((event, index) => (
                      <tr
                        key={`${event.date || event.day || ""}-${event.time || ""}-${event.currency || ""}-${index}`}
                        className="transition-colors hover:bg-white/[0.035]"
                      >
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {event.date || event.day || "—"}
                        </td>

                        <td className="whitespace-nowrap px-3 py-3 font-semibold tabular-nums text-foreground">
                          {event.time || "—"}
                        </td>

                        <td className="px-3 py-3">
                          <span className="inline-flex rounded-md border border-[#d6ad60]/15 bg-[#d6ad60]/10 px-2 py-1 font-bold text-[#d6ad60]">
                            {event.currency || "—"}
                          </span>
                        </td>

                        <td className="px-3 py-3 leading-6 text-foreground">
                          <span className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-red-500" />
                          {event.event}
                        </td>

                        <td className="whitespace-nowrap px-3 py-3 font-medium tabular-nums text-emerald-400">
                          {event.actual || "—"}
                        </td>

                        <td className="whitespace-nowrap px-3 py-3 tabular-nums text-foreground">
                          {event.forecast || "—"}
                        </td>

                        <td className="whitespace-nowrap px-3 py-3 tabular-nums text-muted-foreground">
                          {event.previous || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : data ? (
            <div className="px-4 py-8 text-center">
              <CalendarDays className="mx-auto mb-2 h-7 w-7 text-muted-foreground/50" />
              <p className="text-xs text-muted-foreground">
                رویداد مهمی برای این بازه پیدا نشد.
              </p>
            </div>
          ) : (
            <div className="px-4 py-8 text-center">
              <CalendarDays className="mx-auto mb-2 h-7 w-7 text-[#d6ad60]/60" />
              <p className="text-xs leading-6 text-muted-foreground">
                برای مشاهده رویدادها، یکی از هفته‌ها را انتخاب کن.
              </p>
            </div>
          )}
        </div>

        {/* منبع */}
        <div className="flex items-center justify-between gap-2 border-t border-white/[0.07] pt-3">
          <span className="text-[10px] text-muted-foreground">
            منبع: {data?.source || "ایران بروکر"}
          </span>

          <a
            href={data?.source_url || DEFAULT_SOURCE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] text-muted-foreground transition hover:text-[#d6ad60]"
          >
            مشاهده منبع
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
