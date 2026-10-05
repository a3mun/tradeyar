"use client";

import { useState } from "react";
import { HelpCircle, Book, Zap, BarChart3, Shield, Sparkles, Layers, AlertTriangle, TrendingUp } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

const SECTIONS = [
  {
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    title: "شروع سریع",
    content: [
      "نماد رو از جستجو یا Popular انتخاب کن",
      "صرافی، تایم‌فریم و پروفایل ریسک رو تنظیم کن",
      "سیگنال توی کارت وسط صفحه نمایش داده می‌شه",
      "برای دیدن ۶ نماد برتر، زیر جستجو نگاه کن",
    ],
  },
  {
    icon: <BarChart3 className="h-4 w-4 text-green-400" />,
    title: "تحلیل ۵ گروهی",
    content: [
      "⚡ مومنتوم: RSI، Stochastic، Williams، CCI، ROC",
      "📈 روند: EMA200، MACD، ADX، Supertrend",
      "📊 نوسان: Bollinger، ATR، Keltner، Donchian",
      "💧 حجم: OBV، CVD، Delta، CMF، MFI",
      "🏗 ساختار: Pivot، Swing، Fibonacci، S/R",
      "هر گروه رأی صعودی/نزولی/خنثی می‌ده — اگه ۳ گروه هم‌جهت باشن → سیگنال",
    ],
  },
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "مدیریت ریسک",
    content: [
      "هر سیگنال حد ضرر (SL) و هدف (TP) داره",
      "R:R خام = ۲ یعنی ۱ ریسک، ۲ سود",
      "⚠️ R:R **خالص** (بعد از کارمزد) مهم‌تره",
      "پروفایل جسورانه: ۲-۳٪ سرمایه · محتاطانه: ۱-۲٪",
      "هیچ‌وقت بدون SL وارد نشو",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "کارمزد و R:R خالص",
    content: [
      "کارمزد رفت‌وبرگشتی صرافی‌های ایران: ۰.۲-۰.۶٪",
      "USD: ۰.۲۳٪ · IRT: ۰.۵۰٪ (نوبیتکس)",
      "R:R خام ۲ می‌تونه بعد کارمزد بشه ۱.۷ یا کمتر",
      "⚠️ در TF کوتاه (۱-۵ دقیقه)، کارمزد می‌تونه کل سود رو بخوره",
      "روی خط هزینه بزن تا جزئیات ببینی",
    ],
  },
  {
    icon: <Layers className="h-4 w-4 text-orange-400" />,
    title: "عمق بازار (Order Book)",
    content: [
      "imbalance = نسبت حجم خرید به فروش",
      "بالای ۰.۵۵ = فشار خرید · زیر ۰.۴۵ = فشار فروش",
      "اسپرد کم = نقدینگی خوب · اسپرد زیاد = ریسک اسلیپیج",
      "🧱 دیوار سفارش = سطح با حجم غیرعادی",
      "⚠️ عمق بازار لحظه‌ای است و بین صرافی‌ها فرق می‌کنه — فقط تأییدکننده، نه توصیه",
    ],
  },
  {
    icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
    title: "هشدار تله‌ها",
    content: [
      "🚨 تله صعودی: مومنتوم صعودی ولی جریان پول خروجی",
      "🚨 تله نزولی: مومنتوم نزولی ولی جریان پول ورودی",
      "⚠️ شکست جعلی: ADX قوی ولی حجم کم",
      "😮‍💨 خستگی روند: ADX قوی ولی مومنتوم ضعیف",
      "⚠️ وقتی تله فعاله، سیگنال ریسک‌داره — با احتیاط بیشتر",
    ],
  },
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "تحلیل هوش مصنوعی",
    content: [
      "دو راه داری:",
      "۱. کپی داده‌ها برای AI — ببر توی ChatGPT/Gemini/Claude",
      "۲. کلید DeepSeek/OpenAI خودت رو وارد کن",
      "⚠️ AI فقط مشاوره‌ست، نه تصمیم نهایی",
    ],
  },
  {
    icon: <Book className="h-4 w-4 text-emerald-400" />,
    title: "راستی‌آزمایی خودکار",
    content: [
      "سیگنال‌های LONG/SHORT خودکار ثبت می‌شن",
      "سیستم هر ۵ دقیقه بررسی می‌کنه که به SL/TP رسیدن",
      "برد/باخت/منقضی خودکار تشخیص داده می‌شه",
      "آمار توی صفحه پایین نمایش داده می‌شه",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-pink-400" />,
    title: "شاخص ترس و طمع",
    content: [
      "۰-۲۵: ترس شدید (احتمال کف)",
      "۲۵-۴۵: ترس",
      "۴۵-۵۵: خنثی",
      "۵۵-۷۵: طمع",
      "۷۵-۱۰۰: طمع شدید (احتمال سقف)",
    ],
  },
];

export function HelpPanel() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger className="inline-flex h-8 items-center gap-1 rounded-md border border-border/60 px-2 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground md:h-9 md:px-3 md:text-sm">
        <HelpCircle className="h-3.5 w-3.5 md:h-4 md:w-4" />
        <span>راهنما</span>
      </SheetTrigger>
      <SheetContent side="left" className="w-full max-w-md overflow-y-auto sm:w-96">
        <div className="mt-6 space-y-4">
          <div className="text-center">
            <h2 className="text-lg font-bold">راهنما</h2>
            <p className="text-xs text-muted-foreground mt-1">
              آشنایی سریع با تریدمون
            </p>
          </div>

          <div className="space-y-3">
            {SECTIONS.map((section, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-border/40 bg-muted/10 p-3"
              >
                <div className="flex items-center gap-2 mb-2">
                  {section.icon}
                  <h3 className="text-xs font-bold">{section.title}</h3>
                </div>
                <ul className="space-y-1 pr-4 text-[10px] text-muted-foreground list-disc">
                  {section.content.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-center">
            <p className="text-[10px] text-muted-foreground">
              Trademun v6.0 · دستیار هوشمند معامله‌گر
            </p>
            <p className="mt-1 text-[9px] text-muted-foreground/70">
              ⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارن — تصمیم نهایی با خودته
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}