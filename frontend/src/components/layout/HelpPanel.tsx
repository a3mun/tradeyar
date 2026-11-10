"use client";

import { useState } from "react";
import {
  HelpCircle,
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
  Globe,
  ChevronDown,
  BookOpen,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

// ═══════════════════════════════════════════════════════════
// 🔴 ساختار جدید بخش‌ها (۱۸ بخش · فاز ۱۴.۹.۸)
// ترتیب: از شروع سریع تا پیشرفته
// زبان: ساده و کاربرپسند — بدون لو دادن فرمول‌ها
// ═══════════════════════════════════════════════════════════
const SECTIONS = [
  // ═══ ۱. شروع سریع ═══
  {
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    title: "🚀 شروع سریع (در ۳۰ ثانیه)",
    content: [
      "نماد مورد نظرت رو از نوار جستجو یا دکمه‌های محبوب انتخاب کن.",
      "از پنل تنظیمات (سمت راست)، صرافی، تایم‌فریم، استراتژی و پروفایل ریسک رو انتخاب کن.",
      "بلافاصله کارت تحلیل (وسط) و جدول تایم‌فریم‌ها (چپ) آپدیت می‌شن.",
      "اگر نمادی رو دوست داری، روی ستاره (⭐) بزن تا به واچ‌لیست اضافه بشه.",
    ],
  },

  // ═══ ۲. ۳ استراتژی ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "🎯 سه استراتژی — کدوم رو انتخاب کنم؟",
    content: [
      "⚡ اسکالپ: برای معاملات سریع و نوسان‌گیری لحظه‌ای. ورود و خروج در چند دقیقه. مناسب کسانی که می‌خوان سریع سود بگیرن.",
      "🌊 سوئینگ: برای معاملات میان‌مدت — چند ساعت تا چند روز. تعادل خوبی بین سرعت و اطمینان داره.",
      "🏛 پوزیشن: برای سرمایه‌گذاری بلندمدت — چند روز تا چند هفته. سیگنال‌های با اطمینان بالا، ولی کمتر.",
      "💡 هر استراتژی تنظیمات خودش رو داره — تایم‌فریم مناسب، سطح اطمینان، و حد سود/ضرر.",
      "📌 اگه تازه‌کاری، از سوئینگ شروع کن. حرفه‌ای شدی، اسکالپ و پوزیشن رو هم امتحان کن.",
    ],
  },

  // ═══ ۳. سطوح اطمینان ═══
  {
    icon: <Target className="h-4 w-4 text-orange-400" />,
    title: "🎯 سطوح اطمینان — چطور بخونم؟",
    content: [
      "⚪ خنثی: بازار خوابه یا سیگنال واضحی نیست. بهترین کار: صبر کن.",
      "⚪ دور: هنوز فاصله داریم تا نقطه ورود مناسب. عجله نکن.",
      "🟡 در حال تشکیل: شرایط داره مساعد می‌شه، ولی هنوز کامل نشده. چند دقیقه دیگه چک کن.",
      "🟠 ضعیف: سیگنال هست، ولی ریسکش بیشتره. با حجم کم و احتیاط وارد شو.",
      "🟢 معمولی: سیگنال قابل قبول — معمولاً بهترین نقطه ورود.",
      "✅ قوی: اطمینان بالا. شرایط بازار کاملاً مساعده.",
      "💎 طلایی: نادر! بهترین فرصت. با اطمینان بالا وارد شو.",
      "💡 هر استراتژی، آستانه‌ی اطمینان خودش رو داره — اسکالپ راحت‌گیرتر، پوزیشن سخت‌گیرتر.",
    ],
  },

  // ═══ ۴. صرافی‌ها ═══
  {
    icon: <BarChart3 className="h-4 w-4 text-blue-400" />,
    title: "🏦 صرافی‌ها — کدوم تحلیل داره؟",
    content: [
      "🟣 نوبیتکس: تحلیل کامل — همه ۶ تایم‌فریم. پیشنهاد اصلی ما.",
      "🟢 بیت‌پین: تحلیل کامل — همه ۶ تایم‌فریم.",
      "🔵 والکس: تحلیل محدود — فقط «۱ ساعت» و «روزانه». بقیه تایم‌فریم‌ها خودکار از نوبیتکس گرفته می‌شن.",
      "🟠 تبدیل (Tabdeal): ❌ تحلیل نداره — فقط قیمت و عمق بازار. برای معامله سریع خوبه، برای تحلیل نه.",
      "🇮🇷 بورس تهران: فقط تایم‌فریم «روزانه»، بازار اسپات.",
      "💡 اگر صرافی تحلیل نداشت، کارت سیگنال پیام «تحلیل در دسترس نیست» می‌ده — صرافی دیگه‌ای انتخاب کن.",
    ],
  },

  // ═══ ۵. بخش‌های کشویی ═══
  {
    icon: <BookOpen className="h-4 w-4 text-blue-400" />,
    title: "📂 بخش‌های کشویی — چرا بسته‌ن؟",
    content: [
      "برای اینکه صفحه سریع لود بشه، بخش‌های سنگین به صورت کشویی هستن.",
      "📊 «آمار عملکرد» — نرخ برد، R:R خالص، نرخ رسیدن به هدف.",
      "✅ «چک‌لیست شرایط» — بررسی نهایی ۳۲ اندیکاتور در ۵ گروه.",
      "💬 «تحلیل و چرایی» — توضیح مفصل سیگنال + سناریوهای پیش‌رو.",
      "🧠 «مشاور هوشمند» — تحلیل با هوش مصنوعی (دو روش).",
      "💡 روی هر کارت کلیک کن تا باز بشه. هر بار فقط بخشی که باز می‌کنی، داده‌ها رو fetch می‌کنه.",
    ],
  },

  // ═══ ۶. موتور تحلیل ═══
  {
    icon: <Brain className="h-4 w-4 text-blue-400" />,
    title: "🧠 موتور تحلیل — ۵ گروه، ۳۲ اندیکاتور",
    content: [
      "🎯 هر گروه یک رأی می‌ده (صعودی، نزولی، خنثی) — سیستم بر اساس ترکیب هوشمند، تصمیم نهایی می‌گیره.",
      "✅ ما با بیش از ۳۳۵ تست خودکار، پایداری و دقت سیستم رو تضمین کردیم.",
    ],
    indicatorGroups: [
      {
        name: "مومنتوم",
        icon: "⚡",
        color: "purple",
        indicators: ["RSI", "Stochastic", "Williams %R", "CCI", "ROC"],
      },
      {
        name: "روند",
        icon: "📈",
        color: "blue",
        indicators: [
          "EMA 20",
          "EMA 50",
          "EMA 200",
          "EMA Slope",
          "MACD",
          "ADX",
          "Supertrend",
          "Ichimoku",
        ],
      },
      {
        name: "نوسان",
        icon: "📊",
        color: "amber",
        indicators: [
          "Bollinger",
          "BB Width",
          "ATR",
          "Keltner",
          "Donchian",
          "StdDev",
        ],
      },
      {
        name: "حجم",
        icon: "💧",
        color: "cyan",
        indicators: [
          "OBV",
          "CVD",
          "Delta",
          "CMF",
          "MFI",
          "Absorption",
          "Volume Ratio",
          "VWAP",
        ],
      },
      {
        name: "ساختار",
        icon: "🏗",
        color: "emerald",
        indicators: [
          "Pivot Points",
          "Swing High/Low",
          "Fibonacci",
          "Nearest S/R",
          "Strongest S/R",
        ],
      },
    ],
  },

  // ═══ ۷. مشاور هوشمند ═══
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "🧠 مشاور هوشمند — دو روش",
    content: [
      "روش ۱ (سریع و آسان): کلید رایگان OpenRouter رو بگیر (روزی ۵۰ درخواست رایگان). دکمه «تحلیل با هوش مصنوعی» رو بزن — تحلیل آماده‌ست.",
      "روش ۲ (جایگزین): دکمه «کپی داده‌های خام» رو بزن، بعد توی DeepSeek یا ChatGPT پیست کن.",
      "✅ DeepSeek و ChatGPT: بدون VPN کار می‌کنن — پیشنهاد ما برای کاربران ایران.",
      "⚠️ Gemini, Claude, Groq: نیاز به VPN دارن.",
      "📋 داده‌های خام شامل: قیمت‌های OHLCV، اندیکاتورها، سطوح کلیدی، عمق بازار — همه چیز برای تحلیل حرفه‌ای.",
      "💡 اگر API خطا داد (تحریم، محدودیت)، روش ۲ همیشه کار می‌کنه.",
    ],
  },

  // ═══ ۸. مدیریت ریسک ═══
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "🛡️ مدیریت ریسک — مهم‌ترین بخش",
    content: [
      "هر سیگنال دارای حد ضرر (SL) و حد سود (TP) مشخص است.",
      "R:R یعنی نسبت سود به ضرر — R:R=۲ یعنی در برابر ۱ واحد ریسک، ۲ واحد سود.",
      "⚠️ R:R خالص (بعد از کارمزد) مهم‌ترین معیار تصمیم‌گیریه.",
      "💡 پروفایل جسورانه: ۲-۳٪ سرمایه · محتاطانه: ۱-۲٪ سرمایه.",
      "❌ هیچ‌وقت بدون حد ضرر وارد معامله نشو.",
      "❌ هیچ‌وقت کل سرمایه‌ت رو در یک معامله نذار.",
    ],
  },

  // ═══ ۹. کارمزد ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "💸 کارمزد — چطور سودم رو کم می‌کنه؟",
    content: [
      "کارمزد رفت‌وبرگشتی صرافی‌های ایران بین ۰.۲ تا ۰.۶ درصد است.",
      "جفت‌های USDT: کارمزد کمتر (حدود ۰.۲۳٪).",
      "جفت‌های تومانی: کارمزد بیشتر (حدود ۰.۵۰٪).",
      "⚠️ در تایم‌فریم‌های کوتاه (۱ تا ۵ دقیقه)، کارمزد می‌تونه کل سود رو ببلعه.",
      "💡 برای دیدن جزئیات، روی خط هزینه در کارت سیگنال کلیک کن.",
    ],
  },

  // ═══ ۱۰. روند قوی ═══
  {
    icon: <AlertTriangle className="h-4 w-4 text-orange-400" />,
    title: "🚨 روند قوی — چطور مدیریت می‌شه؟",
    content: [
      "🔴 سوئینگ/پوزیشن: اگر روند قوی صعودی باشه → سیگنال فروش (SHORT) بلاک می‌شه.",
      "🔴 سوئینگ/پوزیشن: اگر روند قوی نزولی باشه → سیگنال خرید (LONG) بلاک می‌شه.",
      "🟡 اسکالپ: سیگنال خلاف روند بلاک نمی‌شه، ولی هشدار می‌بینی — با احتیاط بیشتر.",
      "💡 چرا؟ چون اسکالپ برای نوسان‌گیری لحظه‌ایه و در هر جهتی ممکنه سود بده.",
      "⚠️ همیشه هشدار رو جدی بگیر — روند قوی، دشمن معامله‌ی خلاف جهته.",
    ],
  },

  // ═══ ۱۱. عمق بازار ═══
  {
    icon: <Layers className="h-4 w-4 text-orange-400" />,
    title: "📊 عمق بازار — چطور بخونم؟",
    content: [
      "imbalance = نسبت حجم خرید به فروش. بالای ۰.۵۵ = فشار خرید · زیر ۰.۴۵ = فشار فروش.",
      "اسپرد کم = نقدینگی خوب · اسپرد زیاد = ریسک اسلیپیج (لغزش قیمت).",
      "🧱 دیوار سفارش = سطح با حجم غیرعادی (نشانه حضور نهنگ یا سفارش بزرگ).",
      "⚠️ عمق بازار لحظه‌ای است و بین صرافی‌ها تفاوت داره.",
      "💡 اگر imbalance با سیگنال هم‌جهت باشه، اطمینان بیشتر می‌شه.",
    ],
  },

  // ═══ ۱۲. تله‌ها ═══
  {
    icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
    title: "🚨 هشدار تله‌ها — چرا مهمه؟",
    content: [
      "🚨 تله صعودی: مومنتوم صعودی، ولی جریان پول خروجی — یعنی احتمالاً قیمت برمی‌گرده پایین.",
      "🚨 تله نزولی: مومنتوم نزولی، ولی جریان پول ورودی — یعنی احتمالاً قیمت برمی‌گرده بالا.",
      "⚠️ شکست جعلی: ADX قوی، ولی حجم کم — یعنی احتمالاً شکست واقعی نیست.",
      "😮‍💨 خستگی روند: ADX قوی، ولی مومنتوم ضعیف — یعنی روند داره خسته می‌شه.",
      "💡 وقتی تله فعال باشه، سیگنال ریسک‌دار می‌شه — با احتیاط وارد شو یا صبر کن.",
    ],
  },

  // ═══ ۱۳. فیلترها ═══
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "⏰ فیلترهای هوشمند — چرا سیگنال نمیاد؟",
    content: [
      "فیلتر سشن: در ساعات کم‌نقدینگی (مثل بامداد)، اطمینان کاهش پیدا می‌کنه.",
      "فیلتر آخر هفته: در روزهای تعطیل، سیگنال‌ها سخت‌گیرانه‌تر صادر می‌شن.",
      "فیلتر نوسان: اگر نوسان بازار خیلی کم باشه، سیگنال صادر نمی‌شه (چون به هدف نمی‌رسه).",
      "💡 هدف این فیلترها: فقط در بهترین شرایط بازار سیگنال بگیری — کیفیت بالاتر از کمیت.",
    ],
  },

  // ═══ ۱۴. اسکنر ═══
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "🔎 اسکنر فرصت‌ها — چطور کار می‌کنه؟",
    content: [
      "اسکنر به صورت خودکار نمادهای پرحجم هر صرافی رو بررسی می‌کنه.",
      "فیلترها: سیگنال قطعی (نه ضعیف) با اطمینان بالا.",
      "روی هر نماد بزن تا تحلیل کاملش رو ببینی.",
      "فیلترهای همه/ویژه/LONG/SHORT — برای پیدا کردن سریع‌تر.",
      "💡 اگر نماد جدیدی می‌خوای، از اسکنر پیدا کن و مستقیم به تحلیل برو.",
    ],
  },

  // ═══ ۱۵. راستی‌آزمایی ═══
  {
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
    title: "✅ راستی‌آزمایی — چطور مطمئن بشم؟",
    content: [
      "همه سیگنال‌ها به صورت خودکار در دیتابیس ثبت می‌شن.",
      "ربات‌ها به صورت مستمر عملکرد سیگنال‌ها رو ارزیابی می‌کنن.",
      "📊 آمار عملکرد: نرخ برد، نرخ رسیدن به هدف، R:R خالص.",
      "⏰ سیستم هر ۳ دقیقه یه بار وضعیت سیگنال‌ها رو چک می‌کنه.",
      "💡 آمار کامل و تاریخچه در پنل مدیر (برای ادمین) قابل مشاهده است.",
    ],
  },

  // ═══ ۱۶. Fear & Greed ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-pink-400" />,
    title: "😱 شاخص ترس و طمع — چرا مهمه؟",
    content: [
      "۰-۲۵: ترس شدید — معمولاً بهترین زمان خرید (کف بازار).",
      "۲۵-۴۵: ترس — بازار محتاطه.",
      "۴۵-۵۵: خنثی — بازار در تعادله.",
      "۵۵-۷۵: طمع — بازار هیجانی شده.",
      "۷۵-۱۰۰: طمع شدید — معمولاً زمان فروش (سقف بازار).",
      "💡 از این شاخص به عنوان «فیلتر دوم» استفاده کن — نه تنها معیار.",
    ],
  },

  // ═══ ۱۷. بورس ایران ═══
  {
    icon: <BarChart3 className="h-4 w-4 text-emerald-400" />,
    title: "🇮🇷 بورس تهران — چطور تحلیل کنم؟",
    content: [
      "نمادهای بورس (مثل فولاد، شپنا، آگاس) رو با جستجو پیدا کن.",
      "بورس ایران فقط تایم‌فریم «روزانه» داره و بازارش اسپات هست.",
      "سیستم به صورت خودکار تنظیمات رو برات درست می‌کنه.",
      "اگر دوباره یک نماد کریپتو انتخاب کنی، تنظیمات به حالت قبل برمی‌گرده.",
    ],
  },

  // ═══ ۱۸. افزونه ═══
  {
    icon: <Globe className="h-4 w-4 text-gold-400" />,
    title: "🔌 افزونه کروم — چیه؟",
    content: [
      "افزونه مخصوص صرافی‌های دریا گلد و آلفا گلد است و به تحلیل زنده XAU/USD می‌پردازد.",
      "برای نصب، از داشبورد کاربری دکمه «دانلود افزونه» را بزنید و راهنمای نصب را دنبال کنید.",
      "بعد از نصب، باید افزونه را به حساب تریدمون خود متصل کنید (دکمه «اتصال به حساب» در پاپ‌آپ).",
    ],
  },
];

// ═══════════════════════════════════════════════════════════
// محتوای خام (برای BottomNav موبایل)
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
          <HelpSection key={idx} section={section} defaultOpen={idx === 0} />
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
// HelpSection — بخش کشویی
// ═══════════════════════════════════════════════════════════
function HelpSection({
  section,
  defaultOpen = false,
}: {
  section: {
    icon: React.ReactNode;
    title: string;
    content: string[];
    indicatorGroups?: Array<{
      name: string;
      icon: string;
      color: string;
      indicators: string[];
    }>;
  };
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  // 🎨 رنگ‌بندی بج‌ها بر اساس رنگ گروه
  const colorMap: Record<string, { bg: string; text: string; border: string }> = {
    purple: {
      bg: "bg-purple-500/10",
      text: "text-purple-300",
      border: "border-purple-500/30",
    },
    blue: {
      bg: "bg-blue-500/10",
      text: "text-blue-300",
      border: "border-blue-500/30",
    },
    amber: {
      bg: "bg-amber-500/10",
      text: "text-amber-300",
      border: "border-amber-500/30",
    },
    cyan: {
      bg: "bg-cyan-500/10",
      text: "text-cyan-300",
      border: "border-cyan-500/30",
    },
    emerald: {
      bg: "bg-emerald-500/10",
      text: "text-emerald-300",
      border: "border-emerald-500/30",
    },
  };

  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 p-3 text-right transition-colors hover:bg-muted/20"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {section.icon}
          <h3 className="text-xs font-bold truncate">{section.title}</h3>
        </div>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2.5">
          {/* 🔴 گروه‌های اندیکاتور با بج */}
          {section.indicatorGroups?.map((group) => {
            const colors = colorMap[group.color] || colorMap.blue;
            return (
              <div key={group.name} className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px]">{group.icon}</span>
                  <span className="text-[10.5px] font-bold text-foreground/80">
                    {group.name}
                  </span>
                  <span className="num text-[8.5px] text-muted-foreground/60">
                    ({group.indicators.length})
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {group.indicators.map((ind) => (
                    <span
                      key={ind}
                      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[9px] font-medium ${colors.bg} ${colors.text} ${colors.border}`}
                    >
                      {ind}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}

          {/* متن‌های عادی */}
          {section.content.length > 0 && (
            <ul className="space-y-1 pt-1 text-[10.5px] text-muted-foreground list-disc pr-4">
              {section.content.map((item, i) => (
                <li key={i} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
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
      <SheetContent
        side="left"
        className="w-full max-w-md overflow-y-auto sm:w-96"
      >
        <div className="mt-6">
          <HelpContent />
        </div>
      </SheetContent>
    </Sheet>
  );
}