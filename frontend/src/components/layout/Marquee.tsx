"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/display";

interface PriceItem {
  name: string;
  price: number | null;
  unit: string;
  change?: "up" | "down" | null;
}

const MARKETS = [
  { name: "توکیو", tz: "Asia/Tokyo", open: 0, close: 9, weekend: ["Sat", "Sun"] },
  { name: "لندن", tz: "Europe/London", open: 8, close: 17, weekend: ["Sat", "Sun"] },
  { name: "نیویورک", tz: "America/New_York", open: 13, close: 22, weekend: ["Sat", "Sun"] },
  { name: "بورس", tz: "Asia/Tehran", open: 5.5, close: 9, weekend: ["Thu", "Fri"] },
  { name: "صندوق طلا", tz: "Asia/Tehran", open: 8.5, close: 14.5, weekend: ["Thu", "Fri"] },
];

function useIranTime() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

const TEHRAN_OFFSET_MIN = 3 * 60 + 30;

function convertToTehran(gmtHour: number): string {
  const targetH = Math.floor(gmtHour);
  const targetM = Math.round((gmtHour % 1) * 60);
  let totalMin = targetH * 60 + targetM + TEHRAN_OFFSET_MIN;
  totalMin = ((totalMin % 1440) + 1440) % 1440;
  const tH = Math.floor(totalMin / 60);
  const tM = totalMin % 60;
  return `${String(tH).padStart(2, "0")}:${String(tM).padStart(2, "0")}`;
}

function getMarketSessionStatus(now: Date) {
  const utcH = now.getUTCHours();
  const utcDay = now.getUTCDay();

  if (utcDay === 0 || utcDay === 6) {
    return { label: "📅 آخر هفته", color: "text-gray-500" };
  }
  if (13 <= utcH && utcH < 17) {
    return { label: "🔥 همپوشانی لندن + نیویورک", color: "text-orange-400" };
  }
  if (8 <= utcH && utcH < 9) {
    return { label: "⚡ همپوشانی توکیو + لندن", color: "text-yellow-400" };
  }
  if (0 <= utcH && utcH < 8) {
    return { label: "🌙 فقط بازار آسیا", color: "text-blue-400" };
  }
  return { label: "🕜 زمان عادی بازار", color: "text-gray-400" };
}

// 🔴 کامپوننت هر آیتم قیمت (برای تمیزی کد)
function TickerItem({ item }: { item: PriceItem }) {
  return (
    <div className="flex items-center gap-2.5 px-3 shrink-0" dir="rtl">
      <span className="text-[10px] text-gray-500 font-medium whitespace-nowrap">
        {item.name}
      </span>
      <span
        className={`num text-[12px] font-bold flex items-center gap-1 ${
          item.change === "up"
            ? "text-green-400/90"
            : item.change === "down"
            ? "text-red-400/90"
            : "text-gray-200"
        }`}
      >
        {item.price
          ? formatNumber(item.price, {
              maxDecimals: item.name === "نفت برنت" || item.name === "انس جهانی" ? 2 : 0,
            })
          : "—"}
        {item.change === "up" && <span className="text-[9px]">▲</span>}
        {item.change === "down" && <span className="text-[9px]">▼</span>}
      </span>
      <span className="text-[9px] text-gray-500/80">{item.unit}</span>
      <span className="text-[#d6ad60]/20 px-1 text-[8px]">◆</span>
    </div>
  );
}

function PriceTicker({ items }: { items: PriceItem[] }) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-2 text-[10px] text-gray-500">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div className="relative w-full overflow-hidden py-1" dir="ltr">
      {/* محو شدن دو طرف نوار */}
      <div className="pointer-events-none absolute inset-y-0 right-0 w-20 bg-gradient-to-l from-[#051118] to-transparent z-10" />
      <div className="pointer-events-none absolute inset-y-0 left-0 w-20 bg-gradient-to-r from-[#051118] to-transparent z-10" />

      {/* مسیر حرکت بی‌نهایت */}
      <div className="ticker-track flex w-max flex-nowrap">
        <div className="ticker-group flex shrink-0 flex-nowrap">
          {items.map((item, i) => (
            <TickerItem key={`a-${i}`} item={item} />
          ))}
        </div>
        <div className="ticker-group flex shrink-0 flex-nowrap" aria-hidden="true">
          {items.map((item, i) => (
            <TickerItem key={`b-${i}`} item={item} />
          ))}
        </div>
        <div className="ticker-group flex shrink-0 flex-nowrap" aria-hidden="true">
          {items.map((item, i) => (
            <TickerItem key={`c-${i}`} item={item} />
          ))}
        </div>
      </div>

      <style jsx>{`
        .ticker-track {
          animation: ticker-scroll 50s linear infinite;
          will-change: transform;
        }
        .ticker-track:hover {
          animation-play-state: paused;
        }
        @keyframes ticker-scroll {
          from {
            transform: translateX(0);
          }
          to {
            transform: translateX(-33.33%);
          }
        }
        @media (max-width: 767px) {
          .ticker-track {
            animation-duration: 30s;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .ticker-track {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}

export function Marquee() {
  const [items, setItems] = useState<PriceItem[]>([]);
  const now = useIranTime();

  const prevPricesRef = useRef<Record<string, number>>({});
  const lastDirectionRef = useRef<Record<string, "up" | "down" | null>>({});

  const fetchPrices = () => {
    api
      .get("/symbols/iran-prices")
      .then((res) => {
        const p = res.data.prices || {};

        const rawList = [
          { name: "دلار آزاد", price: p.dollar, unit: "تومان" },
          { name: "طلای ۱۸ عیار", price: p.geram18, unit: "تومان" },
          { name: "سکه امامی", price: p.sekee, unit: "تومان" },
          { name: "انس جهانی", price: p.ons, unit: "دلار" },
          { name: "نفت برنت", price: p.brent, unit: "دلار" },
        ];

        const list: PriceItem[] = rawList
          .filter((x) => x.price)
          .map((item) => {
            const prev = prevPricesRef.current[item.name];
            let change = lastDirectionRef.current[item.name] || null;

            if (prev !== undefined && item.price && item.price !== prev) {
              change = item.price > prev ? "up" : "down";
              lastDirectionRef.current[item.name] = change;
            }

            if (item.price) {
              prevPricesRef.current[item.name] = item.price;
            }

            return { ...item, change };
          });

        setItems(list);
      })
      .catch(() => setItems([]));
  };

  useEffect(() => {
    const timer = setTimeout(fetchPrices, 1000);
    const id = setInterval(fetchPrices, 60000);
    return () => {
      clearTimeout(timer);
      clearInterval(id);
    };
  }, []);

  const marketStatus = (mk: (typeof MARKETS)[number]) => {
    const utcH = now.getUTCHours();
    const utcM = now.getUTCMinutes();
    const utcTm = utcH * 60 + utcM;
    const localDay = now.toLocaleString("en-US", {
      timeZone: mk.tz,
      weekday: "short",
    });
    const fmtClose = convertToTehran(mk.close);
    const fmtOpen = convertToTehran(mk.open);

    if (mk.weekend.includes(localDay)) {
      return { isOpen: false, isHoliday: true, time: "" };
    }

    const isOpen = utcTm >= mk.open * 60 && utcTm < mk.close * 60;
    return {
      isOpen,
      isHoliday: false,
      time: isOpen ? `تا ${fmtClose}` : `از ${fmtOpen}`,
    };
  };

  const sessionStatus = getMarketSessionStatus(now);

  return (
    <div className="w-full overflow-hidden border-b border-white/5 bg-[#051118]/80 backdrop-blur-md shadow-sm">
      {/* ═══════════ خط اول: وضعیت سشن‌ها ═══════════ */}
      <div className="flex items-center justify-center gap-x-5 md:gap-x-7 px-1 py-1 border-b border-white/5 overflow-x-auto whitespace-nowrap scrollbar-hide">
        {MARKETS.map((mk, i) => {
          const st = marketStatus(mk);
          return (
            <div key={i} className="flex items-center gap-1.5 shrink-0 py-0.5">
              <span className="text-[10px] md:text-[11px] font-medium text-gray-400">
                {mk.name}
              </span>
              {st.isHoliday ? (
                <span className="text-[9px] md:text-[10px] font-bold text-orange-400/80">
                  تعطیل
                </span>
              ) : (
                <span className="relative flex h-1.5 w-1.5">
                  {st.isOpen && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  )}
                  <span
                    className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                      st.isOpen ? "bg-green-500" : "bg-slate-600"
                    }`}
                  />
                </span>
              )}
              {st.time && (
                <span
                  className="hidden md:inline num text-[9px] text-gray-500/80"
                  dir="ltr"
                >
                  {st.time}
                </span>
              )}
            </div>
          );
        })}

        <span className="text-white/10 hidden md:inline">|</span>

        <div
          className={`shrink-0 text-[9px] md:text-[10px] font-bold ${sessionStatus.color}`}
        >
          {sessionStatus.label}
        </div>
      </div>

      {/* ═══════════ خط دوم: Ticker قیمت‌ها ═══════════ */}
      <PriceTicker items={items} />
    </div>
  );
}