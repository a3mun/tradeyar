"use client";

import { useEffect, useState } from "react";
import { Heart, AlertTriangle, Shield, Globe, Mail } from "lucide-react";

export function Footer() {
  const [showDisclaimer, setShowDisclaimer] = useState(false);

  useEffect(() => {
    const seen = localStorage.getItem("trademun_disclaimer_seen");
    if (!seen) {
      setTimeout(() => setShowDisclaimer(true), 1500);
    }
  }, []);

  const acceptDisclaimer = () => {
    localStorage.setItem("trademun_disclaimer_seen", "1");
    setShowDisclaimer(false);
  };

  const year = new Intl.DateTimeFormat("fa-IR", { year: "numeric" }).format(
    new Date()
  );

  return (
    <>
      {/* ═══ پاپ‌آپ دیسکلیمر ═══ */}
      {showDisclaimer && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm p-4"
          onClick={acceptDisclaimer}
        >
          <div
            className="max-w-md rounded-xl border border-yellow-500/30 bg-card p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="rounded-full bg-yellow-500/15 p-2">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              </div>
              <h3 className="text-base font-bold">توجه مهم</h3>
            </div>

            <div className="space-y-3 text-xs leading-relaxed text-muted-foreground">
              <p>
                📊 تحلیل‌ها و سیگنال‌های این اپ{" "}
                <strong className="text-foreground">صرفاً جنبه آموزشی</strong>{" "}
                دارن.
              </p>
              <p>
                🎯 تصمیم نهایی معامله،{" "}
                <strong className="text-foreground">با خودتونه</strong>.
              </p>
              <p>
                ⚠️{" "}
                <strong className="text-foreground">مسئولیت سود یا ضرر</strong>{" "}
                بر عهده‌ی شماست.
              </p>
              <p className="rounded-lg bg-muted/50 p-3 text-[11px]">
                💡 این ابزار برای کمک به تحلیل شماست، نه جایگزین تصمیم شما.
                همیشه با مدیریت سرمایه و حد ضرر معامله کنید.
              </p>
            </div>

            <button
              onClick={acceptDisclaimer}
              className="mt-4 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              متوجه شدم
            </button>
          </div>
        </div>
      )}

      {/* ═══ فوتر ═══ */}
      <footer className="border-t border-border/40 bg-background/60 mt-8">
        <div className="container mx-auto px-4 py-6">
          {/* ═══ ردیف بالا: لوگو + اطلاعات + لینک ═══ */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* ─── ستون ۱: برند ─── */}
            <div className="flex items-start gap-3">
              <img
                src="/icon-512.png"
                alt="Trademun"
                className="h-16 w-16 rounded-xl object-contain shrink-0"
              />
              <div className="flex-1">
                <h3 className="text-lg font-bold text-foreground leading-none">
                  تریدمون
                </h3>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Trademun
                </p>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="rounded-md bg-muted/50 px-2 py-0.5 text-[9px] text-muted-foreground">
                    v6.0
                  </span>
                  <span className="text-[9px] text-muted-foreground">
                    دستیار هوشمند بازار
                  </span>
                </div>
              </div>
            </div>

            {/* ─── ستون ۲: اطلاعات ─── */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold mb-3">اطلاعات</h4>
              <a
                href="https://trademun.ir"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-[11px] text-muted-foreground transition-colors hover:text-primary"
              >
                <Globe className="h-3.5 w-3.5" />
                <span dir="ltr">trademun.ir</span>
              </a>
              <a
                href="mailto:info@trademun.ir"
                className="flex items-center gap-2 text-[11px] text-muted-foreground transition-colors hover:text-primary"
              >
                <Mail className="h-3.5 w-3.5" />
                <span dir="ltr">info@trademun.ir</span>
              </a>
              <p className="text-[10px] text-muted-foreground pt-2">
                © {year} · همه حقوق محفوظ است
              </p>
            </div>

            {/* ─── ستون ۳: سلب مسئولیت ─── */}
            <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3">
              <div className="flex items-start gap-2">
                <Shield className="h-4 w-4 shrink-0 mt-0.5 text-yellow-500" />
                <div className="text-[10px] leading-relaxed text-yellow-500/90">
                  <strong className="block mb-1 text-yellow-500">
                    ⚠️ سلب مسئولیت
                  </strong>
                  تحلیل‌ها صرفاً جنبه آموزشی دارن. مسئولیت سود یا ضرر بر عهده
                  شماست.
                </div>
              </div>
            </div>
          </div>

          {/* ═══ خط جداکننده ═══ */}
          <div className="border-t border-border/30 pt-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span>طراحی و ساخت با</span>
                <Heart className="h-3.5 w-3.5 fill-red-500 text-red-500 animate-pulse" />
                <span>توسط</span>
                <span className="font-bold text-foreground">آسمون</span>
              </div>
              <p className="text-[10px] opacity-70">
                ⚠️ معامله در بازارهای مالی ریسک بالایی داره
              </p>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}