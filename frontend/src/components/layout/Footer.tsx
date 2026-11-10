"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatedLogo } from "@/components/ui/animated-logo";
import {
  AlertTriangle,
  Shield,
  Send,
  MessageCircle,
  Info,
  HelpCircle,
  Phone,
  Ticket,
} from "lucide-react";

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

  const year = new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
  }).format(new Date());

  return (
    <>


      {showDisclaimer && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#07111f]/80 backdrop-blur-sm p-4"
          onClick={acceptDisclaimer}
        >
          <div
            className="max-w-md rounded-2xl border border-[#d6ad60]/30 bg-[#0d1b2d] p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center gap-3">
              <div className="rounded-full bg-[#d6ad60]/15 p-2">
                <AlertTriangle className="h-5 w-5 text-[#d6ad60]" />
              </div>
              <h3 className="text-base font-bold text-white">توجه مهم</h3>
            </div>
            <div className="space-y-3 text-xs leading-relaxed text-gray-400">
              <p>
                📊 تحلیل‌ها و سیگنال‌های این اپ{" "}
                <strong className="text-white">صرفاً جنبه آموزشی</strong> دارن.
              </p>
              <p>
                🎯 تصمیم نهایی معامله،{" "}
                <strong className="text-white">با خودتونه</strong>.
              </p>
              <p>
                ⚠️ <strong className="text-white">مسئولیت سود یا ضرر</strong>{" "}
                بر عهده‌ی شماست.
              </p>
              <p className="rounded-lg bg-white/5 p-3 text-[11px]">
                💡 این ابزار برای کمک به تحلیل شماست، نه جایگزین تصمیم شما.
                همیشه با مدیریت سرمایه و حد ضرر معامله کنید.
              </p>
            </div>
            <button
              onClick={acceptDisclaimer}
              className="mt-4 w-full rounded-lg bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-4 py-2.5 text-sm font-bold text-[#101827] transition-opacity hover:opacity-90"
            >
              متوجه شدم
            </button>
          </div>
        </div>
      )}

      <footer className="mt-8 border-t border-[#d6ad60]/10 bg-[#07111f]/60">
        <div className="container mx-auto px-4 py-4 md:py-5">
          {/* ═══════════════════════════════════════════════
              موبایل
          ═══════════════════════════════════════════════ */}
          <div className="flex flex-col items-center gap-4 text-center md:hidden">
            {/* لوگو + شعار */}
            <Link href="/" className="block">
              <AnimatedLogo
                width={120}
                height={80}
                imgWidth={100}
                imgHeight={66}
              />
            </Link>

            <p className="text-[12px] font-medium leading-relaxed">
              <span className="text-white/90">
                معامله هوشمند، از اینجا شروع می‌شه!
              </span>{" "}
              <span className="text-[#d6ad60]">تریدمون نشه؟</span>
            </p>

            {/* لینک‌ها — به صورت دکمه‌های جدا */}
            <div className="flex flex-wrap items-center justify-center gap-2 text-[11px]">
              <Link
                href="/about"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <Info className="h-3.5 w-3.5" />
                درباره ما
              </Link>
              <Link
                href="/contact"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <Phone className="h-3.5 w-3.5" />
                تماس با ما
              </Link>
              <Link
                href="/faq"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <HelpCircle className="h-3.5 w-3.5" />
                سوالات متداول
              </Link>
            </div>

            {/* شبکه‌ها — دکمه‌های جدا */}
            <div className="flex flex-wrap items-center justify-center gap-2 text-[11px]">
              <a
                href="https://t.me/trademun"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <Send className="h-3.5 w-3.5" />
                <span>تلگرام</span>
              </a>
              <a
                href="https://ble.ir/trademun"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <MessageCircle className="h-3.5 w-3.5" />
                <span>بله</span>
              </a>
              <Link
                href="/dashboard/tickets"
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
              >
                <Ticket className="h-3.5 w-3.5" />
                <span>ثبت تیکت</span>
              </Link>
            </div>

            {/* سلب مسئولیت */}
            <div className="flex items-start justify-center gap-1.5 px-2">
              <Shield className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#d6ad60]/70" />
              <p className="text-[10px] leading-relaxed text-[#d6ad60]/80">
                تریدمون یک موتور تحلیل‌گر ریاضی است. مسئولیت معامله با شماست.
              </p>
            </div>

            {/* © + اینماد (لوگو کوچیک) */}
            <div className="flex flex-col items-center gap-2">
              <div className="flex flex-col items-center gap-0.5 text-[10px] text-gray-400">
                <span>
                  طراحی و توسعه:{" "}
                  <span className="font-medium text-[#d6ad60]">آسمون</span> | ©{" "}
                  {year} تریدمون
                </span>
                <span className="text-[8.5px] text-gray-600" dir="ltr">
                  Designed by Asemun · © {year} Trademun
                </span>
              </div>

              <a
                referrerPolicy="origin"
                target="_blank"
                href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
                rel="noopener noreferrer"
                className="block rounded-md border border-white/10 bg-white p-1 transition-transform hover:scale-105"
                title="نماد اعتماد الکترونیکی"
              >
                <img
                  referrerPolicy="origin"
                  src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
                  alt="اینماد"
                  className="h-10 w-auto object-contain"
                />
              </a>
            </div>
          </div>

          {/* ═══════════════════════════════════════════════
              دسکتاپ — ۴ ستون
          ═══════════════════════════════════════════════ */}
          <div className="hidden md:block">
            {/* ═══ ردیف ۱: ۴ ستون ═══ */}
            <div className="grid grid-cols-12 gap-6 mb-4">
              {/* ستون ۱: لوگو + شعار (۳۵٪) */}
              <div className="col-span-4 flex flex-col items-start gap-2">
                <Link href="/" className="block">
                  <AnimatedLogo
                    width={110}
                    height={74}
                    imgWidth={92}
                    imgHeight={62}
                  />
                </Link>
                <p className="text-[11px] font-medium leading-relaxed">
                  <span className="text-white/90">
                    معامله هوشمند، از اینجا شروع می‌شه!
                  </span>
                  <br />
                  <span className="text-[#d6ad60]">تریدمون نشه؟</span>
                </p>
              </div>

              {/* ستون ۲: دسترسی سریع (۲۲٪) */}
              <div className="col-span-3 space-y-1">
                <h4 className="mb-1.5 text-xs font-bold text-[#d6ad60]">
                  دسترسی سریع
                </h4>
                <Link
                  href="/about"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Info className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>درباره ما</span>
                </Link>
                <Link
                  href="/contact"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Phone className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>تماس با ما</span>
                </Link>
                <Link
                  href="/faq"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <HelpCircle className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>سوالات متداول</span>
                </Link>
              </div>

              {/* ستون ۳: کانال‌های سیگنال (۲۲٪) */}
              <div className="col-span-3 space-y-1">
                <h4 className="mb-1.5 text-xs font-bold text-[#d6ad60]">
                  کانال‌های سیگنال
                </h4>
                <a
                  href="https://t.me/trademun"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Send className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>کانال تلگرام</span>
                </a>
                <a
                  href="https://ble.ir/trademun"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <MessageCircle className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>کانال بله</span>
                </a>
                <Link
                  href="/dashboard/tickets"
                  className="flex items-center gap-2 text-[11px] text-gray-300 transition-colors hover:text-[#d6ad60]"
                >
                  <Ticket className="h-3.5 w-3.5 text-[#d6ad60]/70" />
                  <span>پشتیبانی (تیکت)</span>
                </Link>
              </div>

              {/* ستون ۴: نمادها (۲۱٪) — کنار هم */}
              <div className="col-span-2 flex items-center justify-end gap-2">
                {/* زیبال (placeholder) */}
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-white/5"
                  title="درگاه پرداخت زیبال"
                >
                  <span className="text-[8px] font-bold text-gray-400">
                    زیبال
                  </span>
                </div>

                {/* اینماد */}
                <a
                  referrerPolicy="origin"
                  target="_blank"
                  href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
                  rel="noopener noreferrer"
                  className="block rounded-lg border border-white/10 bg-white p-1 transition-transform hover:scale-105"
                  title="نماد اعتماد الکترونیکی"
                >
                  <img
                    referrerPolicy="origin"
                    src="https://trustseal.enamad.ir/logo.aspx?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
                    alt="اینماد"
                    className="h-10 w-auto object-contain"
                  />
                </a>
              </div>
            </div>

            {/* ═══ ردیف ۲: سلب مسئولیت + © ═══ */}
            <div className="border-t border-[#d6ad60]/10 pt-2.5">
              <div className="flex flex-row items-center justify-between gap-3">
                {/* چپ: سلب مسئولیت */}
                <div className="flex max-w-md items-start gap-1.5">
                  <Shield className="mt-0.5 h-3 w-3 shrink-0 text-[#d6ad60]/70" />
                  <p className="text-right text-[9px] leading-relaxed text-[#d6ad60]/70">
                    تریدمون یک موتور تحلیل‌گر ریاضی است. تصمیم معامله و
                    مسئولیت سود یا زیان، با شماست.
                  </p>
                </div>

                {/* راست: © + آسمون (دو خط) */}
                <div className="flex shrink-0 flex-col items-end gap-0.5 text-gray-400">
                  <span className="text-[10px]">
                    طراحی و توسعه:{" "}
                    <span className="font-medium text-[#d6ad60]">آسمون</span>{" "}
                    <span className="mx-1 text-gray-600">|</span> © {year}{" "}
                    تریدمون
                  </span>
                  <span
                    className="text-[8px] text-gray-600"
                    dir="ltr"
                  >
                    Designed by Asemun · © {year} Trademun
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}