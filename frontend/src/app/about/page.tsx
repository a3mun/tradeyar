
"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Sparkles,
  Target,
  TrendingUp,
  ShieldCheck,
  Brain,
  Globe,
  Users,
  Zap,
  Activity,
  BarChart3,
  CandlestickChart,
  Database,
  ChartNoAxesCombined,
} from "lucide-react";

import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Button } from "@/components/ui/button";

const VALUES = [
  {
    icon: Target,
    title: "شفافیت در تحلیل",
    desc: "تلاش می‌کنیم اطلاعات، سناریوها و نتایج سیگنال‌ها به شکلی روشن و قابل بررسی در اختیار کاربران قرار بگیرند.",
  },
  {
    icon: ShieldCheck,
    title: "توجه به مدیریت ریسک",
    desc: "تحلیل بدون توجه به ریسک کامل نیست. نمایش محدوده‌های ورود، حد ضرر و اهداف قیمتی به تصمیم‌گیری آگاهانه‌تر کمک می‌کند.",
  },
  {
    icon: Brain,
    title: "ترکیب فناوری و تحلیل",
    desc: "از الگوریتم‌های تحلیلی، اندیکاتورهای تکنیکال و هوش مصنوعی برای بررسی داده‌های بازار و ارائه دیدی جامع‌تر استفاده می‌کنیم.",
  },
  {
    icon: Globe,
    title: "توجه به بازار ایران",
    desc: "بازارهای داخلی و نیاز معامله‌گران ایرانی را در طراحی ابزارها در نظر گرفته‌ایم؛ از رمزارز و بورس تا طلا و بازارهای جهانی.",
  },
];

const STATS = [
  { label: "اندیکاتور تکنیکال", value: "۲۵+" },
  { label: "بازار و منبع معاملاتی", value: "۶" },
  { label: "سبک معاملاتی", value: "۳" },
  { label: "روز دسترسی آزمایشی", value: "۳" },
];

const FEATURES = [
  {
    icon: CandlestickChart,
    title: "تحلیل تکنیکال بازار",
    desc: "بررسی نمودارها، روندها، حمایت و مقاومت و شرایط بازار با کمک ابزارهای تحلیلی.",
  },
  {
    icon: Activity,
    title: "سیگنال‌ها و سناریوها",
    desc: "مشاهده فرصت‌های معاملاتی، محدوده‌های قیمتی، اهداف و حد ضرر برای بررسی بهتر موقعیت‌ها.",
  },
  {
    icon: BarChart3,
    title: "بررسی و مقایسه بازارها",
    desc: "دسترسی به اطلاعات بازارهای رمزارزی، بورس تهران و بازارهای جهانی در یک محیط یکپارچه.",
  },
  {
    icon: Brain,
    title: "مشاور هوشمند",
    desc: "استفاده از هوش مصنوعی برای کمک به بررسی بازار و پاسخ‌گویی به پرسش‌های معاملاتی.",
  },
  {
    icon: ChartNoAxesCombined,
    title: "اسکنر فرصت‌های بازار",
    desc: "شناسایی و بررسی نمادهایی که با شرایط و معیارهای تحلیلی موردنظر هم‌خوانی دارند.",
  },
  {
    icon: Database,
    title: "داده و ابزارهای تکمیلی",
    desc: "ابزارهایی مانند عمق بازار، شاخص ترس و طمع و مقایسه قیمت‌ها برای شناخت بهتر وضعیت بازار.",
  },
];

const TEAM_ROLES = [
  {
    icon: TrendingUp,
    title: "تحلیل و بازارهای مالی",
    desc: "تمرکز بر بررسی رفتار بازار و توسعه ابزارهای تحلیل معاملاتی.",
  },
  {
    icon: Brain,
    title: "فناوری و هوش مصنوعی",
    desc: "توسعه الگوریتم‌ها، پردازش داده‌ها و قابلیت‌های هوشمند پلتفرم.",
  },
  {
    icon: Users,
    title: "ارتباط با کاربران",
    desc: "دریافت بازخوردها، پاسخ‌گویی و تلاش برای بهبود تجربه استفاده از تریدمون.",
  },
];

export default function AboutPage() {
  return (
    <div
      dir="rtl"
      className="flex min-h-screen flex-col bg-[#030712] text-white"
    >
      <Header />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden px-4 py-16 text-center sm:py-24">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#d6ad60]/10 via-transparent to-transparent" />
          <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full bg-[#d6ad60]/10 blur-[100px]" />

          <div className="relative mx-auto max-w-4xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d6ad60]/30 bg-[#d6ad60]/10 px-4 py-2 text-xs font-medium text-[#d6ad60]">
                <Sparkles className="h-4 w-4" />
                درباره تریدمون
              </div>

              <h1 className="font-display text-3xl font-extrabold leading-[1.5] sm:text-4xl lg:text-5xl">
                ابزارهای هوشمند برای
                <br />
                <span className="text-[#d6ad60]">
                  تصمیم‌گیری آگاهانه‌تر در بازار
                </span>
              </h1>

              <p className="mx-auto mt-6 max-w-2xl text-justify text-sm leading-8 text-gray-400 sm:text-base">
                تریدمون یک پلتفرم تحلیل و پایش بازارهای مالی است که با ترکیب
                تحلیل تکنیکال، الگوریتم‌های محاسباتی، داده‌های بازار و هوش
                مصنوعی، ابزارهای کاربردی را برای بررسی فرصت‌های معاملاتی در
                اختیار کاربران قرار می‌دهد. هدف ما کمک به معامله‌گران برای
                شناخت بهتر شرایط بازار و تصمیم‌گیری بر پایه اطلاعات است.
              </p>

              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                <Link href="/login">
                  <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-7 text-sm font-bold text-[#07111f] hover:opacity-90 sm:w-auto">
                    شروع رایگان
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                </Link>

                <Link href="/subscription">
                  <Button
                    variant="outline"
                    className="h-11 w-full border-white/10 px-7 text-sm text-white hover:bg-white/5 sm:w-auto"
                  >
                    مشاهده اشتراک‌ها
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Stats */}
        <section className="px-4 pb-14">
          <div className="mx-auto grid max-w-5xl grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className="rounded-2xl border border-white/5 bg-[#051118] p-5 text-center shadow-sm transition-colors hover:border-[#d6ad60]/20"
              >
                <div className="num text-3xl font-extrabold text-[#d6ad60] sm:text-4xl">
                  {stat.value}
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Story */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-4xl">
            <div className="mb-8 text-center">
              <span className="text-xs font-semibold text-[#d6ad60]">
                مسیر ما
              </span>
              <h2 className="mt-2 font-display text-2xl font-bold sm:text-3xl">
                داستان تریدمون
              </h2>
            </div>

            <div className="space-y-5 rounded-2xl border border-white/5 bg-[#051118] p-6 text-justify text-sm leading-8 text-gray-300 shadow-sm sm:p-9">
              <p>
                فعالیت در بازارهای مالی، به‌ویژه در شرایط پرنوسان، به بررسی
                مداوم اطلاعات و شناخت دقیق‌تر رفتار قیمت نیاز دارد. تعدد
                ابزارها، پراکندگی داده‌ها و دشواری تحلیل هم‌زمان چند بازار
                می‌تواند تصمیم‌گیری را برای معامله‌گران پیچیده کند.
              </p>

              <p>
                <span className="font-bold text-[#d6ad60]">تریدمون</span> با
                هدف ساده‌تر کردن این مسیر شکل گرفت؛ بستری که ابزارهای موردنیاز
                برای بررسی بازار را در یک محیط یکپارچه جمع‌آوری کند و دسترسی
                کاربران به اطلاعات تحلیلی را آسان‌تر سازد.
              </p>

              <p>
                در تریدمون از بیش از ۲۵ اندیکاتور تکنیکال، الگوریتم‌های تحلیلی
                و ابزارهای مکمل برای بررسی شرایط بازار استفاده می‌شود. کاربران
                می‌توانند روند قیمت، حمایت و مقاومت، عمق بازار، سناریوهای
                معاملاتی و وضعیت سیگنال‌ها را بررسی کنند و از مشاور هوشمند و
                اسکنر فرصت‌ها نیز کمک بگیرند.
              </p>

              <p>
                امروز تریدمون اطلاعات و ابزارهای مرتبط با ۶ بازار و منبع
                معاملاتی را پوشش می‌دهد: نوبیتکس، بیت‌پین، والکس، تبدیل، بورس
                تهران و بازار فارکس و کالا. امکانات هر منبع متناسب با نوع داده
                و دسترسی آن متفاوت است؛ برای مثال، تحلیل کندلی رمزارز در
                صرافی‌های پشتیبانی‌شده ارائه می‌شود و اطلاعات تبدیل شامل قیمت
                و عمق بازار است.
              </p>

              <p>
                مسیر توسعه تریدمون ادامه دارد. ما با توجه به بازخورد کاربران،
                تغییرات بازار و نیازهای معامله‌گران، برای بهبود ابزارها و
                گسترش قابلیت‌های پلتفرم تلاش می‌کنیم.
              </p>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-5xl">
            <div className="mb-8 text-center">
              <span className="text-xs font-semibold text-[#d6ad60]">
                امکانات پلتفرم
              </span>
              <h2 className="mt-2 font-display text-2xl font-bold sm:text-3xl">
                تریدمون چه امکاناتی دارد؟
              </h2>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-gray-400">
                مجموعه‌ای از ابزارهای تحلیلی و کاربردی برای بررسی بهتر
                بازارهای مالی، در یک محیط واحد.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature, i) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ delay: i * 0.05 }}
                  className="rounded-2xl border border-white/5 bg-[#051118] p-5 transition-all hover:-translate-y-1 hover:border-[#d6ad60]/30"
                >
                  <div className="mb-4 inline-flex rounded-xl bg-[#d6ad60]/10 p-3">
                    <feature.icon className="h-5 w-5 text-[#d6ad60]" />
                  </div>

                  <h3 className="mb-2 text-sm font-bold text-gray-100">
                    {feature.title}
                  </h3>

                  <p className="text-justify text-xs leading-7 text-gray-400">
                    {feature.desc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Values */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-5xl">
            <div className="mb-8 text-center">
              <span className="text-xs font-semibold text-[#d6ad60]">
                رویکرد ما
              </span>
              <h2 className="mt-2 font-display text-2xl font-bold sm:text-3xl">
                ارزش‌های تریدمون
              </h2>
              <p className="mt-3 text-sm text-gray-400">
                اصولی که در طراحی و توسعه پلتفرم دنبال می‌کنیم
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {VALUES.map((value, i) => (
                <motion.div
                  key={value.title}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ delay: i * 0.06 }}
                  className="rounded-2xl border border-white/5 bg-[#051118] p-6 transition-colors hover:border-[#d6ad60]/30"
                >
                  <div className="mb-4 inline-flex rounded-xl bg-[#d6ad60]/10 p-3">
                    <value.icon className="h-5 w-5 text-[#d6ad60]" />
                  </div>

                  <h3 className="mb-2 text-base font-bold text-gray-100">
                    {value.title}
                  </h3>

                  <p className="text-justify text-xs leading-7 text-gray-400">
                    {value.desc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Team approach */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-5xl">
            <div className="mb-8 text-center">
              <span className="text-xs font-semibold text-[#d6ad60]">
                پشت صحنه تریدمون
              </span>
              <h2 className="mt-2 font-display text-2xl font-bold sm:text-3xl">
                حوزه‌های تخصصی ما
              </h2>
              <p className="mt-3 text-sm text-gray-400">
                بخش‌هایی که در توسعه و پشتیبانی پلتفرم نقش دارند
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {TEAM_ROLES.map((role, i) => (
                <motion.div
                  key={role.title}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ delay: i * 0.06 }}
                  className="rounded-2xl border border-white/5 bg-[#051118] p-6 text-center shadow-sm"
                >
                  <div className="mx-auto mb-4 inline-flex rounded-full bg-[#d6ad60]/10 p-4">
                    <role.icon className="h-6 w-6 text-[#d6ad60]" />
                  </div>

                  <h3 className="mb-2 text-sm font-bold text-gray-100">
                    {role.title}
                  </h3>

                  <p className="text-xs leading-7 text-gray-400">
                    {role.desc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Fundamental analysis coming soon */}
        <section className="px-4 py-8">
          <div className="mx-auto flex max-w-4xl flex-col items-center gap-3 rounded-2xl border border-[#d6ad60]/20 bg-gradient-to-l from-[#d6ad60]/10 to-transparent p-6 text-center sm:flex-row sm:justify-between sm:text-right">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 text-sm font-bold text-[#d6ad60]">
                <Sparkles className="h-4 w-4" />
                در مسیر توسعه
              </div>
              <h3 className="text-base font-bold text-white">
                تحلیل بنیادین؛ به‌زودی
              </h3>
              <p className="mt-2 text-xs leading-6 text-gray-400">
                در حال توسعه قابلیت‌های جدید برای تکمیل ابزارهای بررسی بازار
                هستیم.
              </p>
            </div>
            <div className="shrink-0 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10 px-4 py-2 text-xs text-[#d6ad60]">
              به‌زودی
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="px-4 py-14">
          <div className="relative mx-auto max-w-3xl overflow-hidden rounded-3xl border border-[#d6ad60]/25 bg-gradient-to-br from-[#d6ad60]/10 via-[#051118] to-[#051118] p-7 text-center shadow-sm sm:p-10">
            <div className="pointer-events-none absolute -left-16 -top-16 h-48 w-48 rounded-full bg-[#d6ad60]/10 blur-[80px]" />

            <div className="relative">
              <div className="mx-auto mb-4 inline-flex rounded-2xl bg-[#d6ad60]/10 p-3">
                <Zap className="h-6 w-6 text-[#d6ad60]" />
              </div>

              <h2 className="font-display text-2xl font-extrabold sm:text-3xl">
                بازار را آگاهانه‌تر بررسی کن
              </h2>

              <p className="mx-auto mb-7 mt-3 max-w-lg text-sm leading-7 text-gray-400">
                با ثبت‌نام در تریدمون، به مدت ۳ روز به امکانات فعال پلتفرم
                دسترسی آزمایشی داشته باش.
              </p>

              <div className="flex flex-col justify-center gap-3 sm:flex-row">
                <Link href="/login">
                  <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-8 text-sm font-bold text-[#07111f] hover:opacity-90 sm:w-auto">
                    شروع رایگان
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                </Link>

                <Link href="/contact">
                  <Button
                    variant="outline"
                    className="h-11 w-full border-white/10 px-8 text-sm text-white hover:bg-white/5 sm:w-auto"
                  >
                    ارتباط با ما
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Disclaimer */}
        <section className="px-4 pb-12">
          <p className="mx-auto max-w-3xl text-center text-[11px] leading-7 text-gray-500">
            تریدمون ابزار تحلیل و پایش بازار است و محتوای آن توصیه قطعی
            سرمایه‌گذاری محسوب نمی‌شود. تصمیم‌گیری و انجام معاملات بر عهده
            کاربر است و هیچ ابزار یا سیگنالی سود یا نتیجه مشخصی را تضمین
            نمی‌کند.
          </p>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
