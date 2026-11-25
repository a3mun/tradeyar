"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Script from "next/script";
import { AnimatedLogo } from "@/components/ui/animated-logo";
import {
  AlertTriangle,
  Send,
  MessageCircle,
  Info,
  HelpCircle,
  Phone,
  Ticket,
} from "lucide-react";

const VERSION = "1.17.3.0";
const UPDATE_DATE = "۱۴۰۵/۰۹/۰۴";
const DISCLAIMER_KEY = "trademun_hide_disclaimer_forever";

const quickLinks = [
  { href: "/about", label: "درباره ما", icon: Info },
  { href: "/contact", label: "تماس با ما", icon: Phone },
  { href: "/faq", label: "سوالات متداول", icon: HelpCircle },
  { href: "/dashboard/tickets", label: "ثبت تیکت", icon: Ticket },
];

const socialLinks = [
  { href: "https://t.me/trademun", label: "تلگرام", icon: Send },
  { href: "https://ble.ir/trademun", label: "بله", icon: MessageCircle },
];

// ═══════════════════════════════════════════════════════════
// TrustBadges — زیبال + اینماد
// ═══════════════════════════════════════════════════════════

function TrustBadges() {
  return (
    <div className="flex flex-row items-center justify-center gap-3">
      {/* زیبال */}
      <a
        href="https://gateway.zibal.ir/trustMe/trademun.ir"
        target="_blank"
        rel="noopener noreferrer"
        title="پرداخت آنلاین زیبال"
        className="flex h-14 w-24 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] p-2 transition-transform hover:scale-105"
      >
        <img
          src="https://zibal.ir/trust/assets/2.png"
          alt="پرداخت آنلاین زیبال"
          className="max-h-10 max-w-full object-contain"
        />
      </a>

      {/* اینماد */}
      <a
        href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
        target="_blank"
        rel="noopener noreferrer"
        referrerPolicy="origin"
        title="نماد اعتماد الکترونیکی"
        className="flex h-14 w-24 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white p-2 transition-transform hover:scale-105"
      >
        <img
          referrerPolicy="origin"
          src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
          alt="نماد اعتماد الکترونیکی"
          className="max-h-10 max-w-full object-contain"
        />
      </a>
    </div>
  );
}




// ═══════════════════════════════════════════════════════════
// CopyrightInfo
// ═══════════════════════════════════════════════════════════
function CopyrightInfo({ year }: { year: string }) {
  return (
    <div className="flex flex-col items-center gap-1 text-center text-gray-400">
      <span className="text-[10px] sm:text-[11px]">
        طراحی و توسعه: <span className="font-medium text-[#d6ad60]">آسمون</span>
        {" "}| © {year} تریدمون
      </span>

      <span className="text-[8px] text-gray-500" dir="ltr">
        Designed by Asemun · © 2026 Trademun
      </span>

      <div
        className="mt-1 flex flex-wrap items-center justify-center gap-1 border-t border-white/5 px-3 pt-2 text-[9px] text-gray-500 sm:text-[10px]"
        dir="rtl"
      >
        <span>
          نسخه نرم‌افزار{" "}
          <span className="font-semibold text-[#d6ad60]">{VERSION}</span>
        </span>
        <span className="mx-1 text-gray-600">·</span>
        <span>به‌روزرسانی {UPDATE_DATE}</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Footer
// ═══════════════════════════════════════════════════════════
export function Footer() {
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    const hideForever = localStorage.getItem(DISCLAIMER_KEY);
    if (hideForever) return;

    const timer = window.setTimeout(() => setShowDisclaimer(true), 1500);
    return () => window.clearTimeout(timer);
  }, []);

  const acceptDisclaimer = () => {
    if (dontShowAgain) {
      localStorage.setItem(DISCLAIMER_KEY, "1");
    } else {
      localStorage.removeItem(DISCLAIMER_KEY);
    }
    setShowDisclaimer(false);
  };

  const year = new Intl.DateTimeFormat("fa-IR", { year: "numeric" }).format(
    new Date()
  );

  return (
    <>
      {/* ═══════════════ هشدار مهم (مودال) ═══════════════ */}
      {showDisclaimer && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#051118]/85 p-4 backdrop-blur-sm"
          role="presentation"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="footer-disclaimer-title"
            className="w-full max-w-md rounded-2xl border border-[#d6ad60]/30 bg-[#051118] p-5 shadow-2xl sm:p-6"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-full bg-[#d6ad60]/15 p-2">
                <AlertTriangle className="h-5 w-5 text-[#d6ad60]" />
              </div>
              <h3
                id="footer-disclaimer-title"
                className="text-base font-bold text-white"
              >
                توجه مهم
              </h3>
            </div>

            <div className="space-y-3 text-xs leading-7 text-gray-400">
              <p>
                ⚠️ تریدمون صرفاً ابزار تحلیل داده و ارائه سیگنال‌های کمکی است.
                تحلیل‌ها بر پایه الگوریتم‌ها و داده‌های تاریخی انجام می‌شوند و
                تضمینی برای سودآوری ندارند. مسئولیت تصمیم‌گیری و نتایج معاملات
                بر عهده کاربر است.
              </p>

              <div className="space-y-2 rounded-lg bg-white/5 p-3 text-[11px]">
                <p>💡 برای استفاده بهتر، پیشنهاد می‌کنیم:</p>
                <ul className="list-inside list-disc space-y-1 pr-1 text-gray-300">
                  <li>
                    از بخش <span className="text-[#d6ad60]">راهنما</span> دیدن
                    کنید.
                  </li>
                  <li>
                    در صورت وجود سؤال،{" "}
                    <span className="text-[#d6ad60]">سؤالات متداول</span> را
                    بخوانید.
                  </li>
                  <li>
                    در صورت نیاز به پشتیبانی، از بخش{" "}
                    <span className="text-[#d6ad60]">ثبت تیکت</span> استفاده
                    کنید.
                  </li>
                </ul>
              </div>
            </div>

            <label
              htmlFor="dontShowAgain"
              className="mt-4 flex cursor-pointer items-center gap-2 text-[11px] text-gray-400"
            >
              <input
                type="checkbox"
                id="dontShowAgain"
                checked={dontShowAgain}
                onChange={(e) => setDontShowAgain(e.target.checked)}
                className="h-4 w-4 cursor-pointer accent-[#d6ad60]"
              />
              دیگر نمایش داده نشود
            </label>

            <button
              onClick={acceptDisclaimer}
              className="mt-4 w-full rounded-lg bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-4 py-3 text-sm font-bold text-[#101827] transition-opacity hover:opacity-90"
            >
              متوجه شدم
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════ فوتر ═══════════════ */}
      <footer className="mt-8 border-t border-white/5 bg-[#051118]/70 backdrop-blur-md">
        <div className="container mx-auto px-4 py-6 md:py-7">
          {/* ═══════ موبایل ═══════ */}
          <div className="flex flex-col items-center gap-4 text-center md:hidden">
            <Link href="/" className="block">
              <AnimatedLogo
                width={145}
                height={90}
                imgWidth={125}
                imgHeight={78}
              />
            </Link>

            <p className="text-[11px] font-medium leading-relaxed">
              <span className="text-white/90">
                معامله هوشمند، از اینجا شروع می‌شه!
              </span>{" "}
              <span className="text-[#d6ad60]">تریدمون نشه؟</span>
            </p>

            {/* دسترسی سریع */}
            <div className="grid w-full max-w-sm grid-cols-2 gap-2">
              {quickLinks.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex min-h-10 items-center justify-center gap-2 rounded-lg border border-white/5 bg-white/[0.03] px-2 py-2 text-[11px] text-gray-300 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
                >
                  <Icon className="h-3.5 w-3.5 text-[#d6ad60]/80" />
                  {label}
                </Link>
              ))}
            </div>

            {/* شبکه‌های اجتماعی */}
            <div className="flex w-full max-w-sm gap-2">
              {socialLinks.map(({ href, label, icon: Icon }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex min-h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-[11px] text-gray-300 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
                >
                  <Icon className="h-3.5 w-3.5 text-[#d6ad60]/80" />
                  {label}
                </a>
              ))}
            </div>

            {/* 🔴 نمادهای اعتماد */}
            <TrustBadges />
          </div>

          {/* ═══════ دسکتاپ ═══════ */}
          <div className="hidden items-start gap-8 md:grid md:grid-cols-12">
            {/* ستون ۱: لوگو و شعار */}
            <div className="col-span-4 flex flex-col items-start gap-1">
              <Link href="/" className="block">
                <AnimatedLogo
                  width={160}
                  height={105}
                  imgWidth={140}
                  imgHeight={92}
                />
              </Link>
              <p className="text-[11px] font-medium leading-7">
                <span className="text-white/90">
                معامله هوشمند، از اینجا شروع می‌شه!
              </span>{" "}
              <span className="text-[#d6ad60]">تریدمون نشه؟</span>
            
              </p>
            </div>

            {/* ستون ۲: دسترسی سریع */}
            <div className="col-span-3 space-y-3 pt-3">
              <h4 className="mb-4 text-xs font-bold text-[#d6ad60]">
                دسترسی سریع
              </h4>
              {quickLinks.slice(0, 3).map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Icon className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>{label}</span>
                </Link>
              ))}
            </div>

            {/* ستون ۳: کانال‌ها و پشتیبانی */}
            <div className="col-span-3 space-y-3 pt-3">
              <h4 className="mb-4 text-xs font-bold text-[#d6ad60]">
                کانال‌ها و پشتیبانی
              </h4>
              {socialLinks.map(({ href, label, icon: Icon }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Icon className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>کانال {label}</span>
                </a>
              ))}
              <Link
                href="/dashboard/tickets"
                className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
              >
                <Ticket className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                <span>پشتیبانی (تیکت)</span>
              </Link>
            </div>

            {/* ستون ۴: نمادهای اعتماد */}
            <div className="col-span-2 flex items-start justify-center pt-4">
              <TrustBadges />
            </div>
          </div>

          {/* کپی‌رایت */}
          <div className="mt-5 border-t border-white/5 pt-4">
            <CopyrightInfo year={year} />
          </div>
        </div>
      </footer>
    </>
  );
}