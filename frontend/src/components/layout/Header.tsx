"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { HelpPanel } from "./HelpPanel";

export function Header() {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString("fa-IR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
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
          <HelpPanel />

          <div className="flex items-center gap-1.5 rounded-lg bg-muted/50 px-2 py-1 text-[10px] md:px-3 md:py-1.5 md:text-sm">
            <Clock className="h-3 w-3 text-muted-foreground md:h-3.5 md:w-3.5" />
            <span className="num font-medium tabular-nums">{time}</span>
          </div>
        </div>
      </div>
    </header>
  );
}