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
  CheckCircle2,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

const SECTIONS = [
  {
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    title: "🚀 شروع سریع (در ۳۰ ثانیه)",
    content: [
      "نماد مورد نظرت رو از نوار جستجو یا دکمه‌های محبوب (بالای صفحه) انتخاب کن.",
      "از پنل سمت راست، صرافی، تایم‌فریم و پروفایل ریسکت رو تنظیم کن.",
      "بلافاصله کارت تحلیل (وسط صفحه) و جدول تایم‌فریم‌ها (چپ) آپدیت می‌شن.",
      "اگر نمادی رو دوست داری، روی ستاره (⭐) بزن تا به واچ‌لیست اضافه بشه.",
    ],
  },
  {
    icon: <Brain className="h-4 w-4 text-blue-400" />,
    title: "🇮🇷 تحلیل بورس ایران (TSETMC)",
    content: [
      "نمادهای بورس (مثل فولاد، شپنا، آگاس) رو با جستجو پیدا کن.",
      "بورس ایران فقط تایم‌فریم «روزانه» داره و بازارش اسپات هست.",
      "سیستم به صورت خودکار تنظیمات رو برات درست می‌کنه.",
      "اگر دوباره یک نماد کریپتو انتخاب کنی، تنظیمات به حالت قبل برمی‌گرده.",
    ],
  },
  {
    icon: <BarChart3 className="h-4 w-4 text-green-400" />,
    title: "🧠 موتور تحلیل ۵ گروهی",
    content: [
      "⚡ مومنتوم: RSI، Stochastic، Williams، CCI، ROC",
      "📈 روند: EMA200، MACD، ADX، Supertrend، Ichimoku",
      "📊 نوسان: Bollinger، ATR، Keltner، Donchian",
      "💧 حجم: OBV، CVD، Delta، CMF، MFI",
      "🏗 ساختار: Pivot، Swing، Fibonacci، S/R",
      "هر گروه یک رأی (صعودی، نزولی، خنثی) می‌دهد و سیستم بر اساس وزن‌دهی، تصمیم نهایی رو می‌گیره.",
    ],
  },
  {
    icon: <Target className="h-4 w-4 text-orange-400" />,
    title: "🎯 سطوح اطمینان (خیلی مهم)",
    content: [
      "۰ تا ۱۵٪: خنثی — بازار خوابه یا سیگنال واضحی نیست.",
      "۱۵ تا ۳۰٪: دور — هنوز فاصله داریم، عجله نکن.",
      "۳۰ تا ۴۰٪: در حال تشکیل — شرایط داره مساعد می‌شه.",
      "۴۰ تا ۵۵٪: سیگنال ضعیف — با احتیاط و حجم کم وارد شو.",
      "۵۵ تا ۷۰٪: سیگنال معمولی — قابل قبول.",
      "۷۰ تا ۸۵٪: سیگنال قوی — اطمینان بالا.",
      "بالای ۸۵٪: سیگنال طلایی 💎 — بهترین فرصت.",
    ],
  },
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "⏰ فیلترهای هوشمند (ساعت و نوسان)",
    content: [
      "فیلتر سشن: در ساعات کم‌نقدینگی (مثل بامداد)، اطمینان کاهش پیدا می‌کنه.",
      "فیلتر آخر هفته: در روزهای تعطیل، سیگنال‌ها سخت‌گیرانه‌تر صادر می‌شن.",
      "فیلتر ATR: اگر نوسان بازار خیلی کم باشه، سیگنال صادر نمی‌شه (چون به هدف نمی‌رسه).",
      "هدف این فیلترها اینه که فقط در بهترین شرایط بازار سیگنال بگیری.",
    ],
  },
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "🛡️ مدیریت ریسک و سرمایه",
    content: [
      "هر سیگنال دارای حد ضرر (SL) و حد سود (TP) مشخص است.",
      "نسبت R:R خام = ۲ یعنی در برابر ۱ واحد ریسک، ۲ واحد سود.",
      "⚠️ R:R خالص (بعد از کارمزد) مهم‌ترین معیار است.",
      "پروفایل جسورانه: ۲-۳٪ سرمایه · محتاطانه: ۱-۲٪ سرمایه.",
      "هیچ‌وقت بدون حد ضرر وارد معامله نشو.",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "💸 کارمزد و R:R خالص",
    content: [
      "کارمزد رفت‌وبرگشتی صرافی‌های ایران بین ۰.۲ تا ۰.۶ درصد است.",
      "کارمزد جفت‌های USDT حدود ۰.۲۳٪ و جفت‌های تومانی حدود ۰.۵۰٪ است.",
      "R:R خام ۲ ممکن است بعد از کارمزد به ۱.۷ یا کمتر برسد.",
      "⚠️ در تایم‌فریم‌های کوتاه (۱ تا ۵ دقیقه) کارمزد می‌تواند کل سود را ببلعد.",
      "برای دیدن جزئیات، روی خط هزینه در کارت سیگنال کلیک کن.",
    ],
  },
  {
    icon: <Target className="h-4 w-4 text-orange-400" />,
    title: "👑 اولویت روند بر سیگنال",
    content: [
      "اگر روند قوی صعودی باشد، سیستم اجازه نمی‌دهد سیگنال فروش (SHORT) صادر شود.",
      "اگر روند قوی نزولی باشد، سیستم اجازه نمی‌دهد سیگنال خرید (LONG) صادر شود.",
      "این تصمیم بر اساس داده‌های واقعی گرفته شده که ۱۰۰٪ بردها در جهت روند بوده‌اند.",
      "نتیجه: کیفیت سیگنال بالاتر و ضرر کمتر.",
    ],
  },
  {
    icon: <Layers className="h-4 w-4 text-orange-400" />,
    title: "📊 عمق بازار (Order Book)",
    content: [
      "imbalance = نسبت حجم خرید به فروش.",
      "بالای ۰.۵۵ = فشار خرید · زیر ۰.۴۵ = فشار فروش.",
      "اسپرد کم = نقدینگی خوب · اسپرد زیاد = ریسک اسلیپیج.",
      "🧱 دیوار سفارش = سطح با حجم غیرعادی (نشانه حضور نهنگ).",
      "⚠️ عمق بازار لحظه‌ای است و بین صرافی‌ها تفاوت دارد.",
    ],
  },
  {
    icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
    title: "🚨 هشدار تله‌ها (Trap Detection)",
    content: [
      "🚨 تله صعودی: مومنتوم صعودی ولی جریان پول خروجی.",
      "🚨 تله نزولی: مومنتوم نزولی ولی جریان پول ورودی.",
      "⚠️ شکست جعلی: ADX قوی ولی حجم کم.",
      "😮‍💨 خستگی روند: ADX قوی ولی مومنتوم ضعیف.",
      "وقتی تله فعال باشد، سیگنال ریسک‌دار می‌شود و باید با احتیاط وارد شوی.",
    ],
  },
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "🤖 تحلیل هوش مصنوعی (AI)",
    content: [
      "سیستم داده‌های خام بازار (مثل OHLCV، اندیکاتورها و سطوح) را آماده می‌کند.",
      "شما با یک کلیک، این داده‌ها را کپی می‌کنید و در ChatGPT، Gemini یا Claude تحلیل می‌کنید.",
      "این روش باعث می‌شود از زاویه دید یک هوش مصنوعی دیگر هم به بازار نگاه کنی.",
      "⚠️ هوش مصنوعی فقط مشاور است، تصمیم نهایی با خودت است.",
    ],
  },
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "🔎 اسکنر فرصت‌ها",
    content: [
      "اسکنر به صورت خودکار نمادهای پرحجم هر صرافی را بررسی می‌کند.",
      "فیلترها: سیگنال قطعی (نه ضعیف) با اطمینان ≥ ۴۰٪.",
      "روی هر نماد بزن تا تحلیل کامل آن را ببینی.",
      "دکمه راستی‌آزمایی → ثبت دستی سیگنال.",
      "فیلترهای همه/ویژه/LONG/SHORT.",
    ],
  },
  {
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
    title: "✅ راستی‌آزمایی سیگنال‌ها",
    content: [
      "همه سیگنال‌ها به صورت خودکار در دیتابیس ثبت می‌شوند.",
      "ربات‌ها و تیم کنترل کیفیت تریدمون، به صورت مستمر عملکرد سیگنال‌ها را ارزیابی می‌کنند.",
      "این ارزیابی به ما کمک می‌کند تا الگوریتم‌ها را بهتر کنیم و سیگنال‌های باکیفیت‌تری به شما ارائه دهیم.",
      "نمادهای ثابت: بیت‌کوین، تتر گلد، پکس گلد، سولانا، ریپل، دوج‌کوین، اتریوم و جفت‌های تومانی آن‌ها.",
      "⏰ سیستم به صورت خودکار هر ۳ دقیقه یک بار وضعیت سیگنال‌ها را بررسی می‌کند.",
    ],
  },
  {
    icon: <TrendingUp className="h-4 w-4 text-pink-400" />,
    title: "😱 شاخص ترس و طمع (Fear & Greed)",
    content: [
      "۰-۲۵: ترس شدید (احتمال کف بازار).",
      "۲۵-۴۵: ترس.",
      "۴۵-۵۵: خنثی.",
      "۵۵-۷۵: طمع.",
      "۷۵-۱۰۰: طمع شدید (احتمال سقف بازار).",
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
        <h2 className="text-lg font-bold">راهنمای تریدمون</h2>
        <p className="text-xs text-muted-foreground mt-1">
          هر آنچه برای استفاده حرفه‌ای نیاز داری
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