"use client";

import { Lock } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

interface ProOverlayProps {
  children: React.ReactNode;
  feature?: string;
}

export function ProOverlay({ children, feature = "این بخش" }: ProOverlayProps) {
  const [isPro, setIsPro] = useState(true); // پیش‌فرض true تا اول لود، چیزی مخفی نشه

  useEffect(() => {
    // چک کردن پلن از localStorage
    const userStr = localStorage.getItem("trademun_user");
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.is_admin) {
          setIsPro(true);
          return;
        }
      } catch (e) {}
    }

    const subStr = localStorage.getItem("trademun_subscription");
    if (subStr) {
      try {
        const sub = JSON.parse(subStr);
        if (sub.plan && sub.plan !== "free" && sub.status === "active") {
          setIsPro(true);
        } else {
          setIsPro(false);
        }
      } catch (e) {
        setIsPro(false);
      }
    } else {
      setIsPro(false);
    }
  }, []);

  if (isPro) {
    return <>{children}</>;
  }

  return (
    <div className="relative group">
      {/* ۱. پنل اصلی */}
      <div className="relative z-0">
        {children}
      </div>

      {/* ۲. لایه شفاف برای بلاک کردن کلیک‌ها */}
      <div className="absolute inset-0 z-10 bg-transparent hover:bg-background/5 transition-colors cursor-not-allowed" />

      {/* ۳. پیام برای دسکتاپ (با هاور) */}
      <div className="hidden md:flex absolute inset-0 z-20 items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
        <div className="pointer-events-auto flex flex-col items-center justify-center gap-2 bg-background/95 p-4 rounded-xl border border-[#d6ad60]/40 shadow-2xl backdrop-blur-md">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/30">
            <Lock className="h-5 w-5 text-[#d6ad60]" />
          </div>
          <p className="text-xs font-bold text-foreground text-center">
            {feature} مخصوص کاربران حرفه‌ای است
          </p>
          <p className="text-[10px] text-muted-foreground text-center">
            برای استفاده، اشتراک تهیه کن
          </p>
          <Link
            href="/subscription"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-4 py-2 text-[11px] font-bold text-[#101827] transition-opacity hover:opacity-90 shadow-lg shadow-[#d6ad60]/20"
          >
            🚀 ارتقا به Pro
          </Link>
        </div>
      </div>

      {/* ۴. پیام برای موبایل (همیشه دیده می‌شه - شیشه‌ای پایین) */}
      <div className="md:hidden absolute bottom-2 left-2 right-2 z-20 flex justify-center">
        <Link
          href="/subscription"
          target="_blank"
          rel="noopener noreferrer"
          className="pointer-events-auto flex items-center gap-2 bg-background/90 px-3 py-2 rounded-lg border border-[#d6ad60]/40 shadow-lg backdrop-blur-md"
        >
          <Lock className="h-4 w-4 text-[#d6ad60]" />
          <span className="text-[11px] font-bold text-foreground">
            ارتقا به Pro برای {feature}
          </span>
        </Link>
      </div>
    </div>
  );
}