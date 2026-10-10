"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { HelpPanel } from "./HelpPanel";

export function Header() {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      // 🔴 ساعت تهران با اعداد انگلیسی
      setTime(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Asia/Tehran",
        }).format(now)
      );
    };
  tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* ─── لوگو ─── */}
        <div className="flex items-center gap-3">
          <img
            src="/icon-192.png"
            alt="Trademun"
            className="h-10 w-10 rounded-xl object-contain"
          />
          <div>
            <h1 className="text-lg font-bold leading-none">تریدمون</h1>
            <p className="text-[10px] text-muted-foreground">Trademun</p>
          </div>
        </div>

        {/* ─── راهنما + ساعت ─── */}
        <div className="flex items-center gap-2">
          {/* 🔴 فاز ۱۰.۲ — راهنما فقط روی دسکتاپ */}
          <div className="hidden md:flex">
            <HelpPanel />
          </div>

          <div className="num flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1 text-[11px] font-medium tabular-nums text-primary md:px-3 md:py-1.5 md:text-[13px]">
            <Clock className="h-3 w-3 md:h-3.5 md:w-3.5" />
            <span style={{ fontFamily: "monospace" }}>
              {time || "--:--:--"}
            </span>
            <span className="text-[9px] opacity-70">TEH</span>
          </div>
        </div>
      </div>
    </header>
  );
}