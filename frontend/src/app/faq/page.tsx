"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  HelpCircle,
  ArrowLeft,
  MessageCircleQuestion,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Button } from "@/components/ui/button";

const FAQ_CATEGORIES = [
  {
    id: "general",
    title: "عمومی",
    icon: "🚀",
    items: [
      {
        q: "تریدمون چیه؟",
        a: "تریدمون یک موتور تحلیل‌گر ریاضی است که با ترکیب ۳۲ اندیکاتور تکنیکال حرفه‌ای در ۵ گروه (مومنتوم، روند، نوسان، حجم، ساختار)، به معامله‌گران ایرانی کمک می‌کند تصمیم‌های بهتری بگیرند. ما از ۴ صرافی ایرانی (نوبیتکس، بیت‌پین، والکس، تبدیل) و ۳ استراتژی معاملاتی (اسکالپ، سوئینگ، پوزیشن) پشتیبانی می‌کنیم.",
      },
      {
        q: "چطور شروع کنم؟",
        a: "۳ روز رایگان — بدون نیاز به کارت بانکی. با شماره موبایل ثبت‌نام کن، بعد از فعال‌سازی، بلافاصله به همه بخش‌ها دسترسی داری. برای شروع: صفحه اصلی → انتخاب نماد → تنظیم استراتژی → دریافت سیگنال.",
      },
      {
        q: "پلن رایگان چقدره و چی داره؟",
        a: "پلن رایگان ۳ روزه است و شامل: مشاهده کارت سیگنال، جدول تایم‌فریم‌ها، عمق بازار، شاخص ترس و طمع، تحلیل تکنیکال پیشرفته، سناریوها، چک‌لیست، کپی داده خام، و کارت آمار راستی‌آزمایی. برای اسکنر، مشاور هوشمند AI، مقایسه صرافی‌ها و افزونه کروم، نیاز به اشتراک Pro داری.",
      },
    ],
  },
  {
    id: "strategies",
    title: "استراتژی‌ها",
    icon: "🎯",
    items: [
      {
        q: "تفاوت اسکالپ، سوئینگ و پوزیشن چیه؟",
        a: "⚡ اسکالپ: معاملات سریع ۱-۵ دقیقه (فقط فیوچرز). سیگنال‌های پویا، حتی در روند مخالف (با هشدار). مناسب نوسان‌گیری لحظه‌ای. 🌊 سوئینگ: میان‌مدت — همه ۶ تایم‌فریم. تعادل بین سرعت و اطمینان. 🏛 پوزیشن: بلندمدت — ۳۰ دقیقه، ۱ ساعت، روزانه. اطمینان بالا، سیگنال کمتر.",
      },
      {
        q: "تفاوت پروفایل جسورانه و محتاطانه چیه؟",
        a: "جسورانه: آستانه اطمینان پایین‌تر، سیگنال بیشتر، ریسک بیشتر، اهرم ۲-۳x. محتاطانه: آستانه اطمینان بالاتر، سیگنال کمتر، ریسک کمتر، اهرم ۱-۲x. محتاطانه + اسکالپ در UI بلاک شده — خودکار به سوئینگ تغییر می‌کند.",
      },
      {
        q: "چرا اسکالپ سیگنال بیشتری می‌ده؟",
        a: "اسکالپ برای نوسان‌گیری لحظه‌ای طراحی شده — آستانه اطمینان پایین‌تر (۳۰٪) و تعداد رأی کمتر (۱ رأی) کافیه. همچنین در روند مخالف بلاک نمی‌شه، فقط هشدار می‌ده. این یعنی سیگنال‌های بیشتر، ولی با ریسک بالاتر.",
      },
    ],
  },
  {
    id: "signals",
    title: "سیگنال‌ها",
    icon: "📊",
    items: [
      {
        q: "چرا سیگنال نمی‌بینم؟",
        a: "۴ دلیل احتمالی: ۱) بازار خوابه (ADX پایین، حجم کم) → عادی است. ۲) استراتژی/تایم‌فریم مناسبی انتخاب نکردی → راهنما رو ببین. ۳) صرافی انتخابی تحلیل نداره (مثل تبدیل) → نوبیتکس یا بیت‌پین انتخاب کن. ۴) در روند قوی، سیگنال مخالف بلاک می‌شه (در سوئینگ/پوزیشن) یا confidence کم می‌شه (در اسکالپ).",
      },
      {
        q: "سطوح اطمینان به چی معنیه؟",
        a: "⚪ خنثی: بازار خوابه. ⚪ دور: هنوز فاصله داریم. 🟡 در حال تشکیل: شرایط داره مساعد می‌شه. 🟠 ضعیف: با احتیاط. 🟢 معمولی: قابل قبول. ✅ قوی: اطمینان بالا. 💎 طلایی: نادر، بهترین فرصت. هر استراتژی، آستانه خودش رو داره.",
      },
      {
        q: "سیگنال طلایی چیه؟",
        a: "وقتی confidence ≥ ۸۵٪ باشه، سیگنال «طلایی» (💎) می‌شه. این نادرترین و باکیفیت‌ترین نوع سیگنال است — بهترین نقطه ورود. با اطمینان بالا وارد شو، ولی همیشه حد ضرر بذار.",
      },
      {
        q: "آمار راستی‌آزمایی چیه؟",
        a: "همه سیگنال‌ها به صورت خودکار در دیتابیس ثبت می‌شن و ربات‌ها به صورت مستمر عملکردشون رو ارزیابی می‌کنن (هر ۳ دقیقه). آمار (نرخ برد، R:R خالص، نرخ رسیدن به TP) در کارت «آمار عملکرد» قابل مشاهده است.",
      },
    ],
  },
  {
    id: "ai",
    title: "مشاور هوشمند AI",
    icon: "🧠",
    items: [
      {
        q: "مشاور هوشمند چطور کار می‌کنه؟",
        a: "دو روش: ۱) API رایگان — کلید OpenRouter بگیر (روزی ۵۰ درخواست رایگان)، دکمه «تحلیل با هوش مصنوعی» بزن. ۲) کپی داده خام — دکمه «کپی داده‌های خام» بزن، بعد توی DeepSeek یا ChatGPT پیست کن. داده‌های خام شامل OHLCV، اندیکاتورها، سطوح و عمق بازار است.",
      },
      {
        q: "کدوم پلتفرم AI بدون VPN کار می‌کنه؟",
        a: "✅ DeepSeek (chat.deepseek.com) و ChatGPT (chat.openai.com) — بدون VPN کار می‌کنن. ⚠️ Gemini, Claude, Groq — نیاز به VPN دارن.",
      },
      {
        q: "کلید OpenRouter چیه و چطور بگیرم؟",
        a: "OpenRouter یک سرویس رایگان AI است. کلید رایگان از openrouter.ai/keys بگیر — با ثبت‌نام، روزی ۵۰ درخواست داری. کلید فقط در مرورگر شما ذخیره می‌شه — هیچ‌وقت به سرور Trademun فرستاده نمی‌شه.",
      },
    ],
  },
  {
    id: "payment",
    title: "پرداخت و اشتراک",
    icon: "💳",
    items: [
      {
        q: "چطور اشتراک بخرم؟",
        a: "از داشبورد → اشتراک، یا مستقیم از صفحه /subscription. ۴ پلن داری: یک ماهه، سه ماهه (پرفروش)، شش ماهه، یک ساله. دو روش پرداخت: زیبال (فعال‌سازی آنی) یا کارت‌به‌کارت (تا ۲۴ ساعت).",
      },
      {
        q: "اشتراکم فعال نشده، چیکار کنم؟",
        a: "از پنل کاربری → تیکت‌ها، تیکت بزنید و رسید پرداخت رو ضمیمه کنید. معمولاً کمتر از ۲۴ ساعت پاسخ می‌دیم. یا از طریق کانال تلگرام/بله پیام بدید.",
      },
      {
        q: "اشتراکم چطور تمدید می‌شه؟",
        a: "از داشبورد → اشتراک، پلن جدید رو انتخاب کن. اگه اشتراک فعلی هنوز فعاله، از پلن جدید به صورت خودکار استفاده می‌شه. برای تغییر پلن یا درخواست بازگشت وجه، تیکت بزن.",
      },
      {
        q: "کارمزد صرافی چطور حساب می‌شه؟",
        a: "در بخش «اقتصاد معامله» کارت سیگنال، کارمزد رفت‌وبرگشتی + اسپرد + اسلیپیج نشون داده می‌شه. جفت‌های USDT: ~۰.۲۳٪ · جفت‌های تومانی: ~۰.۵۰٪. R:R خالص (بعد از کارمزد) مهم‌ترین معیار است.",
      },
    ],
  },

  {
    id: "extension",
    title: "افزونه کروم",
    icon: "🔌",
    items: [
      {
        q: "افزونه کروم چیه و چطور کار می‌کنه؟",
        a: "افزونه اختصاصی تریدمون برای مرورگر کروم است که به صورت خودکار به WebSocket داخلی صرافی‌های دریا گلد و آلفا گلد متصل می‌شود، قیمت‌های لحظه‌ای XAU/USD را دریافت می‌کند، و در مرورگر شما تحلیل می‌کند. هیچ‌گونه سفارش یا تراکنشی به صورت خودکار انجام نمی‌شود.",
      },
      {
        q: "چرا افزونه فقط برای دریا گلد و آلفا گلد کار می‌کنه؟",
        a: "این دو صرافی، دسترسی به داده‌های لحظه‌ای XAU/USD را به صورت عمومی فراهم می‌کنند. تریدمون به دلیل محدودیت‌های فنی و امنیتی، افزونه را در فاز اول فقط برای این دو صرافی عرضه کرده. ما هیچگونه فعالیت رباتی در این دو صرافی انجام نمی‌دهیم. صرافی‌های دیگر در فازهای بعدی اضافه می‌شوند.",
      },
      {
        q: "چطور افزونه رو نصب کنم؟",
        a: "از داشبورد → افزونه، فایل zip را دانلود کنید. از حالت فشرده خارج کنید. در کروم به chrome://extensions بروید. حالت Developer Mode را فعال کنید. روی Load unpacked کلیک کنید و پوشه را انتخاب کنید. سپس روی آیکون افزونه کلیک کنید و «اتصال به حساب تریدمون» را بزنید.",
      },
      {
        q: "چرا افزونه به داده‌های حسابم دسترسی نداره؟",
        a: "افزونه فقط قیمت‌های لحظه‌ای را از WebSocket عمومی صرافی می‌خواند. هیچ دسترسی به موجودی، سفارش‌ها یا اطلاعات حساب شما ندارد. کلید API صرافی هم ذخیره نمی‌شود. طراحی افزونه بر اساس اصل «حداقل دسترسی» است.",
      },
    ],
  },


  {
    id: "account",
    title: "حساب کاربری",
    icon: "👤",
    items: [
      {
        q: "چطور تیکت بزنم؟",
        a: "از داشبورد → تیکت‌ها → تیکت جدید. موضوع و پیام رو وارد کن، فایل هم می‌تونی ضمیمه کنی. پاسخ ادمین از همون صفحه قابل مشاهده است.",
      },
      {
        q: "امنیت حساب چطوریه؟",
        a: "ورود با OTP (کد پیامکی) یا رمز عبور. کلید OpenRouter فقط در مرورگر شما ذخیره می‌شه. تریدمون هیچ‌وقت از طریق پیام خصوصی، شماره کارت یا رمز عبور درخواست نمی‌کنه.",
      },
      {
        q: "چطور با پشتیبانی تماس بگیرم؟",
        a: "سریع‌ترین راه: کانال تلگرام (t.me/trademun) یا بله (ble.ir/trademun). برای مشکلات حساب: تیکت در پنل کاربری. ساعات پاسخ‌دهی: شنبه تا پنجشنبه، ۹-۲۱.",
      },
      {
        q: "قوانین و سلب مسئولیت تریدمون چیه؟",
        a: "سایت تریدمون صرفاً یک تحلیل‌گر داده و ارائه‌دهنده سیگنال‌های کمکی است. تمامی تحلیل‌ها بر اساس الگوریتم‌های ریاضی و داده‌های تاریخی انجام می‌شود و هیچ‌گونه تضمینی برای سودآوری وجود ندارد. تصمیم‌گیری نهایی برای ورود یا خروج از معامله، کاملاً بر عهده کاربر است و تریدمون هیچ مسئولیتی در قبال سود یا زیان احتمالی کاربران نمی‌پذیرد.",
      },
    ],
  },
];

export default function FAQPage() {
  const [openItems, setOpenItems] = useState<string[]>([]);

  const toggleItem = (id: string) => {
    setOpenItems((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

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
                <MessageCircleQuestion className="h-4 w-4" />
                سوالات متداول
              </div>
              <h1 className="font-display text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
                چه سوالی داری؟
                <br />
                <span className="text-[#d6ad60]">جوابش اینجاست</span>
              </h1>
              <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-gray-400 sm:text-base">
                هر آنچه برای استفاده حرفه‌ای از تریدمون نیاز داری. اگه جوابت رو
                پیدا نکردی، از طریق کانال‌های پشتیبانی با ما در ارتباط باش.
              </p>
            </motion.div>
          </div>
        </section>

        {/* ═══ FAQ ═══ */}
        <section className="px-4 pb-16">
          <div className="mx-auto max-w-3xl space-y-8">
            {FAQ_CATEGORIES.map((category) => (
              <div key={category.id}>
                <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-bold text-[#d6ad60]">
                  <span className="text-xl">{category.icon}</span>
                  {category.title}
                </h2>
                <div className="space-y-2">
                  {category.items.map((item, idx) => {
                    const itemId = `${category.id}-${idx}`;
                    const isOpen = openItems.includes(itemId);
                    return (
                      <div
                        key={itemId}
                        className="overflow-hidden rounded-xl border border-white/10 bg-[#0d1b2d]"
                      >
                        <button
                          onClick={() => toggleItem(itemId)}
                          className="flex w-full items-center justify-between gap-3 p-4 text-right transition-colors hover:bg-white/[0.03]"
                          aria-expanded={isOpen}
                        >
                          <span className="flex-1 text-sm font-bold text-white">
                            {item.q}
                          </span>
                          <ChevronDown
                            className={`h-4 w-4 shrink-0 text-[#d6ad60] transition-transform ${
                              isOpen ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        <AnimatePresence initial={false}>
                          {isOpen && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{
                                duration: 0.25,
                                ease: "easeInOut",
                              }}
                              style={{ overflow: "hidden" }}
                            >
                              <div className="border-t border-white/10 p-4 text-xs leading-relaxed text-gray-400">
                                {item.a}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ CTA ═══ */}
        <section className="px-4 pb-16">
          <div className="mx-auto max-w-2xl rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-br from-[#d6ad60]/10 to-transparent p-8 text-center">
            <HelpCircle className="mx-auto mb-3 h-8 w-8 text-[#d6ad60]" />
            <h2 className="mb-3 font-display text-xl font-bold">
              جوابت رو پیدا نکردی؟
            </h2>
            <p className="mb-6 text-sm text-gray-400">
              تیم پشتیبانی ما آماده کمکه
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/contact">
                <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-6 text-sm font-bold text-[#07111f] hover:opacity-90 sm:w-auto">
                  تماس با ما
                </Button>
              </Link>
              <Link href="/dashboard/tickets">
                <Button
                  variant="outline"
                  className="h-11 w-full gap-2 border-white/20 text-white hover:bg-white/5 sm:w-auto"
                >
                  ثبت تیکت
                  <ArrowLeft className="h-4 w-4" />
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