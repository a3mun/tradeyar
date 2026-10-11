"use client";

/**
 * Footer — فوتر سایت (فاز ۱۰.۳)
 * ============================================================
 * موبایل: Compact (لوگو + لینک‌ها + سلب مسئولیت + کپی‌رایت)
 * دسکتاپ: سه‌ستونه (برند | اطلاعات | سلب مسئولیت)
 *
 * ═══ تغییرات فاز ۱۰.۳ ═══
 *   • موبایل فشرده شد (لوگو بدون متن تکراری)
 *   • لینک‌ها در یک ردیف افقی
 *   • سلب مسئولیت یک‌خطی
 *   • حذف تکرار «تریدمون / Trademun / دستیار هوشمند»
 *   • پاپ‌آپ دیسکلیمر دست‌نخورده
 */

import { useEffect, useState } from "react";
import { Heart, AlertTriangle, Shield, Globe, Send } from "lucide-react";

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
      <footer className="mt-8 border-t border-border/40 bg-background/60">
        <div className="container mx-auto px-4 py-5 md:py-6">
          {/* ═══════════════════════════════════════════════
              📱 موبایل — Compact
              ═══════════════════════════════════════════════ */}
          <div className="flex flex-col items-center gap-3 text-center md:hidden">
            {/* لوگو */}
            <img
              src="/icon-512.png"
              alt="Trademun"
              className="h-12 w-12 rounded-xl object-contain"
            />

            {/* لینک‌ها — یک ردیف افقی */}
            <div className="flex items-center gap-3 text-[11px]">
              <a
                href="https://trademun.ir"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-muted-foreground transition-colors hover:text-primary"
              >
                <Globe className="h-3 w-3" />
                <span dir="ltr">trademun.ir</span>
              </a>
              <span className="text-muted-foreground/40" aria-hidden="true">
                ·
              </span>
              <a
                href="https://t.me/trademun"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-muted-foreground transition-colors hover:text-primary"
              >
                <Send className="h-3 w-3" />
                <span dir="ltr">t.me/trademun</span>
              </a>
            </div>

            {/* سلب مسئولیت یک خط */}
            <p className="text-[10px] text-yellow-500/80">
              ⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارن
            </p>

            {/* کپی‌رایت + اعتبار */}
            <p className="flex items-center gap-1.5 text-[10px] text-muted-foreground/70">
              <span>© {year}</span>
              <span aria-hidden="true">·</span>
              <span>طراحی با</span>
              <Heart className="h-3 w-3 fill-red-500 text-red-500" />
              <span>آسمون</span>
            </p>
          </div>

          {/* ═══════════════════════════════════════════════
              🖥️ دسکتاپ — سه‌ستونه
              ═══════════════════════════════════════════════ */}
          <div className="hidden md:block">
            {/* ردیف بالا */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 text-right">
              {/* ستون ۱: برند */}
              <div className="flex flex-row items-start gap-3">
                <img
                  src="/icon-512.png"
                  alt="Trademun"
                  className="h-16 w-16 rounded-xl object-contain shrink-0"
                />
                <div className="flex-1 text-right">
                  <h3 className="text-lg font-bold text-foreground leading-none">
                    تریدمون
                  </h3>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Trademun
                  </p>
                  <div className="flex items-center gap-1.5 mt-2 justify-start">
                    <span className="rounded-md bg-muted/50 px-2 py-0.5 text-[9px] text-muted-foreground">
                      v6.0
                    </span>
                    <span className="text-[9px] text-muted-foreground">
                      دستیار هوشمند بازار
                    </span>
                  </div>
                </div>
              </div>

              {/* ستون ۲: اطلاعات */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold mb-3">اطلاعات</h4>
                <a
                  href="https://trademun.ir"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-[11px] text-muted-foreground transition-colors hover:text-primary justify-start"
                >
                  <Globe className="h-3.5 w-3.5" />
                  <span dir="ltr">trademun.ir</span>
                </a>
                <a
                  href="https://t.me/trademun"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-[11px] text-muted-foreground transition-colors hover:text-primary justify-start"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span dir="ltr">t.me/trademun</span>
                </a>
                <p className="text-[10px] text-muted-foreground pt-2">
                  © {year} · همه حقوق محفوظ است
                </p>
              </div>

              {/* ستون ۳: سلب مسئولیت */}
              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-right">
                <div className="flex items-start gap-2">
                  <Shield className="h-4 w-4 shrink-0 mt-0.5 text-yellow-500" />
                  <div className="text-[10px] leading-relaxed text-yellow-500/90 text-right">
                    <strong className="block mb-1 text-yellow-500">
                      ⚠️ سلب مسئولیت
                    </strong>
                    تحلیل‌ها صرفاً جنبه آموزشی دارن. مسئولیت سود یا ضرر بر عهده
                    شماست.
                  </div>
                </div>
              </div>
            </div>

            {/* خط جداکننده */}
            <div className="border-t border-border/30 pt-4">
              <div className="flex flex-row items-center justify-between gap-2 text-[11px] text-muted-foreground">
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
        </div>
      </footer>
    </>
  );
}