"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ArrowRight, Globe, Download, FileArchive, FolderOpen, MonitorPlay, ShieldCheck,
  AlertTriangle, Clock, Info, ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getToken } from "@/lib/auth";

// ═══ بخش‌های راهنما (برای Accordion) ═══
const GUIDE_SECTIONS = [
  {
    id: "setup",
    title: "📥 راهنمای نصب افزونه",
    icon: <MonitorPlay className="h-4 w-4" />,
    content: (
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <Download className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۱. دانلود فایل افزونه</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">از داشبورد تریدمون، دکمه «دانلود افزونه» را بزنید تا فایل zip دریافت شود.</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <FolderOpen className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۲. استخراج فایل</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">فایل zip را از حالت فشرده خارج کنید.</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <Globe className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۳. باز کردن تنظیمات کروم</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">در مرورگر کروم به آدرس <code className="text-[#d6ad60] bg-[#d6ad60]/10 px-1 rounded">chrome://extensions</code> بروید.</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <FileArchive className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۴. فعال‌سازی حالت توسعه‌دهنده</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">گزینه Developer mode را در گوشه بالا فعال کنید.</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <FolderOpen className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۵. بارگذاری افزونه</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">روی Load unpacked کلیک کرده و پوشه استخراج شده را انتخاب کنید.</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <MonitorPlay className="h-5 w-5 text-[#d6ad60] mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold text-white">۶. اتصال به حساب کاربری</p>
            <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">روی آیکون افزونه کلیک کنید. دکمه «اتصال به حساب تریدمون» را بزنید و فرآیند را کامل کنید.</p>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "disclaimer",
    title: "⚠️ سلب مسئولیت و قوانین",
    icon: <AlertTriangle className="h-4 w-4" />,
    content: (
      <p className="text-[11px] text-gray-300 leading-relaxed text-justify">
        سایت <b>تریدمون</b> صرفاً یک <b>تحلیل‌گر داده</b> و ارائه‌دهنده سیگنال‌های کمکی است. تمامی تحلیل‌ها بر اساس الگوریتم‌های ریاضی و داده‌های تاریخی انجام می‌شود و <b>هیچ‌گونه تضمینی برای سودآوری وجود ندارد</b>. تصمیم‌گیری نهایی برای ورود یا خروج از معامله، کاملاً بر عهده کاربر است و تریدمون هیچ مسئولیتی در قبال سود یا زیان احتمالی کاربران نمی‌پذیرد.
      </p>
    ),
  },
  {
    id: "why-wait",
    title: "⏳ چرا باید صبر کنید؟",
    icon: <Clock className="h-4 w-4" />,
    content: (
      <div className="space-y-2 text-[11px] text-gray-300 leading-relaxed text-justify">
        <p>به دلیل عدم فعالیت رباتی و <b>محافظت از حساب شما در صرافی</b>، اکستنشن برای راه‌اندازی اولیه و اطمینان از صحت سیگنال‌ها، نیاز به جمع‌آوری حداقل <b>۱۵ کندل (۱۵ دقیقه)</b> دارد.</p>
        <p className="text-[#d6ad60] font-bold bg-[#d6ad60]/10 p-2 rounded border border-[#d6ad60]/20">
          🔹 توصیه اکید: لطفاً پس از باز کردن صفحه صرافی، حداقل <b>یک ساعت</b> به اکستنشن زمان دهید تا دیتای کافی جمع‌آوری شده و تحلیل‌های لایه‌های بالاتر (مانند ۵۰ و ۲۰۰ کندل) فعال شوند.
        </p>
      </div>
    ),
  },
  {
    id: "how-it-works",
    title: "🔌 افزونه چطور کار می‌کند؟",
    icon: <Info className="h-4 w-4" />,
    content: (
      <ul className="space-y-2 text-[11px] text-gray-300 leading-relaxed text-justify pr-4 list-disc">
        <li>افزونه به صورت خودکار به WebSocket داخلی صرافی متصل می‌شود و قیمت‌های لحظه‌ای را بدون دستکاری در حساب شما دریافت می‌کند.</li>
        <li>داده‌ها در مرورگر شما (لوکال) به کندل تبدیل می‌شوند و تحلیل روی همین کندل‌ها انجام می‌شود.</li>
        <li>هیچ‌گونه سفارش خرید یا فروشی به صورت خودکار ثبت نمی‌شود.</li>
      </ul>
    ),
  },
  {
    id: "optional",
    title: "📊 امکانات آپشنال (درصد سود/زیان)",
    icon: <ShieldCheck className="h-4 w-4" />,
    content: (
      <p className="text-[11px] text-gray-300 leading-relaxed text-justify">
        افزونه به صورت اختیاری می‌تواند درصد سود/زیان و قیمت لحظه‌ای هر معامله را در جدول صرافی نمایش دهد. برای کپی قیمت، روی آن کلیک کنید. اگر نمی‌خواهید این اطلاعات نمایش داده شوند، از <b>پاپ‌آپ افزونه</b> (کلید «نمایش امکانات آپشنال») آن را غیرفعال کنید.
      </p>
    ),
  },
];

export default function ExtensionGuidePage() {
  const [openSections, setOpenSections] = useState<string[]>(["setup"]);

  const toggleSection = (id: string) => {
    setOpenSections(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  return (
    <div className="min-h-screen bg-[#07111f] text-white py-12 px-4">
      <div className="max-w-3xl mx-auto">
        
        {/* هدر */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-[#d6ad60]/10 text-[#d6ad60] px-4 py-1.5 rounded-full text-sm font-bold mb-4 border border-[#d6ad60]/20">
            <Globe className="h-4 w-4" /> راهنمای افزونه کروم
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-3">راهنمای جامع نوسان‌گیر تریدمون</h1>
          <p className="text-gray-400 text-xs sm:text-sm leading-relaxed max-w-xl mx-auto">
            هر آنچه برای نصب و استفاده حرفه‌ای از افزونه نیاز دارید.
          </p>
        </motion.div>



        {/* بخش‌های راهنما (Accordion) */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="space-y-3 mb-10">
          {GUIDE_SECTIONS.map((section) => {
            const isOpen = openSections.includes(section.id);
            return (
              <div key={section.id} className="rounded-xl border border-white/10 bg-white/5 overflow-hidden transition-all duration-300">
                <button
                  onClick={() => toggleSection(section.id)}
                  className="w-full flex items-center justify-between p-4 text-right hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <div className="text-[#d6ad60]">{section.icon}</div>
                    <span className="text-sm font-bold text-white">{section.title}</span>
                  </div>
                  <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`} />
                </button>
                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <div className="p-4 pt-0 border-t border-white/10">
                        {section.content}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </motion.div>

        {/* دکمه بازگشت */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="text-center">
          <Link href="/dashboard">
            <Button variant="outline" className="border-white/20 text-white hover:bg-white/10 gap-2">
              <ArrowRight className="h-4 w-4" /> بازگشت به داشبورد
            </Button>
          </Link>
        </motion.div>

      </div>
    </div>
  );
}