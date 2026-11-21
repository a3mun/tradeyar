"use client";

/**
 * PublicFooter — فوتر عمومی (نسخه ۳.۱)
 * ============================================================
 * 🔴 تغییرات:
 *   • رفع مشکل دیده نشدن متن در دسکتاپ (تغییر رنگ شعار)
 *   • یکدست‌سازی رنگ‌ها و فاصله‌ها با تم جدید
 */

import Link from "next/link";
import {
  Info,
  Phone,
  HelpCircle,
  CheckCircle2,
} from "lucide-react";

export function PublicFooter() {
  const year = new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
  }).format(new Date());

  return (
    <footer className="relative z-10 mt-8 border-t border-white/5 bg-[#051118]/70 px-4 py-5 backdrop-blur-sm">
      {/* ═══ دسکتاپ: یک خط ═══ */}
      <div className="hidden items-center justify-center gap-x-4 text-[11.5px] md:flex">
        <span className="font-medium text-[#d6ad60]">
          تریدمون — معامله هوشمند، از اینجا شروع می‌شه.
        </span>
        <span className="text-white/10">·</span>
        <Link
          href="/about"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <Info className="h-3.5 w-3.5" />
          <span>درباره ما</span>
        </Link>
        <span className="text-white/10">·</span>
        <Link
          href="/contact"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <Phone className="h-3.5 w-3.5" />
          <span>تماس با ما</span>
        </Link>
        <span className="text-white/10">·</span>
        <Link
          href="/faq"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          <span>سوالات متداول</span>
        </Link>
        <span className="text-white/10">·</span>
        <a
          href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-emerald-400 transition-colors hover:text-emerald-300"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>ثبت شده در سامانه اینماد</span>
        </a>
      </div>

      {/* ═══ موبایل: دو خط ═══ */}
      <div className="flex flex-col items-center gap-4 text-center md:hidden">
        {/* خط ۱: شعار + © */}
        <div className="flex flex-col items-center gap-1.5">
          <p className="text-[11.5px] font-medium text-[#d6ad60]">
            تریدمون — معامله هوشمند، از اینجا شروع می‌شه.
          </p>
        </div>

        {/* خط ۲: لینک‌ها + اینماد */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-[11px]">
          <Link
            href="/about"
            className="flex items-center gap-1 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <Info className="h-3.5 w-3.5" />
            <span>درباره ما</span>
          </Link>
          <Link
            href="/contact"
            className="flex items-center gap-1 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <Phone className="h-3.5 w-3.5" />
            <span>تماس</span>
          </Link>
          <Link
            href="/faq"
            className="flex items-center gap-1 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>سوالات</span>
          </Link>
          <a
            href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-emerald-400 transition-colors hover:border-emerald-500/40 hover:bg-emerald-500/10"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>اینماد</span>
          </a>
        </div>
      </div>
    </footer>
  );
}