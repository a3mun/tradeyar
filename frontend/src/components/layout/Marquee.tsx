"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/display";

interface PriceItem {
  name: string;
  price: number | null;
  unit: string;
}

const MARKETS = [
  { name: "توکیو", icon: "🇯🇵", tz: "Asia/Tokyo", open: 9, close: 15, weekend: ["Sat", "Sun"] },
  { name: "لندن", icon: "🇪🇺", tz: "Europe/London", open: 8, close: 16.5, weekend: ["Sat", "Sun"] },
  { name: "نیویورک", icon: "🇺🇸", tz: "America/New_York", open: 9.5, close: 16, weekend: ["Sat", "Sun"] },
  { name: "بورس", icon: "🇮🇷", tz: "Asia/Tehran", open: 9, close: 12.5, weekend: ["Thu", "Fri"] },
  { name: "صندوق طلا", icon: "🪙", tz: "Asia/Tehran", open: 12, close: 18, weekend: ["Thu", "Fri"] },
];

function useIranTime() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

// 🔴 تبدیل دقیق ساعت محلی بازار به وقت تهران با استفاده از Intl
function convertToTehran(localHour: number, tz: string) {
  const now = new Date();
  
  // استخراج دقیق ساعت و دقیقه فعلی بازار
  const localParts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(now);
  
  const currentLocalH = parseInt(localParts.find(p => p.type === "hour")?.value || "0", 10);
  const currentLocalM = parseInt(localParts.find(p => p.type === "minute")?.value || "0", 10);

  // محاسبه اختلاف بازار با ساعت هدف (open یا close)
  const targetH = Math.floor(localHour);
  const targetM = Math.round((localHour % 1) * 60);
  
  let diffMinutes = (targetH * 60 + targetM) - (currentLocalH * 60 + currentLocalM);
  
  // ساخت یک تاریخ جدید که به اندازه اختلاف دقیقه جابجا شده است
  const targetDate = new Date(now.getTime() + diffMinutes * 60 * 1000);
  
  // حالا زمان این تاریخ جدید را در منطقه زمانی تهران بخوان
  const tehranParts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tehran",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(targetDate);
  
  const tehranH = parseInt(tehranParts.find(p => p.type === "hour")?.value || "0", 10);
  const tehranM = parseInt(tehranParts.find(p => p.type === "minute")?.value || "0", 10);

  return `${String(tehranH).padStart(2, "0")}:${String(tehranM).padStart(2, "0")}`;
}

export function Marquee() {
  const [items, setItems] = useState<PriceItem[]>([]);
  const [priceIdx, setPriceIdx] = useState(0);
  const [priceFading, setPriceFading] = useState(false);
  const now = useIranTime();

  const fetchPrices = () => {
    api
      .get("/symbols/iran-prices")
      .then((res) => {
        const p = res.data.prices || {};
        const list: PriceItem[] = [
          { name: "دلار آزاد", price: p.dollar, unit: "تومان" },
          { name: "طلای ۱۸ عیار", price: p.geram18, unit: "تومان" },
          { name: "سکه امامی", price: p.sekee, unit: "تومان" },
          { name: "مثقال طلا", price: p.mesghal, unit: "تومان" },
          { name: "انس جهانی", price: p.ons, unit: "دلار" },
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

  useEffect(() => {
    if (items.length === 0) return;
    const id = setInterval(() => {
      setPriceFading(true);
      setTimeout(() => {
        setPriceIdx((i) => (i + 1) % items.length);
        setPriceFading(false);
      }, 250);
    }, 2500);
    return () => clearInterval(id);
  }, [items.length]);

  const currentPrice = items[priceIdx];

  // منطق وضعیت بازارها
  const marketStatus = (mk: (typeof MARKETS)[number]) => {
    const localTimeStr = now.toLocaleString("en-US", {
      timeZone: mk.tz,
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
    });
    const [h, m] = localTimeStr.split(":").map(Number);
    const tm = h * 60 + m;

    const localDay = now.toLocaleString("en-US", { timeZone: mk.tz, weekday: "short" });
    
    if (mk.weekend.includes(localDay)) {
      return { label: "تعطیل", color: "text-muted-foreground", time: "" };
    }

    const isOpen = tm >= mk.open * 60 && tm < mk.close * 60;
    const fmtOpen = convertToTehran(mk.open, mk.tz);
    const fmtClose = convertToTehran(mk.close, mk.tz);

    return isOpen
      ? { label: "باز", color: "text-green-500", time: `تا ${fmtClose}` }
      : { label: "بسته", color: "text-red-500", time: `از ${fmtOpen}` };
  };

  const getSessionStatus = () => {
    const utcHour = now.getUTCHours();
    const utcDay = now.getUTCDay();
    if (utcDay === 0 || utcDay === 6) return { label: "📅 آخر هفته", color: "text-orange-400" };
    if (utcHour >= 0 && utcHour < 6) return { label: "🕒 خواب تریدرها 💤", color: "text-red-400" };
    if (utcHour >= 12 && utcHour < 16) return { label: "🕒 لندن-نیویورک 🔥", color: "text-green-400" };
    return { label: "🕒 زمان عادی بازار", color: "text-slate-400" };
  };
  
  const currentSession = getSessionStatus();

  return (
    <div className="w-full overflow-hidden border-b border-border/40 bg-muted/20">
      {/* ═══════════ موبایل ═══════════ */}
      <div className="md:hidden">
        {/* خط ۱: وضعیت بازارها + بج وضعیت کلی */}
        <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b border-border/20 px-2 py-1">
          {MARKETS.map((mk, i) => {
            const st = marketStatus(mk);
            return (
              <span key={i} className="flex items-center gap-0.5 whitespace-nowrap">
                <span className="text-[9px]">{mk.icon}</span>
                <span className={`text-[8px] font-bold ${st.color}`}>
                  {st.label === "تعطیل" ? "● تعطیل" : `● ${st.time}`}
                </span>
              </span>
            );
          })}
          
          {/* بج وضعیت بازار در همان خط */}
          <span className={`flex items-center gap-1 rounded-md border border-border/50 bg-muted/30 px-1.5 py-0.5 text-[8px] font-bold ${currentSession.color}`}>
            {currentSession.label}
          </span>
        </div>
        
        {/* خط ۲: قیمت‌ها (بدون آیکون) */}
        <div className="flex items-center justify-center px-3 py-1">
          {currentPrice ? (
            <div className={`flex items-center gap-1.5 transition-opacity duration-300 ${priceFading ? "opacity-0" : "opacity-100"}`}>
              <span className="text-[10px] font-medium text-muted-foreground">{currentPrice.name}:</span>
              <span className="num text-[11px] font-bold">{currentPrice.price ? formatNumber(currentPrice.price, { maxDecimals: 0 }) : "—"}</span>
              <span className="text-[9px] text-muted-foreground">{currentPrice.unit}</span>
            </div>
          ) : (
            <span className="text-[10px] text-muted-foreground">در حال بارگذاری...</span>
          )}
        </div>
      </div>

      {/* ═══════════ دسکتاپ ═══════════ */}
      <div className="hidden md:block">
        <div className="flex items-center justify-center gap-4 border-b border-border/20 px-4 py-1.5">
          {MARKETS.map((mk, i) => {
            const st = marketStatus(mk);
            return (
              <div key={i} className="flex items-center gap-1.5 whitespace-nowrap">
                <span className="text-xs">{mk.icon}</span>
                <span className="text-[11px] font-medium text-muted-foreground">{mk.name}</span>
                <span className={`text-[11px] font-bold ${st.color}`}>● {st.label}</span>
                <span className="num text-[10px] text-muted-foreground">{st.time}</span>
              </div>
            );
          })}
          <div className="flex items-center border-r border-border/40 pr-4 mr-2">
            <span className={`flex items-center gap-1 rounded-md border border-border/50 bg-muted/20 px-2 py-0.5 text-[10px] font-bold ${currentSession.color}`}>
              {currentSession.label}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-10 px-6 py-2">
          {items.length === 0 ? (
            <span className="text-[11px] text-muted-foreground">در حال بارگذاری...</span>
          ) : (
            items.map((item, i) => (
              <div key={i} className="flex items-center gap-2 whitespace-nowrap">
                <span className="text-[12px] font-medium text-muted-foreground">{item.name}:</span>
                <span className="num text-[12px] font-bold">{item.price ? formatNumber(item.price, { maxDecimals: 0 }) : "—"}</span>
                <span className="text-[10px] text-muted-foreground">{item.unit}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}