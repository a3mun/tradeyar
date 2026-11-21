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
  Search,
  Coins,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

// ═══════════════════════════════════════════════════════════
// 🔴 ساختار جدید بخش‌ها (۱۸ بخش · فاز ۱۶.۶)
// ═══════════════════════════════════════════════════════════
const SECTIONS = [
  // ═══ ۱. شروع سریع ═══
  {
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    title: "🚀 شروع سریع (در ۳۰ ثانیه)",
    content: [
      "نماد مورد نظرت رو از نوار جستجو (کریپتو، بورس، یا فارکس) یا دکمه‌های محبوب انتخاب کن.",
      "از پنل تنظیمات (سمت راست)، صرافی، تایم‌فریم، استراتژی و پروفایل ریسک رو انتخاب کن.",
      "بلافاصله کارت تحلیل (وسط) و جدول تایم‌فریم‌ها (چپ) آپدیت می‌شن.",
      "اگر نمادی رو دوست داری، روی ستاره (⭐) بزن تا به واچ‌لیست اضافه بشه.",
    ],
  },


  // ═══ ۳. بازارها ═══
  {
    icon: <Coins className="h-4 w-4 text-yellow-400" />,
    title: "🌍 بازارها — کدوم تحلیل داره؟",
    content: [
      "🪙 کریپتو (نوبیتکس، بیت‌پین، والکس): تحلیل کامل — همه ۶ تایم‌فریم.",
      "📈 فارکس و کالا (Biquote): تحلیل کامل — طلا، نقره، نفت، شاخص‌ها، جفت‌ارزها.",
      "🇮🇷 بورس تهران (TSETMC): فقط تایم‌فریم «روزانه»، بازار اسپات.",
      "🟠 تبدیل (Tabdeal): ❌ کندل و تحلیل نداره — فقط قیمت و عمق بازار. برای معامله سریع خوبه.",
      " صرافی تبدیل در حال حاضر فقط قیمت لحظه ای ارائه می دهد.",
    ],
  },

  // ═══ ۴. ۳ استراتژی ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "🎯 سه استراتژی — کدوم رو انتخاب کنم؟",
    content: [
      "⚡ اسکالپ: برای معاملات سریع و نوسان‌گیری لحظه‌ای. ورود و خروج در چند دقیقه.",
      "🌊 سوئینگ: برای معاملات میان‌مدت — چند ساعت تا چند روز. تعادل خوبی بین سرعت و اطمینان داره.",
      "🏛 پوزیشن: برای سرمایه‌گذاری بلندمدت — چند روز تا چند هفته. سیگنال‌های با اطمینان بالا، ولی کمتر.",
      "💡 هر استراتژی تنظیمات خودش رو داره — تایم‌فریم مناسب، سطح اطمینان، و حد سود/ضرر.",
      "📌 اگه تازه‌کاری، از سوئینگ شروع کن.",
    ],
  },

  // ═══ ۵. سطوح اطمینان ═══
  {
    icon: <Target className="h-4 w-4 text-orange-400" />,
    title: "🎯 سطوح اطمینان — چطور بخونم؟",
    content: [
      "⚪ خنثی: بازار خوابه یا سیگنال واضحی نیست. بهترین کار: صبر کن.",
      "⚪ دور: هنوز فاصله داریم تا نقطه ورود مناسب. عجله نکن.",
      "🟡 در حال تشکیل: شرایط داره مساعد می‌شه، ولی هنوز کامل نشده.",
      "🟠 ضعیف: سیگنال هست، ولی ریسکش بیشتره. با حجم کم و احتیاط وارد شو.",
      "🟢 معمولی: سیگنال قابل قبول — معمولاً بهترین نقطه ورود.",
      "✅ قوی: اطمینان بالا. شرایط بازار کاملاً مساعده.",
      "💎 طلایی: نادر! بهترین فرصت. با اطمینان بالا وارد شو.",
    ],
  },

  // ═══ ۶. بخش‌های کشویی ═══
  {
    icon: <BookOpen className="h-4 w-4 text-blue-400" />,
    title: "📂 بخش‌های کشویی — چرا بسته‌ن؟",
    content: [
      "برای اینکه صفحه سریع لود بشه، بخش‌های سنگین به صورت کشویی هستن.",
      "📊 «آمار عملکرد» — نرخ برد، R:R خالص، نرخ رسیدن به هدف.",
      "✅ «چک‌لیست شرایط» — بررسی نهایی ۳۲ اندیکاتور در ۵ گروه.",
      "💬 «تحلیل تکنیکال» — توضیح مفصل سیگنال + سناریوهای پیش‌رو.",
      "🏛 «تحلیل بنیادین» — به زودی (در حال توسعه).",
      "🧠 «مشاور هوشمند» — تحلیل با هوش مصنوعی (دو روش).",
      "💡 روی هر کارت کلیک کن تا باز بشه.",
    ],
  },

  // ═══ ۷. موتور تحلیل ═══
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
          "EMA 20", "EMA 50", "EMA 200", "EMA Slope",
          "MACD", "ADX", "Supertrend", "Ichimoku",
        ],
      },
      {
        name: "نوسان",
        icon: "📊",
        color: "amber",
        indicators: ["Bollinger", "BB Width", "ATR", "Keltner", "Donchian", "StdDev"],
      },
      {
        name: "حجم",
        icon: "💧",
        color: "cyan",
        indicators: [
          "OBV", "CVD", "Delta", "CMF", "MFI",
          "Absorption", "Volume Ratio", "VWAP",
        ],
      },
      {
        name: "ساختار",
        icon: "🏗",
        color: "emerald",
        indicators: ["Pivot Points", "Swing High/Low", "Fibonacci", "Nearest S/R", "Strongest S/R"],
      },
    ],
  },

  // ═══ ۸. مشاور هوشمند ═══
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "🧠 مشاور هوشمند — دو روش",
    content: [
      "روش ۱ (سریع و آسان): با کمک هوش مصنوعی های متصل به Cloudflare AI روزانه چندین درخواست می‌تونید ثبت کنید. دکمه «دریافت تحلیل هوشمند» رو بزن.",
      "روش ۲ (جایگزین): دکمه «کپی داده‌های خام» رو بزن، بعد توی DeepSeek یا ChatGPT پیست کن.",
      "✅ DeepSeek و ChatGPT: بدون VPN کار می‌کنن — پیشنهاد ما برای کاربران ایران.",
      "⚠️ Gemini, Claude, Groq: گاهی نیاز به VPN دارن.",
    ],
  },

  // ═══ ۹. مدیریت ریسک ═══
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "🛡️ مدیریت ریسک — مهم‌ترین بخش",
    content: [
      "هر سیگنال دارای حد ضرر (SL) و حد سود (TP) مشخص است.",
      "R:R یعنی نسبت سود به ضرر — R:R=۲ یعنی در برابر ۱ واحد ریسک، ۲ واحد سود.",
      "⚠️ R:R خالص (بعد از کارمزد) مهم‌ترین معیار تصمیم‌گیریه.",
      "💡 پروفایل جسورانه: ۲-۳٪ سرمایه · محتاطانه: ۱-۲٪ سرمایه.",
      "❌ هیچ‌وقت بدون حد ضرر وارد معامله نشو.",
    ],
  },

  // ═══ ۱۰. کارمزد ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-cyan-400" />,
    title: "💸 کارمزد — چطور سودم رو کم می‌کنه؟",
    content: [
      "کارمزد رفت‌وبرگشتی صرافی‌های ایران بین ۰.۲ تا ۰.۶ درصد است.",
      "جفت‌های USDT: کارمزد کمتر (حدود ۰.۲۳٪).",
      "جفت‌های تومانی: کارمزد بیشتر (حدود ۰.۵۰٪).",
      "⚠️ در تایم‌فریم‌های کوتاه، کارمزد می‌تونه کل سود رو ببلعه.",
    ],
  },

  // ═══ ۱۱. روند قوی ═══
  {
    icon: <AlertTriangle className="h-4 w-4 text-orange-400" />,
    title: "🚨 روند قوی — چطور مدیریت می‌شه؟",
    content: [
      "🔴 سوئینگ/پوزیشن: اگر روند قوی صعودی باشه → سیگنال فروش (SHORT) بلاک می‌شه.",
      "🔴 سوئینگ/پوزیشن: اگر روند قوی نزولی باشه → سیگنال خرید (LONG) بلاک می‌شه.",
      "🟡 اسکالپ: سیگنال خلاف روند بلاک نمی‌شه، ولی هشدار می‌بینی.",
    ],
  },

  // ═══ ۱۲. عمق بازار ═══
  {
    icon: <Layers className="h-4 w-4 text-orange-400" />,
    title: "📊 عمق بازار — چطور بخونم؟",
    content: [
      "imbalance = نسبت حجم خرید به فروش. بالای ۰.۵۵ = فشار خرید · زیر ۰.۴۵ = فشار فروش.",
      "اسپرد کم = نقدینگی خوب · اسپرد زیاد = ریسک اسلیپیج.",
      "🧱 دیوار سفارش = سطح با حجم غیرعادی (نشانه حضور نهنگ).",
    ],
  },

  // ═══ ۱۳. تله‌ها ═══
  {
    icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
    title: "🚨 هشدار تله‌ها — چرا مهمه؟",
    content: [
      "🚨 تله صعودی: مومنتوم صعودی، ولی جریان پول خروجی.",
      "🚨 تله نزولی: مومنتوم نزولی، ولی جریان پول ورودی.",
      "⚠️ شکست جعلی: ADX قوی، ولی حجم کم.",
      "😮‍💨 خستگی روند: ADX قوی، ولی مومنتوم ضعیف.",
    ],
  },

  // ═══ ۱۴. فیلترها ═══
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "⏰ فیلترهای هوشمند — چرا سیگنال نمیاد؟",
    content: [
      "فیلتر سشن: در ساعات کم‌نقدینگی، اطمینان کاهش پیدا می‌کنه.",
      "فیلتر آخر هفته: در روزهای تعطیل، سیگنال‌ها سخت‌گیرانه‌تر صادر می‌شن.",
      "فیلتر نوسان: اگر نوسان بازار خیلی کم باشه، سیگنال صادر نمی‌شه.",
    ],
  },

  // ═══ ۱۵. اسکنر ═══
  {
    icon: <Filter className="h-4 w-4 text-purple-400" />,
    title: "🔎 اسکنر فرصت‌ها — چطور کار می‌کنه؟",
    content: [
      "اسکنر به صورت خودکار نمادهای پرحجم هر صرافی رو بررسی می‌کنه.",
      "فیلترها: سیگنال قطعی (نه ضعیف) با اطمینان بالا.",
      "فیلترهای همه/ویژه/LONG/SHORT — برای پیدا کردن سریع‌تر.",
    ],
  },

  // ═══ ۱۶. راستی‌آزمایی ═══
  {
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
    title: "✅ راستی‌آزمایی — چطور مطمئن بشم؟",
    content: [
      "همه سیگنال‌ها به صورت خودکار در دیتابیس ثبت می‌شن.",
      "ربات‌ها به صورت مستمر عملکرد سیگنال‌ها رو ارزیابی می‌کنن.",
      "📊 آمار عملکرد: نرخ برد، نرخ رسیدن به هدف، R:R خالص.",
      "⏰ سیستم هر ۳ دقیقه یه بار وضعیت سیگنال‌ها رو چک می‌کنه.",
    ],
  },

  // ═══ ۱۷. Fear & Greed ═══
  {
    icon: <TrendingUp className="h-4 w-4 text-pink-400" />,
    title: "😱 شاخص ترس و طمع — چرا مهمه؟",
    content: [
      "۰-۲۵: ترس شدید — معمولاً بهترین زمان خرید.",
      "۲۵-۴۵: ترس — بازار محتاطه.",
      "۴۵-۵۵: خنثی — بازار در تعادله.",
      "۵۵-۷۵: طمع — بازار هیجانی شده.",
      "۷۵-۱۰۰: طمع شدید — معمولاً زمان فروش.",
      "💡 از این شاخص به عنوان «فیلتر دوم» استفاده کن.",
    ],
  },

  // ═══ ۱۸. بورس ایران ═══
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

  // ═══ ۱۹. افزونه ═══
  {
    icon: <Globe className="h-4 w-4 text-gold-400" />,
    title: "🔌 افزونه کروم — چیه؟",
    content: [
      "افزونه مخصوص صرافی‌های دریا گلد و آلفا گلد است و به تحلیل زنده XAU/USD می‌پردازد.",
      "برای نصب، از داشبورد کاربری دکمه «دانلود افزونه» را بزنید.",
      "بعد از نصب، باید افزونه را به حساب تریدمون خود متصل کنید.",
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
          تریدمون | معامله هوشمند از اینجا شروع میشه!
        </p>
        <p className="mt-1 text-[9px] text-muted-foreground/70">
         ⚠️ تریدمون صرفاً ابزار تحلیل داده و ارائه سیگنال‌های کمکی است. تحلیل‌ها بر پایه الگوریتم‌ها و داده‌های تاریخی انجام می‌شوند و تضمینی برای سودآوری ندارند. مسئولیت تصمیم‌گیری و نتایج معاملات بر عهده کاربر است.

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

  const colorMap: Record<string, { bg: string; text: string; border: string }> = {
    purple: { bg: "bg-purple-500/10", text: "text-purple-300", border: "border-purple-500/30" },
    blue: { bg: "bg-blue-500/10", text: "text-blue-300", border: "border-blue-500/30" },
    amber: { bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/30" },
    cyan: { bg: "bg-cyan-500/10", text: "text-cyan-300", border: "border-cyan-500/30" },
    emerald: { bg: "bg-emerald-500/10", text: "text-emerald-300", border: "border-emerald-500/30" },
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
          {/* 🔴 گروه‌های اندیکاتور */}
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
      <SheetTrigger className="flex items-center justify-center gap-1.5 h-9 rounded-xl border border-white/5 bg-white/5 text-[11px] font-medium text-gray-300 transition-all duration-200 hover:bg-white/10 hover:border-white/10 hover:text-white px-3">
        <HelpCircle className="h-3.5 w-3.5 text-[#d6ad60]/80" />
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