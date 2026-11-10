"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Send,
  Globe,
  MessageCircle,
  Clock,
  ArrowLeft,
  Shield,
  Headphones,
  Ticket,
  CheckCircle2,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Button } from "@/components/ui/button";

const CONTACT_METHODS = [
  {
    icon: Send,
    title: "کانال تلگرام",
    subtitle: "دریافت خودکار سیگنال‌های روزانه",
    link: "https://t.me/trademun",
    label: "t.me/trademun",
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/20",
    primary: true,
    action: "عضویت در کانال",
  },
  {
    icon: MessageCircle,
    title: "کانال بله",
    subtitle: "دریافت خودکار سیگنال‌های روزانه",
    link: "https://ble.ir/trademun",
    label: "ble.ir/trademun",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    primary: true,
    action: "عضویت در کانال",
  },
  {
    icon: Ticket,
    title: "تیکت در پنل کاربری",
    subtitle: "برای مشکلات حساب، اشتراک و پرداخت",
    link: "/dashboard/tickets",
    label: "داشبورد → تیکت‌ها",
    color: "text-[#d6ad60]",
    bg: "bg-[#d6ad60]/10",
    border: "border-[#d6ad60]/20",
    primary: false,
    action: "ثبت تیکت",
  },
];

const FAQ_QUICK = [
  {
    q: "چطور اشتراک بخرم؟",
    a: "از داشبورد → اشتراک، یا مستقیم از صفحه /subscription. کارت‌به‌کارت یا زیبال.",
  },
  {
    q: "اشتراکم فعال نشده، چیکار کنم؟",
    a: "از پنل کاربری → تیکت‌ها، تیکت بزنید. معمولاً کمتر از ۲۴ ساعت پاسخ می‌دیم.",
  },
  {
    q: "سیگنال چرا نمی‌بینم؟",
    a: "شاید بازار خوابه، یا استراتژی/تایم‌فریم مناسبی انتخاب نکردی. راهنما رو ببین.",
  },
];

export default function ContactPage() {
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
                <Headphones className="h-4 w-4" />
                تماس با ما
              </div>
              <h1 className="font-display text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
                هر سوالی داری،
                <br />
                <span className="text-[#d6ad60]">ما اینجاییم</span>
              </h1>
              <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-gray-400 sm:text-base">
                از سه راه می‌تونی با ما در ارتباط باشی. سریع‌ترین راه، عضویت در
                کانال‌های تلگرام و بله است.
              </p>
            </motion.div>
          </div>
        </section>

        {/* ═══ راه‌های ارتباط ═══ */}
        <section className="px-4 pb-12">
          <div className="mx-auto max-w-4xl">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {CONTACT_METHODS.map((m, i) => (
                <motion.a
                  key={i}
                  href={m.link}
                  target={m.link.startsWith("http") ? "_blank" : undefined}
                  rel={m.link.startsWith("http") ? "noreferrer" : undefined}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`group flex flex-col rounded-2xl border ${m.border} ${m.bg} p-5 transition-all hover:scale-[1.02] hover:shadow-lg`}
                >
                  <div className={`mb-3 inline-flex rounded-xl bg-white/5 p-2.5 ${m.color} w-fit`}>
                    <m.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mb-1 text-base font-bold">{m.title}</h3>
                  <p className="mb-3 text-[11px] leading-relaxed text-gray-400">
                    {m.subtitle}
                  </p>
                  <div className="mt-auto flex items-center justify-between">
                    <span
                      className="num text-[10px] text-gray-500"
                      dir="ltr"
                    >
                      {m.label}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 text-[11px] font-bold ${m.color}`}
                    >
                      {m.action}
                      <ArrowLeft className="h-3 w-3 transition-transform group-hover:-translate-x-1" />
                    </span>
                  </div>
                </motion.a>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ ساعات پاسخ‌دهی ═══ */}
        <section className="px-4 pb-12">
          <div className="mx-auto max-w-2xl">
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1b2d] p-5">
              <div className="rounded-xl bg-[#d6ad60]/15 p-2.5">
                <Clock className="h-5 w-5 text-[#d6ad60]" />
              </div>
              <div>
                <h3 className="text-sm font-bold">ساعات پاسخ‌دهی</h3>
                <p className="text-xs text-gray-400">
                  شنبه تا پنجشنبه، ۹ صبح تا ۹ شب
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ سوالات سریع ═══ */}
        <section className="px-4 py-12">
          <div className="mx-auto max-w-3xl">
            <h2 className="mb-2 text-center font-display text-2xl font-bold sm:text-3xl">
              سوالات پرتکرار
            </h2>
            <p className="mb-8 text-center text-sm text-gray-400">
              شاید جوابت اینجا باشه
            </p>
            <div className="space-y-3">
              {FAQ_QUICK.map((faq, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/10 bg-[#0d1b2d] p-4"
                >
                  <h3 className="mb-2 text-sm font-bold text-white">
                    {faq.q}
                  </h3>
                  <p className="text-xs leading-relaxed text-gray-400">
                    {faq.a}
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-6 text-center">
              <Link href="/faq">
                <Button
                  variant="outline"
                  className="gap-2 border-white/20 text-white hover:bg-white/5"
                >
                  مشاهده همه سوالات
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* ═══ امنیت ═══ */}
        <section className="px-4 pb-16">
          <div className="mx-auto max-w-2xl rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-emerald-500/15 p-2.5">
                <Shield className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="mb-1 text-sm font-bold text-emerald-400">
                  امنیت ارتباط شما
                </h3>
                <p className="text-xs leading-relaxed text-gray-400">
                  تریدمون هیچ‌وقت از طریق پیام خصوصی، شماره کارت یا رمز عبور
                  درخواست نمی‌کند. برای پرداخت، فقط از شماره کارت رسمی در صفحه
                  اشتراک استفاده کنید.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}