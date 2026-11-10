"use client";

/**
 * PublicFooter — فوتر عمومی (نسخه ۳)
 * ============================================================
 * 🔴 فاز ۱۴.۹.۹:
 *   • دسکتاپ: یک خط، خواناتر (فونت بزرگ‌تر، رنگ‌های واضح‌تر)
 *   • موبایل: دو خط (شعار+© / لینک‌ها+اینماد)
 *   • شعار طلایی، لینک‌ها سفید، اینماد سبز
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
    <footer className="relative z-10 mt-8 border-t border-[#d6ad60]/15 bg-[#07111f]/70 px-4 py-4 backdrop-blur-sm">
      {/* ═══ دسکتاپ: یک خط ═══ */}
      <div className="hidden items-center justify-center gap-x-3 text-[11.5px] md:flex">
        <span className="font-medium text-[#d6ad60]">
          تریدمون — معامله هوشمند، از اینجا شروع می‌شه.
        </span>
        <span className="text-gray-600">·</span>
        <span className="text-gray-300">© {year} تریدمون</span>
        <span className="text-gray-600">·</span>
        <Link
          href="/about"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <Info className="h-3.5 w-3.5" />
          <span>درباره ما</span>
        </Link>
        <span className="text-gray-600">·</span>
        <Link
          href="/contact"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <Phone className="h-3.5 w-3.5" />
          <span>تماس با ما</span>
        </Link>
        <span className="text-gray-600">·</span>
        <Link
          href="/faq"
          className="flex items-center gap-1 text-gray-300 transition-colors hover:text-[#d6ad60]"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          <span>سوالات متداول</span>
        </Link>
        <span className="text-gray-600">·</span>
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
      <div className="flex flex-col items-center gap-3 text-center md:hidden">
        {/* خط ۱: شعار + © */}
        <div className="flex flex-col items-center gap-1">
          <p className="text-[11px] font-medium text-[#d6ad60]">
            تریدمون — معامله هوشمند، از اینجا شروع می‌شه.
          </p>
          <p className="text-[10px] text-gray-300">© {year} تریدمون</p>
        </div>

        {/* خط ۲: لینک‌ها + اینماد */}
        <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-[11px]">
          <Link
            href="/about"
            className="flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <Info className="h-3.5 w-3.5" />
            <span>درباره ما</span>
          </Link>
          <Link
            href="/contact"
            className="flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <Phone className="h-3.5 w-3.5" />
            <span>تماس</span>
          </Link>
          <Link
            href="/faq"
            className="flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-gray-200 transition-colors hover:border-[#d6ad60]/40 hover:bg-[#d6ad60]/5 hover:text-[#d6ad60]"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>سوالات</span>
          </Link>
          <a
            href="https://trustseal.enamad.ir/?id=8340385&Code=jUOINjWjTAjOBPnz52mIxW9RrL578POs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1.5 text-emerald-400 transition-colors hover:border-emerald-500/40 hover:bg-emerald-500/10"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>اینماد</span>
          </a>
        </div>
      </div>
    </footer>
  );
}