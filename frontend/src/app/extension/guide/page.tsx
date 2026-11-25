
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ArrowRight,
  Globe,
  Download,
  FileArchive,
  FolderOpen,
  MonitorPlay,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Info,
  ChevronDown,
  Lock,
  Activity,
  Settings,
  HelpCircle,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";

// ═══════════════════════════════════════════
// راهنمای افزونه
// ═══════════════════════════════════════════

const GUIDE_SECTIONS = [
  {
    id: "before-install",
    title: "قبل از نصب افزونه",
    icon: <Info className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          افزونه کروم تریدمون برای دریافت داده‌های قیمت، تحلیل بازار و نمایش
          سیگنال‌های کمکی طراحی شده است. در حال حاضر این افزونه برای استفاده
          در وب‌سایت‌های <b className="text-white">دریا گلد و آلفا گلد</b>{" "}
          ارائه شده است.
        </p>

        <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 p-3">
          <div className="flex items-center gap-2 text-[#d6ad60] font-bold mb-2">
            <ShieldCheck className="h-4 w-4" />
            نکته مهم درباره امنیت حساب
          </div>
          <p>
            برای استفاده از افزونه نیازی به ورود به حساب معاملاتی صرافی،
            ارائه رمز عبور یا دسترسی به اطلاعات خصوصی حساب خود ندارید.
            اتصال احتمالی به حساب تریدمون، صرفاً برای استفاده از امکانات
            سرویس تریدمون است و با حساب معاملاتی شما در سایت طلا تفاوت دارد.
          </p>
        </div>

        <ul className="space-y-2 pr-4 list-disc">
          <li>برای نصب، از مرورگر Google Chrome در کامپیوتر استفاده کنید.</li>
          <li>فایل افزونه را فقط از داشبورد رسمی تریدمون دریافت کنید.</li>
          <li>پوشه افزونه را پس از استخراج جابه‌جا یا حذف نکنید.</li>
          <li>
            برای دریافت قیمت و نمایش تحلیل‌ها، صفحه مربوط به سایت پشتیبانی‌شده
            را باز نگه دارید.
          </li>
        </ul>
      </div>
    ),
  },
  {
    id: "setup",
    title: "راهنمای نصب افزونه کروم",
    icon: <MonitorPlay className="h-4 w-4" />,
    content: (
      <div className="space-y-4">
        {[
          {
            icon: <Download className="h-5 w-5" />,
            title: "۱. دانلود فایل افزونه",
            description:
              "از داشبورد تریدمون روی دکمه «دانلود افزونه» کلیک کنید و فایل ZIP را دریافت کنید.",
          },
          {
            icon: <FolderOpen className="h-5 w-5" />,
            title: "۲. استخراج فایل ZIP",
            description:
              "فایل دانلودشده را از حالت فشرده خارج کنید. پوشه‌ای که فایل‌های افزونه داخل آن قرار دارند باید در دسترس باشد.",
          },
          {
            icon: <Globe className="h-5 w-5" />,
            title: "۳. ورود به صفحه افزونه‌های کروم",
            description:
              "در نوار آدرس مرورگر کروم عبارت chrome://extensions را وارد کنید و وارد صفحه مدیریت افزونه‌ها شوید.",
            code: "chrome://extensions",
          },
          {
            icon: <Settings className="h-5 w-5" />,
            title: "۴. فعال‌کردن Developer mode",
            description:
              "گزینه Developer mode یا «حالت توسعه‌دهنده» را در صفحه افزونه‌ها فعال کنید.",
          },
          {
            icon: <FileArchive className="h-5 w-5" />,
            title: "۵. بارگذاری افزونه",
            description:
              "روی دکمه Load unpacked کلیک کنید و پوشه‌ای را انتخاب کنید که فایل‌های استخراج‌شده افزونه در آن قرار دارند.",
          },
          {
            icon: <CheckCircle2 className="h-5 w-5" />,
            title: "۶. بررسی نصب",
            description:
              "پس از بارگذاری، افزونه تریدمون باید در فهرست افزونه‌های کروم نمایش داده شود. در صورت نیاز، آیکون آن را از بخش Extensions در نوار مرورگر در دسترس قرار دهید.",
          },
          {
            icon: <MonitorPlay className="h-5 w-5" />,
            title: "۷. ورود به حساب تریدمون",
            description:
              "روی آیکون افزونه کلیک کنید و در صورت نمایش گزینه ورود یا اتصال، با حساب کاربری تریدمون وارد شوید. برای این کار نیازی به ورود به حساب معاملاتی دریا گلد یا آلفا گلد ندارید.",
          },
        ].map((step, index) => (
          <div key={index} className="flex items-start gap-3">
            <div className="mt-1 shrink-0 text-[#d6ad60]">{step.icon}</div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-white">{step.title}</p>
              <p className="mt-1 text-[11px] leading-6 text-gray-400">
                {step.description}
              </p>
              {step.code && (
                <div className="mt-2 flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 p-2">
                  <code
                    dir="ltr"
                    className="flex-1 text-left text-xs text-[#d6ad60]"
                  >
                    {step.code}
                  </code>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard?.writeText(step.code);
                    }}
                    className="rounded-md px-2 py-1 text-[10px] text-gray-400 transition hover:bg-white/10 hover:text-white"
                    aria-label="کپی آدرس صفحه افزونه‌ها"
                  >
                    کپی
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    id: "how-it-works",
    title: "افزونه چطور کار می‌کند؟",
    icon: <Activity className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          افزونه تریدمون داده‌های قیمت را از منابع قابل دسترس دریافت می‌کند
          و با استفاده از اطلاعات بازار، تحلیل‌ها و سیگنال‌های کمکی را
          در اختیار شما قرار می‌دهد.
        </p>

        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#d6ad60]" />
            <p>
              دریافت داده‌های قیمت از منابع پشتیبانی‌شده و بررسی تغییرات بازار.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#d6ad60]" />
            <p>
              پردازش داده‌ها و ارائه تحلیل و سیگنال بر اساس اطلاعات در دسترس.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#d6ad60]" />
            <p>
              نمایش قیمت با درنظرگرفتن اسپرد مربوط به هر منبع معاملاتی.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#d6ad60]" />
            <p>
              نمایش اطلاعات و امکانات تحلیلی در محیط مرورگر.
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <p className="font-bold text-white mb-1">توجه</p>
          <p>
            افزونه ابزار تحلیل و نمایش اطلاعات است؛ هیچ سفارش خرید یا فروشی
            را به‌صورت خودکار ثبت نمی‌کند و معامله‌ای به جای شما انجام نمی‌دهد.
          </p>
        </div>
      </div>
    ),
  },
  {
    id: "wait",
    title: "چرا بعد از نصب باید کمی صبر کنم؟",
    icon: <Clock className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          برای انجام تحلیل، افزونه باید داده‌های کافی از بازار دریافت کند.
          بنابراین ممکن است بلافاصله پس از نصب یا بازکردن صفحه، همه اطلاعات
          و تحلیل‌ها آماده نمایش نباشند.
        </p>

        <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 p-3">
          <div className="mb-2 flex items-center gap-2 font-bold text-[#d6ad60]">
            <Clock className="h-4 w-4" />
            پیشنهاد ما
          </div>
          <p>
            پس از بازکردن صفحه مربوط به دریا گلد یا آلفا گلد، اجازه دهید
            داده‌های بازار جمع‌آوری شوند. زمان آماده‌شدن تحلیل‌ها به
            بازه زمانی، حجم داده‌های موردنیاز و وضعیت دریافت قیمت بستگی دارد.
          </p>
        </div>

        <p>
          هرچه داده‌های موردنیاز یک تحلیل بیشتر باشد، آماده‌شدن آن ممکن است
          زمان بیشتری ببرد. در صورت خالی‌بودن اطلاعات، ابتدا اتصال اینترنت،
          بازبودن صفحه پشتیبانی‌شده و وضعیت افزونه را بررسی کنید.
        </p>
      </div>
    ),
  },
  {
    id: "privacy",
    title: "امنیت و حریم خصوصی حساب معاملاتی",
    icon: <Lock className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          افزونه تریدمون برای ارائه تحلیل و نمایش قیمت به دسترسی به حساب
          معاملاتی شما نیاز ندارد.
        </p>

        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
            <p>نیازی به واردکردن رمز عبور حساب معاملاتی نیست.</p>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
            <p>برای کارکرد افزونه، ورود به بخش خصوصی حساب صرافی لازم نیست.</p>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
            <p>افزونه سفارش خرید یا فروش ثبت نمی‌کند.</p>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
            <p>افزونه به جای شما معامله‌ای انجام نمی‌دهد.</p>
          </div>
        </div>

        <p>
          از آنجا که افزونه به حساب معاملاتی دسترسی ندارد و سفارش خودکاری
          ثبت نمی‌کند، فعالیت رباتیک معاملاتی یا ریسک مسدودی ناشی از
          ثبت سفارش خودکار ایجاد نمی‌کند.
        </p>
      </div>
    ),
  },
  {
    id: "optional",
    title: "امکانات اختیاری؛ نمایش سود و زیان",
    icon: <ShieldCheck className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          افزونه می‌تواند امکانات اختیاری مربوط به نمایش اطلاعات قیمت و
          درصد سود یا زیان را در جدول مربوط به معاملات نمایش دهد.
        </p>

        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <p className="mb-2 font-bold text-white">نحوه استفاده</p>
          <ul className="list-disc space-y-1 pr-4">
            <li>در صورت فعال‌بودن قابلیت، اطلاعات مربوط در جدول نمایش داده می‌شود.</li>
            <li>برای کپی قیمت، در صورت فعال‌بودن این قابلیت روی قیمت کلیک کنید.</li>
            <li>
              برای غیرفعال‌کردن نمایش این اطلاعات، از پاپ‌آپ افزونه و گزینه
              «نمایش امکانات آپشنال» استفاده کنید.
            </li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    id: "troubleshooting",
    title: "اگر افزونه درست کار نکرد چه کنم؟",
    icon: <RefreshCw className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>اگر قیمت یا تحلیل‌ها نمایش داده نمی‌شوند، این موارد را بررسی کنید:</p>

        <ol className="list-decimal space-y-2 pr-4">
          <li>مطمئن شوید از آخرین نسخه افزونه استفاده می‌کنید.</li>
          <li>بررسی کنید صفحه دریا گلد یا آلفا گلد باز و در دسترس باشد.</li>
          <li>اتصال اینترنت و دسترسی مرورگر به صفحه را بررسی کنید.</li>
          <li>وضعیت فعال‌بودن افزونه را در صفحه chrome://extensions بررسی کنید.</li>
          <li>در صورت نیاز، صفحه را یک‌بار تازه‌سازی کنید.</li>
          <li>اگر مشکل ادامه داشت، از طریق پشتیبانی تریدمون موضوع را گزارش دهید.</li>
        </ol>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="mb-1 flex items-center gap-2 font-bold text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            نکته
          </div>
          <p>
            اگر افزونه پس از به‌روزرسانی کروم یا دریافت نسخه جدید درست کار
            نمی‌کند، ممکن است لازم باشد نسخه قبلی را از صفحه افزونه‌ها
            به‌روزرسانی یا دوباره بارگذاری کنید.
          </p>
        </div>
      </div>
    ),
  },
  {
    id: "disclaimer",
    title: "سلب مسئولیت و نکات معاملاتی",
    icon: <AlertTriangle className="h-4 w-4" />,
    content: (
      <div className="space-y-3 text-[11px] text-gray-300 leading-7 text-justify">
        <p>
          تریدمون یک ابزار تحلیل داده و ارائه سیگنال‌های کمکی است.
          تحلیل‌ها بر اساس داده‌های در دسترس و روش‌های محاسباتی و تحلیلی
          تولید می‌شوند و ممکن است در شرایط مختلف بازار تغییر کنند.
        </p>

        <p>
          <b className="text-white">
            هیچ‌یک از تحلیل‌ها یا سیگنال‌های تریدمون تضمین‌کننده سود نیستند.
          </b>
          {" "}بازارهای مالی و معاملات طلا و سایر دارایی‌ها با ریسک همراه‌اند
          و احتمال زیان وجود دارد.
        </p>

        <p>
          تصمیم نهایی برای انجام معامله، تعیین حجم، مدیریت ریسک و ورود یا
          خروج از بازار بر عهده کاربر است. پیش از هر تصمیم معاملاتی،
          شرایط بازار و میزان ریسک‌پذیری خود را بررسی کنید.
        </p>
      </div>
    ),
  },
];

export default function ExtensionGuidePage() {
  const [openSections, setOpenSections] = useState<string[]>([
    "before-install",
    "setup",
  ]);

  const toggleSection = (id: string) => {
    setOpenSections((prev) =>
      prev.includes(id)
        ? prev.filter((sectionId) => sectionId !== id)
        : [...prev, id]
    );
  };

  const openAll = () => {
    setOpenSections(GUIDE_SECTIONS.map((section) => section.id));
  };

  const closeAll = () => {
    setOpenSections([]);
  };

  const allOpen = openSections.length === GUIDE_SECTIONS.length;

  return (
    <main
      dir="rtl"
      className="min-h-screen bg-[#030712] px-4 py-10 text-white sm:py-12"
    >
      <div className="mx-auto max-w-3xl">

        {/* هدر صفحه */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 text-center sm:mb-10"
        >
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10 px-4 py-2 text-sm font-bold text-[#d6ad60]">
            <Globe className="h-4 w-4" />
            راهنمای افزونه کروم تریدمون
          </div>

          <h1 className="mb-3 text-2xl font-black leading-relaxed text-white sm:text-3xl">
            راهنمای نصب و استفاده از افزونه
          </h1>

          <p className="mx-auto max-w-xl text-xs leading-7 text-gray-400 sm:text-sm">
            از نصب افزونه تا دریافت داده‌های قیمت و استفاده از امکانات تحلیلی؛
            مراحل را قدم‌به‌قدم دنبال کنید.
          </p>
        </motion.header>

        {/* معرفی کوتاه */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 rounded-2xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#d6ad60]/10 to-transparent p-4 sm:p-5"
        >
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-[#d6ad60]" />
            <h2 className="text-sm font-bold text-white">
              افزونه تحلیل قیمت تریدمون
            </h2>
          </div>

          <p className="text-xs leading-7 text-gray-300">
            افزونه تریدمون با دریافت داده‌های قیمت، تحلیل بازار و سیگنال‌های
            کمکی را نمایش می‌دهد. این افزونه برای استفاده به رمز عبور یا
            دسترسی به حساب معاملاتی شما نیاز ندارد و هیچ سفارش خودکاری ثبت
            نمی‌کند.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] text-gray-300">
              دریا گلد
            </span>
            <span className="rounded-lg border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] text-gray-300">
              آلفا گلد
            </span>
            <span className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-[10px] text-emerald-400">
              بدون ثبت سفارش خودکار
            </span>
          </div>
        </motion.div>

        {/* کنترل آکاردئون‌ها */}
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="text-xs font-bold text-gray-400">
            بخش‌های راهنما
          </p>

          <button
            type="button"
            onClick={allOpen ? closeAll : openAll}
            className="text-[11px] text-[#d6ad60] transition hover:text-[#f0ca80]"
          >
            {allOpen ? "بستن همه بخش‌ها" : "بازکردن همه بخش‌ها"}
          </button>
        </div>

        {/* آکاردئون راهنما */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-8 space-y-3"
        >
          {GUIDE_SECTIONS.map((section, index) => {
            const isOpen = openSections.includes(section.id);
            const contentId = `guide-content-${section.id}`;

            return (
              <motion.section
                key={section.id}
                layout
                className={`overflow-hidden rounded-xl border transition-colors duration-300 ${
                  isOpen
                    ? "border-[#d6ad60]/30 bg-white/[0.06]"
                    : "border-white/10 bg-white/[0.03]"
                }`}
              >
                <button
                  type="button"
                  onClick={() => toggleSection(section.id)}
                  aria-expanded={isOpen}
                  aria-controls={contentId}
                  className="flex w-full items-center justify-between gap-3 p-4 text-right transition-colors hover:bg-white/[0.04]"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                        isOpen
                          ? "bg-[#d6ad60]/15 text-[#d6ad60]"
                          : "bg-white/5 text-gray-400"
                      }`}
                    >
                      {section.icon}
                    </div>

                    <div className="min-w-0">
                      <span className="block text-xs font-bold leading-6 text-white sm:text-sm">
                        {section.title}
                      </span>
                      <span className="text-[10px] text-gray-500">
                        بخش {index + 1} از {GUIDE_SECTIONS.length}
                      </span>
                    </div>
                  </div>

                  <ChevronDown
                    className={`h-4 w-4 shrink-0 text-gray-400 transition-transform duration-300 ${
                      isOpen ? "rotate-180 text-[#d6ad60]" : ""
                    }`}
                  />
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={contentId}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{
                        height: { duration: 0.3 },
                        opacity: { duration: 0.2 },
                      }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-white/10 p-4 pt-4">
                        {section.content}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.section>
            );
          })}
        </motion.div>

        {/* پشتیبانی */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="mb-8 rounded-2xl border border-white/10 bg-white/[0.04] p-4 sm:p-5"
        >
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#d6ad60]/10 text-[#d6ad60]">
              <HelpCircle className="h-5 w-5" />
            </div>

            <div className="flex-1">
              <h2 className="mb-1 text-sm font-bold text-white">
                هنوز به راهنمایی نیاز دارید؟
              </h2>
              <p className="mb-3 text-[11px] leading-6 text-gray-400">
                اگر در نصب یا استفاده از افزونه با مشکلی روبه‌رو شدید،
                از طریق پشتیبانی تریدمون با ما در ارتباط باشید.
              </p>

              <Link href="/contact">
                <Button
                  variant="outline"
                  className="h-9 gap-2 border-[#d6ad60]/30 text-xs text-[#d6ad60] hover:bg-[#d6ad60]/10 hover:text-[#f0ca80]"
                >
                  ارتباط با پشتیبانی
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </div>
        </motion.div>

        {/* بازگشت به داشبورد */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-center"
        >
          <Link href="/dashboard">
            <Button
              variant="outline"
              className="h-10 gap-2 border-white/20 px-5 text-xs text-white hover:bg-white/10"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت به داشبورد
            </Button>
          </Link>
        </motion.div>

        {/* یادآوری پایانی */}
        <p className="mt-8 text-center text-[10px] leading-6 text-gray-600">
          تریدمون ابزار تحلیل و تصمیم‌یار معاملاتی است؛ استفاده از سیگنال‌ها
          جایگزین مدیریت ریسک و تصمیم‌گیری آگاهانه شما نیست.
        </p>
      </div>
    </main>
  );
}
