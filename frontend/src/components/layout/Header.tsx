"use client";

import { useEffect, useState } from "react";
import Link from "next/link"; // ⬅️ اضافه شد
import { Clock, User } from "lucide-react";
import { HelpPanel } from "./HelpPanel";

export function Header() {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
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
        
        {/* ─── لوگو (لینک به صفحه اصلی) ─── */}
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img
            src="/icon-192.png"
            alt="Trademun"
            className="h-10 w-10 rounded-xl object-contain"
          />
          <div>
            <h1 className="text-lg font-bold leading-none">تریدمون</h1>
            <p className="text-[10px] text-muted-foreground">Trademun</p>
          </div>
        </Link>

        {/* ─── سمت راست: دکمه‌های دسکتاپ + ساعت ─── */}
        <div className="flex items-center gap-2">
          
          <div className="hidden md:flex items-center overflow-hidden rounded-lg border border-primary/20 bg-primary/5">
            <div className="flex items-center">
              <HelpPanel />
            </div>
            <span className="h-6 w-px bg-primary/20" aria-hidden="true" />
            
            {/* دکمه حساب کاربری (لینک به داشبورد) */}
            <Link
              href="/dashboard"
              className="num inline-flex h-9 items-center gap-1.5 px-3 text-[13px] font-medium text-primary transition-colors hover:bg-primary/10"
              title="حساب کاربری"
            >
              <User className="h-3.5 w-3.5" />
              <span>حساب کاربری</span>
            </Link>
          </div>

          {/* ساعت TEH */}
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