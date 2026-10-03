"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/display";

interface PriceItem {
  name: string;
  emoji: string;
  price: number | null;
  unit: string;
}

const MARKETS = [
  { name: "توکیو", icon: "🇯🇵", open: 3 * 60 + 30, close: 12 * 60 },
  { name: "لندن", icon: "🇪🇺", open: 11 * 60 + 30, close: 20 * 60 },
  { name: "نیویورک", icon: "🇺🇸", open: 16 * 60 + 30, close: 23 * 60 },
  { name: "تهران", icon: "🇮🇷", open: 9 * 60, close: 12 * 60 + 30, iranOnly: true },
];

function useIranTime() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return new Date(now.getTime() + (3 * 60 + 30) * 60 * 1000);
}

export function Marquee() {
  const [items, setItems] = useState<PriceItem[]>([]);
  const iranNow = useIranTime();

  const fetchPrices = () => {
    api
      .get("/symbols/iran-prices")
      .then((res) => {
        const p = res.data.prices || {};
        const list: PriceItem[] = [
          { name: "دلار", emoji: "💵", price: p.dollar, unit: "تومان" },
          { name: "طلای ۱۸", emoji: "🥇", price: p.geram18, unit: "تومان" },
          { name: "سکه امامی", emoji: "🪙", price: p.sekee, unit: "تومان" },
          { name: "مثقال", emoji: "⚖️", price: p.mesghal, unit: "تومان" },
          { name: "انس جهانی", emoji: "🌍", price: p.ons, unit: "دلار" },
        ];
        setItems(list.filter((x) => x.price));
      })
      .catch(() => setItems([]));
  };

  useEffect(() => {
    fetchPrices();
    const id = setInterval(fetchPrices, 60000);
    return () => clearInterval(id);
  }, []);

  const h = iranNow.getUTCHours();
  const m = iranNow.getUTCMinutes();
  const tm = h * 60 + m;
  const wd = iranNow.getUTCDay();
  const isGlobalWeekend = wd === 6 || wd === 0;
  const isIranWorkday = [6, 0, 1, 2, 3].includes(wd);

  const marketStatus = (mk: (typeof MARKETS)[number]) => {
    if (mk.iranOnly) {
      if (!isIranWorkday)
        return { label: "تعطیل", color: "text-muted-foreground" };
      const isOpen = tm >= mk.open && tm < mk.close;
      return isOpen
        ? { label: "باز", color: "text-green-500" }
        : { label: "بسته", color: "text-red-500" };
    }
    if (isGlobalWeekend)
      return { label: "تعطیل", color: "text-muted-foreground" };
    const isOpen = tm >= mk.open && tm < mk.close;
    return isOpen
      ? { label: "باز", color: "text-green-500" }
      : { label: "بسته", color: "text-red-500" };
  };

  const priceRow = (
    <div className="flex shrink-0 items-center gap-10 px-6">
      {items.length === 0 ? (
        <span className="text-[11px] text-muted-foreground">
          در حال بارگذاری...
        </span>
      ) : (
        items.map((item, i) => (
          <div key={i} className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-sm">{item.emoji}</span>
            <span className="text-[12px] font-medium text-muted-foreground">
              {item.name}:
            </span>
            <span className="num text-[12px] font-bold">
              {item.price ? formatNumber(item.price, 0) : "—"}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {item.unit}
            </span>
          </div>
        ))
      )}
    </div>
  );

  return (
    <div className="w-full overflow-hidden border-b border-border/40 bg-muted/20">
  {/* ═══ ساعت بازارها ═══ */}
      <div className="flex items-center justify-center gap-4 border-b border-border/20 px-4 py-1.5">
        <div className="flex items-center gap-1.5 whitespace-nowrap border-l border-border/30 pl-4">
          <span className="text-xs">🕐</span>
          <span className="text-[11px] font-medium text-muted-foreground">
            تهران
          </span>
          <span className="num text-[11px] font-bold text-foreground">
            {String(h).padStart(2, "0")}:{String(m).padStart(2, "0")}
          </span>
        </div>
        {MARKETS.map((mk, i) => {
          const st = marketStatus(mk);
          const openTime = `${String(Math.floor(mk.open / 60)).padStart(2, "0")}:${String(mk.open % 60).padStart(2, "0")}`;
          const closeTime = `${String(Math.floor(mk.close / 60)).padStart(2, "0")}:${String(mk.close % 60).padStart(2, "0")}`;
          return (
            <div key={i} className="flex items-center gap-1.5 whitespace-nowrap">
              <span className="text-xs">{mk.icon}</span>
              <span className="text-[11px] font-medium text-muted-foreground">
                {mk.name}
              </span>
              <span className={`text-[11px] font-bold ${st.color}`}>
                ● {st.label}
              </span>
              <span className="num text-[10px] text-muted-foreground">
                {st.label === "باز" ? `تا ${closeTime}` : `از ${openTime}`}
              </span>
            </div>
          );
        })}
      </div>

      {/* ═══ قیمت‌ها — تکرار نامحدود با سرعت خیلی کم ═══ */}
      <div className="relative overflow-hidden">
        <div className="marquee-track py-2">
          {priceRow}
          {priceRow}
          {priceRow}
        </div>
      </div>

      <style jsx>{`
        .marquee-track {
          display: flex;
          width: max-content;
          animation: marquee 150s linear infinite;
        }
        @keyframes marquee {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-33.33%);
          }
        }
        .marquee-track:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
}