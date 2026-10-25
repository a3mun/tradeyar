"use client";

import { useState } from "react";
import {
  HelpCircle,
  Book,
  Zap,
  BarChart3,
  Shield,
  Sparkles,
  Layers,
  AlertTriangle,
  TrendingUp,
  Brain,
  Target,
  Filter,
} from "lucide-react";
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
      "از جستجو یا دکمه‌های نماد محبوب (بالای صفحه) نماد را انتخاب کن.",
      "صرافی، تایم‌فریم و پروفایل ریسک را از پنل سمت راست تنظیم کن.",
      "بعد از انتخاب، کارت تحلیل در وسط صفحه ظاهر می‌شود.",
      "برای ذخیره‌ی نماد در واچ‌لیست، روی ستاره بزن.",
    ],
  },
  {
    icon: <Brain className="h-4 w-4 text-blue-400" />,
    title: "نماد بورس (TSETMC)",
    content: [
      "نمادهای بورس (مثل فولاد، شپنا، آگاس) را با جستجو انتخاب کن.",
      "بورس فقط تایم‌فریم روزانه دارد و بازار آن اسپات است.",
      "تایم‌فریم و بازار به صورت خودکار تنظیم می‌شوند.",
      "با انتخاب مجدد یک نماد کریپتو، تنظیمات به حالت اول برمی‌گردد.",
    ],
  },
  {
    icon: <BarChart3 className="h-4 w-4 text-green-400" />,
    title: "تحلیل ۵ گروهی",
    content: [
      "⚡ مومنتوم: RSI، Stochastic، Williams، CCI، ROC",
      "📈 روند: EMA200، MACD، ADX، Supertrend، Ichimoku",
      "📊 نوسان: Bollinger، ATR، Keltner، Donchian",
      "💧 حجم: OBV، CVD، Delta، CMF، MFI",
      "🏗 ساختار: Pivot، Swing، Fibonacci، S/R",
      "هر گروه یک رأی صعودی، نزولی یا خنثی می‌دهد.",
    ],
  },
  {
    icon: <Target className="h-4 w-4 text-orange-400" />,
    title: "اولویت روند بر سیگنال",
    content: [
      "اگر روند قوی صعودی باشد، سیگنال فروش (SHORT) صادر نمی‌شود.",
      "اگر روند قوی نزولی باشد، سیگنال خرید (LONG) صادر نمی‌شود.",
      "این تصمیم بر اساس داده‌های واقعی گرفته شده که ۱۰۰٪ بردها در جهت روند بوده‌اند.",
      "نتیجه: کیفیت سیگنال بالاتر و ضرر کمتر.",
    ],
  },
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "مدیریت ریسک",
    content: [
      "هر سیگنال دارای حد ضرر (SL) و حد سود (TP) است.",
      "نسبت R:R خام = ۲ یعنی در برابر ۱ واحد ریسک، ۲ واحد سود.",
      "⚠️ R:R خالص (بعد از کارمزد) مهم‌ترین معیار است.",
      "پروفایل جسورانه: ۲-۳٪ سرمایه · محتاطانه: ۱-۲٪ سرمایه.",
      "هیچ‌وقت بدون حد ضرر وارد معامله نشو.",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "کارمزد و R:R خالص",
    content: [
      "کارمزد رفت‌وبرگشتی صرافی‌های ایران بین ۰.۲ تا ۰.۶ درصد است.",
      "کارمزد جفت‌های USDT حدود ۰.۲۳٪ و جفت‌های تومانی حدود ۰.۵۰٪ است.",
      "R:R خام ۲ ممکن است بعد از کارمزد به ۱.۷ یا کمتر برسد.",
      "⚠️ در تایم‌فریم‌های کوتاه (۱ تا ۵ دقیقه) کارمزد می‌تواند کل سود را ببلعد.",
      "برای دیدن جزئیات، روی خط هزینه در کارت سیگنال کلیک کن.",
    ],
  },
  {
    icon: <Layers className="h-4 w-4 text-orange-400" />,
    title: "عمق بازار (Order Book)",
    content: [
      "imbalance = نسبت حجم خرید به فروش.",
      "بالای ۰.۵۵ = فشار خرید · زیر ۰.۴۵ = فشار فروش.",
      "اسپرد کم = نقدینگی خوب · اسپرد زیاد = ریسک اسلیپیج.",
      "🧱 دیوار سفارش = سطح با حجم غیرعادی.",
      "⚠️ عمق بازار لحظه‌ای است و بین صرافی‌ها تفاوت دارد.",
    ],
  },
  {
    icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
    title: "هشدار تله‌ها",
    content: [
      "🚨 تله صعودی: مومنتوم صعودی ولی جریان پول خروجی.",
      "🚨 تله نزولی: مومنتوم نزولی ولی جریان پول ورودی.",
      "⚠️ شکست جعلی: ADX قوی ولی حجم کم.",
      "😮‍💨 خستگی روند: ADX قوی ولی مومنتوم ضعیف.",
      "⚠️ وقتی تله فعال باشد، سیگنال ریسک‌دار می‌شود.",
    ],
  },
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "تحلیل هوش مصنوعی",
    content: [
      "دو روش برای استفاده از AI وجود دارد:",
      "۱. کپی داده‌های خام برای AI — در ChatGPT/Gemini/Claude تحلیل کن.",
      "۲. کلید DeepSeek خودت را در پنل وارد کن.",
      "⚠️ AI فقط مشاور است، نه تصمیم نهایی.",
    ],
  },
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "اسکنر فرصت‌ها",
    content: [
      "نمادهای پرحجم هر صرافی را اسکن می‌کند.",
      "فیلتر: سیگنال قطعی (نه ضعیف) با اطمینان ≥ ۵۰٪.",
      "روی هر نماد بزن تا تحلیل کامل آن را ببینی.",
      "دکمه راستی‌آزمایی → ثبت دستی سیگنال.",
      "فیلترهای همه/ویژه/LONG/SHORT.",
    ],
  },
  {
    icon: <Book className="h-4 w-4 text-emerald-400" />,
    title: "راستی‌آزمایی خودکار",
    content: [
      "سیگنال‌های فعال به صورت خودکار ثبت می‌شوند.",
      "نمادهای ثابت: بیت‌کوین، تتر گلد، پکس گلد، سولانا، ریپل، دوج‌کوین، اتریوم و جفت‌های تومانی آن‌ها.",
      "نمادهای واچ‌لیست نیز در صورت انتخاب، تحلیل و ثبت می‌شوند.",
      "⏰ راستی‌آزمایی خودکار هر ۱۵ دقیقه اجرا می‌شود.",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-pink-400" />,
    title: "شاخص ترس و طمع",
    content: [
      "۰-۲۵: ترس شدید (احتمال کف).",
      "۲۵-۴۵: ترس.",
      "۴۵-۵۵: خنثی.",
      "۵۵-۷۵: طمع.",
      "۷۵-۱۰۰: طمع شدید (احتمال سقف).",
    ],
  },
];

// ═══════════════════════════════════════════════════════════
// 🔴 محتوای خام (برای BottomNav موبایل)
// ═══════════════════════════════════════════════════════════
export function HelpContent() {
  return (
    <div className="space-y-4">
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
          Trademun · دستیار هوشمند معامله‌گر
        </p>
        <p className="mt-1 text-[9px] text-muted-foreground/70">
          ⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارند — تصمیم نهایی با خودت است.
        </p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// HelpPanel — برای دسکتاپ (Sheet کنار صفحه)
// ═══════════════════════════════════════════════════════════
export function HelpPanel() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger className="num inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/10 md:h-9 md:px-3 md:text-[13px]">
        <HelpCircle className="h-3 w-3 text-orange-500 md:h-3.5 md:w-3.5" />
        <span>راهنما</span>
      </SheetTrigger>
      <SheetContent side="left" className="w-full max-w-md overflow-y-auto sm:w-96">
        <div className="mt-6">
          <HelpContent />
        </div>
      </SheetContent>
    </Sheet>
  );
}