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
  Check,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Button } from "@/components/ui/button";

const VALUES = [
  {
    icon: Target,
    title: "شفافیت کامل",
    desc: "آمار واقعی، بدون ادعای اغراق‌آمیز. هر عدد قابل راستی‌آزمایی است.",
  },
  {
    icon: ShieldCheck,
    title: "مدیریت ریسک اول",
    desc: "هر سیگنال با حد ضرر و حد سود مشخص. حفاظت از سرمایه، اولویت ماست.",
  },
  {
    icon: Brain,
    title: "هوش مصنوعی + ریاضیات",
    desc: "ترکیب الگوریتم‌های ریاضی با AI. نه شهود، نه احساس — داده و منطق.",
  },
  {
    icon: Globe,
    title: "بومی‌سازی ایرانی",
    desc: "پشتیبانی از ۴ صرافی ایرانی. کارمزد ریالی، جفت‌های تومانی، تایم‌فریم‌های مناسب.",
  },
];

const STATS = [
  { label: "اندیکاتور تکنیکال", value: "۳۲" },
  { label: "صرافی متصل", value: "۴" },
  { label: "استراتژی معاملاتی", value: "۳" },
  { label: "تست خودکار", value: "۳۳۵+" },
];

const TEAM_ROLES = [
  { icon: TrendingUp, title: "تحلیل‌گران بازار", desc: "متخصصان مالی با تجربه" },
  { icon: Brain, title: "مهندسان داده", desc: "متخصصان الگوریتم و AI" },
  { icon: Users, title: "تیم پشتیبانی", desc: "پاسخگوی سوالات شما" },
];

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />

      <main className="flex-1">
        {/* ═══ هدر ═══ */}
        <section className="relative overflow-hidden px-4 py-16 text-center sm:py-20">
          <div className="absolute inset-0 bg-gradient-to-b from-[#d6ad60]/5 to-transparent" />
          <div className="relative mx-auto max-w-3xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#d6ad60]/30 bg-[#d6ad60]/10 px-4 py-1.5 text-xs font-medium text-[#d6ad60]">
                <Sparkles className="h-4 w-4" />
                درباره تریدمون
              </div>
              <h1 className="font-display text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
                ما معتقدیم هر معامله‌گر
                <br />
                <span className="text-[#d6ad60]">لایق تحلیل حرفه‌ای است</span>
              </h1>
              <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-gray-400 sm:text-base">
                تریدمون یک پلتفرم تحلیل تکنیکال است که با ترکیب الگوریتم‌های
                ریاضی، داده‌های تاریخی و هوش مصنوعی، به معامله‌گران ایرانی کمک
                می‌کند تصمیم‌های بهتری بگیرند.
              </p>
            </motion.div>
          </div>
        </section>

        {/* ═══ آمار ═══ */}
        <section className="px-4 pb-12">
          <div className="mx-auto grid max-w-4xl grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            {STATS.map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-xl border border-white/10 bg-[#0d1b2d] p-4 text-center"
              >
                <div className="num text-2xl font-bold text-[#d6ad60] sm:text-3xl">
                  {stat.value}
                </div>
                <div className="mt-1 text-[10px] text-gray-400">
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ═══ داستان ما ═══ */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-3xl">
            <h2 className="mb-6 text-center font-display text-2xl font-bold sm:text-3xl">
              داستان ما
            </h2>
            <div className="space-y-4 rounded-2xl border border-white/10 bg-[#0d1b2d] p-6 text-sm leading-relaxed text-gray-300 sm:p-8">
              <p>
                در بازار پرنوسان کریپتو و بورس ایران، معامله‌گران با انبوهی از
                اطلاعات، سیگنال‌های متناقض و ابزارهای غیربومی روبرو هستند.
                تحلیل تکنیکال حرفه‌ای معمولاً در انحصار پلتفرم‌های خارجی
                گران‌قیمت است که با شرایط بازار ایران سازگار نیستند.
              </p>
              <p>
                <span className="font-bold text-[#d6ad60]">تریدمون</span> با این
                باور متولد شد که هر معامله‌گر — از تازه‌کار تا حرفه‌ای — باید به
                تحلیل‌های دقیق، شفاف و قابل اعتماد دسترسی داشته باشد. ما یک موتور
                تحلیل‌گر ریاضی ساختیم که ۳۲ اندیکاتور حرفه‌ای را در ۵ گروه تخصصی
                ترکیب می‌کند و بر اساس داده‌های واقعی بازار ایران، سیگنال تولید
                می‌کند.
              </p>
              <p>
                امروز تریدمون به ۴ صرافی ایرانی (نوبیتکس، بیت‌پین، والکس، تبدیل)
                متصل است، از ۳ استراتژی معاملاتی (اسکالپ، سوئینگ، پوزیشن)
                پشتیبانی می‌کند، و با راستی‌آزمایی خودکار سیگنال‌ها، شفافیت کامل
                در آمار را تضمین می‌کند.
              </p>
            </div>
          </div>
        </section>

        {/* ═══ ارزش‌ها ═══ */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-4xl">
            <h2 className="mb-2 text-center font-display text-2xl font-bold sm:text-3xl">
              ارزش‌های ما
            </h2>
            <p className="mb-8 text-center text-sm text-gray-400">
              ۴ اصل که هر تصمیم ما را هدایت می‌کند
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {VALUES.map((v, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="rounded-2xl border border-white/10 bg-[#0d1b2d] p-5 transition-colors hover:border-[#d6ad60]/30"
                >
                  <div className="mb-3 inline-flex rounded-xl bg-[#d6ad60]/15 p-2.5">
                    <v.icon className="h-5 w-5 text-[#d6ad60]" />
                  </div>
                  <h3 className="mb-2 text-base font-bold">{v.title}</h3>
                  <p className="text-xs leading-relaxed text-gray-400">
                    {v.desc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ تیم ═══ */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-4xl">
            <h2 className="mb-2 text-center font-display text-2xl font-bold sm:text-3xl">
              تیم ما
            </h2>
            <p className="mb-8 text-center text-sm text-gray-400">
              ترکیبی از تخصص مالی، مهندسی داده و پشتیبانی
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {TEAM_ROLES.map((t, i) => (
                <div
                  key={i}
                  className="rounded-2xl border border-white/10 bg-[#0d1b2d] p-5 text-center"
                >
                  <div className="mx-auto mb-3 inline-flex rounded-full bg-[#d6ad60]/15 p-3">
                    <t.icon className="h-6 w-6 text-[#d6ad60]" />
                  </div>
                  <h3 className="mb-1 text-sm font-bold">{t.title}</h3>
                  <p className="text-[11px] text-gray-400">{t.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ CTA ═══ */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-2xl rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-br from-[#d6ad60]/10 to-transparent p-8 text-center">
            <h2 className="mb-3 font-display text-2xl font-bold">
              آماده‌ای شروع کنی؟
            </h2>
            <p className="mb-6 text-sm text-gray-400">
              ۳ روز رایگان — بدون نیاز به کارت بانکی
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/login">
                <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-8 text-sm font-bold text-[#07111f] hover:opacity-90 sm:w-auto">
                  <Zap className="h-4 w-4" /> شروع رایگان
                </Button>
              </Link>
              <Link href="/contact">
                <Button
                  variant="outline"
                  className="h-11 w-full gap-2 border-white/20 text-white hover:bg-white/5 sm:w-auto"
                >
                  تماس با ما
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}