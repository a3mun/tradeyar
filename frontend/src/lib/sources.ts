/**
 * lib/sources.ts
 * متادیتای صرافی‌ها — تنها منبع حقیقت فرانت
 * ============================================================
 * ⚠️ منبع حقیقت نهایی **بک‌اند** است
 *    (`GET /symbols/sources`). این فایل فقط برای رندر سریع
 *    بدون درخواست شبکه است و باید با `core/sources.py` هم‌خوان بماند.
 */

import type { ActiveSource, PlannedSource, Source } from "@/lib/types";

export interface SourceMeta {
  value: Source;
  /** نام کوتاه فارسی */
  label: string;
  icon: string;
  /** مسیر لوگو در public/logos */
  logo: string;
  /** رنگ بج (Tailwind) */
  badgeClass: string;
  /** ✅ فعال است (fetcher دارد) */
  active: boolean;
  /** 🔜 هنوز پیاده‌سازی نشده */
  planned: boolean;
  /** آیا OHLCV (کندل) دارد؟ — آبان‌تتر ندارد */
  hasOhlcv: boolean;
  /** آیا بازار تتری (USDT) دارد؟ — آبان‌تتر ندارد */
  hasUsdt: boolean;
  /** آیا بازار تومانی دارد؟ */
  hasIrt: boolean;
  /** تایم‌فریم‌های قطعاً پشتیبانی‌نشده (بقیه fallback می‌شوند) */
  unsupportedTfs?: string[];
  /** نکته‌ی نمایشی */
  note?: string;
  /** 🔴 آیا این منبع فقط برای فارکس/کالا است؟ */
  isForex?: boolean;
}

/** صرافی‌ها و منابع فعال — به ترتیب اولویت نمایش */
export const SOURCE_META: SourceMeta[] = [
  {
    value: "nobitex",
    label: "نوبیتکس",
    icon: "🟣",
    logo: "/logos/nobitex.png",
    badgeClass: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    active: true,
    planned: false,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: true,
  },
  {
    value: "bitpin",
    label: "بیت‌پین",
    icon: "🟢",
    logo: "/logos/bitpin.png",
    badgeClass: "bg-green-500/15 text-green-400 border-green-500/30",
    active: true,
    planned: false,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: true,
  },
  {
    value: "wallex",
    label: "والکس",
    icon: "🔵",
    logo: "/logos/wallex.png",
    badgeClass: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    active: true,
    planned: false,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: true,
    unsupportedTfs: ["۳۰ دقیقه"],
  },
  {
    value: "tabdeal",
    label: "تبدیل",
    icon: "🟠",
    logo: "/logos/tabdeal.png",
    badgeClass: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    active: true,
    planned: false,
    hasOhlcv: false,
    hasUsdt: true,
    hasIrt: true,
    note: "فقط قیمت و عمق بازار — تحلیل ندارد",
  },
  {
    value: "tsetmc",
    label: "بورس",
    icon: "🇮🇷",
    logo: "/logos/tsetmc.png",
    badgeClass: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    active: true,
    planned: false,
    hasOhlcv: true,
    hasUsdt: false,
    hasIrt: false,
    unsupportedTfs: ["۳۰ دقیقه"],
    note: "فقط روزانه",
  },
  // 🔴 فاز ۱۶.۴ — فارکس و کالا (طلا/نقره)

  {
    value: "forex",
    label: "فارکس",
    icon: "🌍",
    logo: "/logos/biquote.png",
    badgeClass: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
    active: true,
    planned: false,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: false,
    note: "فارکس، کالا، شاخص‌ها — Biquote",
    isForex: true,
  },
];

/** منابع حذف‌شده */
export interface RemovedSourceMeta {
  value: string;
  label: string;
  icon: string;
  logo: string;
  badgeClass: string;
  reason: string;
}

export const REMOVED_SOURCE_META: RemovedSourceMeta[] = [
  {
    value: "abantether",
    label: "آبان‌تتر",
    icon: "🔷",
    logo: "/logos/abantether.png",
    badgeClass: "bg-red-500/15 text-red-400 border-red-500/30",
    reason: "کندل و عمق بازار نداشت — با بقیه ناهماهنگ بود",
  },
];

/** 🔜 صرافی‌های برنامه‌ریزی‌شده برای فاز ۷ */
export const PLANNED_SOURCE_META: SourceMeta[] = [
  {
    value: "ramzinex",
    label: "رمزینکس",
    icon: "🟡",
    logo: "/logos/ramzinex.png",
    badgeClass: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    active: false,
    planned: true,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: true,
  },
  {
    value: "toobit",
    label: "توبیت",
    icon: "🟤",
    logo: "/logos/toobit.png",
    badgeClass: "bg-amber-700/15 text-amber-600 border-amber-700/30",
    active: false,
    planned: true,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: false,
  },
  {
    value: "bingx",
    label: "بینگ‌ایکس",
    icon: "🔶",
    logo: "/logos/bingx.png",
    badgeClass: "bg-orange-600/15 text-orange-500 border-orange-600/30",
    active: false,
    planned: true,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: false,
  },
  {
    value: "bit24",
    label: "بیت۲۴",
    icon: "🔹",
    logo: "/logos/bit24.png",
    badgeClass: "bg-blue-600/15 text-blue-500 border-blue-600/30",
    active: false,
    planned: true,
    hasOhlcv: true,
    hasUsdt: true,
    hasIrt: true,
  },
];

/** همه‌ی صرافی‌ها (فعال + برنامه‌ریزی‌شده) — بدون حذف‌شده‌ها */
export const ALL_SOURCE_META: SourceMeta[] = [
  ...SOURCE_META,
  ...PLANNED_SOURCE_META,
];

/** جستجوی سریع بر اساس کلید */
export const SOURCE_BY_KEY: Record<string, SourceMeta> = Object.fromEntries(
  ALL_SOURCE_META.map((s) => [s.value, s])
);

/**
 * صرافی‌هایی که در **جدول مقایسه قیمت** پرسیده می‌شوند.
 * 🔴 tsetmc و  از این لیست خارج می‌شوند (فقط برای کریپتو).
 */
export const QUOTE_SOURCE_META: SourceMeta[] = SOURCE_META.filter(
  (s) => s.value !== "tsetmc"
);

/** چک: آیا این صرافی تحلیل (OHLCV) خودش را دارد؟ */
export function sourceHasAnalysis(source: string): boolean {
  return SOURCE_BY_KEY[source]?.hasOhlcv ?? true;
}

/** 🔴 فاز ۱۴.۹.۵ — آیا این صرافی تحلیل OHLCV دارد؟ */
export function sourceSupportsAnalysis(source: string): boolean {
  return SOURCE_BY_KEY[source]?.hasOhlcv ?? false;
}

/** چک: آیا این صرافی فعال است؟ */
export function isActiveSource(source: string): boolean {
  return SOURCE_BY_KEY[source]?.active ?? false;
}

/**
 * آیا این صرافی برای این جفت‌ارز بازار دارد؟
 */
export function sourceSupportsPair(source: string, ticker: string): boolean {
  const meta = SOURCE_BY_KEY[source];
  if (!meta || meta.planned) return false;
  if (!ticker) return false;

  const upper = ticker.toUpperCase();

  // 🔴 فاز ۱۶.۵ — فارکس (Biquote): کالا، شاخص، جفت‌ارز
  if (source === "forex") {
    return (
      upper === "XAU-USD" ||
      upper === "XAG-USD" ||
      upper === "USOIL-USD" ||
      upper === "UKOIL-USD" ||
      upper === "DXY-USD" ||
      upper === "US500-USD" ||
      upper === "US30-USD" ||
      upper === "USTEC-USD" ||
      upper === "EUR-USD" ||
      upper === "DE30-USD" ||
      // 🟢 BTC-USD: برای مقایسه قیمت جهانی
      (upper === "BTC-USD" && meta.hasUsdt)
    );
  }
  
  const isUsdt = upper.endsWith("-USD") || upper.endsWith("-USDT");
  const isIrt = upper.endsWith("-IRT") || upper.endsWith("-RLS");
  const isIranianStock = !/^[A-Za-z0-9]/.test(ticker);

  // ─── ناهماهنگی دوطرفه ───
  if (source === "tsetmc") {
    return isIranianStock;
  }
  if (isIranianStock) {
    return false;
  }

  // 🔴 اگه نماد فارکس (XAU-USD/XAG-USD) بود ولی صرافی xaus نبود → false
  if (upper === "XAU-USD" || upper === "XAG-USD") {
    return false;
  }

  if (isUsdt) return meta.hasUsdt;
  if (isIrt) return meta.hasIrt;
  return true;
}

/** آیا جفت (source, ticker) **هماهنگ** است؟ */
export function isPairCoherent(source: string, ticker: string): boolean {
  return sourceSupportsPair(source, ticker);
}

/** نام نمایشی صرافی */
export function sourceLabel(source: string): string {
  return SOURCE_BY_KEY[source]?.label ?? source;
}

/** آیکن صرافی */
export function sourceIcon(source: string): string {
  return SOURCE_BY_KEY[source]?.icon ?? "•";
}

/** کلاس بج صرافی */
export function sourceBadgeClass(source: string): string {
  return (
    SOURCE_BY_KEY[source]?.badgeClass ??
    "bg-muted/30 text-muted-foreground border-border"
  );
}

export type { ActiveSource, PlannedSource, Source };