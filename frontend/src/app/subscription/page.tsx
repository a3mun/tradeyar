"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  CheckCircle2, Copy, ShieldCheck, 
  Zap, Gift, Check, CreditCard, Wallet, Sparkles, Clock, Info, LayoutDashboard
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getToken } from "@/lib/auth";
import Link from "next/link";

const CARD_NUMBER = "5859-4710-1084-0910";
const CARD_HOLDER = "محمدمهدی";

const PENDING_KEY = "trademun_pending_request";

const SEO_KEYWORDS = [
  "تحلیل تکنیکال کریپتو", "سیگنال هوش مصنوعی کریپتو", "مقایسه صرافی‌های ایرانی",
  "تحلیل انس طلا XAU USD", "سیگنال انس طلا", "دریا گلد", "آلفا گلد",
  "تحلیل نوبیتکس", "تحلیل بیت‌پین", "تحلیل والکس", "تحلیل تبدیل",
  "بورس تهران تحلیل تکنیکال", "اسکنر فرصت‌های کریپتو", "عمق بازار کریپتو",
  "شاخص ترس و طمع", "چک‌لیست معاملاتی", "مدیریت ریسک کریپتو", "پروفایل ریسک",
  "افزونه کروم ترید", "تایم‌فریم تحلیل", "RSI MACD تحلیل", "سناریوهای پیش‌بینی بازار",
  "راستی‌آزمایی سیگنال", "تاریخچه معاملات", "تریدمون",
];

export default function SubscriptionPage() {
  const router = useRouter();
  const [selectedPlan, setSelectedPlan] = useState<string>("3_months");
  const [paymentMethod, setPaymentMethod] = useState<"zibal" | "card">("card");
  const [paymentTime, setPaymentTime] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  // 🔴 فقط یک بار تعریف State برای پلن‌ها
  const [plans, setPlans] = useState<any[]>([]);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  const selectedPlanData = plans.find(p => p.id === selectedPlan);
  
  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem(PENDING_KEY) === "true") {
      setSuccess(true);
    }
  }, []);

  // 🔴 دریافت قیمت‌ها از API
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    fetch(`${apiUrl}/admin/pricing`)
      .then(res => res.json())
      .then(data => {
        const formatted = Object.entries(data).map(([id, v]: [string, any]) => ({
          id,
          title: id === "1_month" ? "یک ماهه" : id === "3_months" ? "سه ماهه" : id === "6_months" ? "شش ماهه" : "یک ساله",
          price: v.price,
          oldPrice: v.old_price,
          discount: v.discount,
          days: id === "1_month" ? 30 : id === "3_months" ? 90 : id === "6_months" ? 180 : 365,
          popular: v.popular
        }));
        setPlans(formatted);
      })
      .catch(console.error);
  }, []);

  const copyCard = () => {
    navigator.clipboard.writeText(CARD_NUMBER.replace(/-/g, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRequest = async () => {
    if (!token) { router.push("/login"); return; }
    if (!selectedPlan) { alert("لطفاً یک پلن را انتخاب کنید."); return; }
    if (!paymentTime.trim()) { alert("لطفاً زمان واریز را وارد کنید (مثال: 1404/10/25 - 16:42)"); return; }
    
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/subscription/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ 
        plan: selectedPlan, 
        receipt_note: note, 
        payment_time: paymentTime,
        payment_method: paymentMethod,
        amount: selectedPlanData?.price,
        plan_price_at_purchase: selectedPlanData?.price  // 🔴 قیمت لحظه‌ی خرید
      }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
      if (typeof window !== "undefined") {
        localStorage.setItem(PENDING_KEY, "true");
      }
      setSuccess(true);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[#030712] text-white">
      {/* SEO */}
      <div className="sr-only" aria-hidden="true">
        <h1>خرید اشتراک حرفه‌ای تریدمون | تحلیل تکنیکال کریپتو، سیگنال هوش مصنوعی و تحلیل انس طلا</h1>
        <h2>پلن‌های اشتراک تریدمون — از ۳ روز رایگان تا یک ساله</h2>
        <p>
          تریدمون بهترین پلتفرم تحلیل تکنیکال کریپتو و بورس ایران است. با ۳۲+ اندیکاتور حرفه‌ای، تحلیل هوشمند با کلید شخصی (BYOK)،
          اسکنر فرصت‌ها، مقایسه صرافی‌های ایرانی (نوبیتکس، بیت‌پین، والکس، تبدیل، بورس تهران)، و افزونه اختصاصی کروم برای
          تحلیل لحظه‌ای انس طلا (XAU/USD) در دریا گلد و آلفا گلد. مدیریت ریسک هوشمند، چک‌لیست معاملاتی،
          سناریوهای پیش‌بینی بازار، راستی‌آزمایی سیگنال، شاخص ترس و طمع، و عمق بازار در ۵ تایم‌فریم.
        </p>
        <ul>
          {SEO_KEYWORDS.map((kw, i) => <li key={i}>{kw}</li>)}
        </ul>
      </div>

      <Header />
      <main className="flex-1 container mx-auto p-4 py-6 max-w-5xl">
        
        {/* ═══════ بنر دوره آزمایشی رایگان ═══════ */}
        <motion.div 
          initial={{ opacity: 0, y: 16 }} 
          animate={{ opacity: 1, y: 0 }} 
          className="rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-r from-[#0d1b2d] to-[#051118] p-4 sm:p-5 mb-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg shadow-[#d6ad60]/5"
        >
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="bg-[#d6ad60]/15 p-2.5 rounded-xl border border-[#d6ad60]/30 shrink-0">
              <Gift className="h-6 w-6 text-[#d6ad60]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                دوره آشنایی با تریدمون
                <span className="text-[10px] text-green-400 font-bold bg-green-400/10 px-2 py-0.5 rounded-full border border-green-400/20">۳ روز رایگان</span>
              </h2>
              <p className="text-[11px] text-gray-400 mt-0.5 leading-relaxed">
                همه امکانات تحلیل و سیگنال‌دهی را بدون محدودیت امتحان کنید.
              </p>
            </div>
          </div>

        </motion.div>

        {/* ═══════ بخش امکانات دوره آشنایی ═══════ */}
        <motion.div 
          initial={{ opacity: 0, y: 16 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.08 }} 
          className="rounded-2xl border border-white/5 bg-[#051118] p-4 sm:p-5 mb-6 shadow-sm"
        >
          <div className="flex items-center gap-2 mb-3">
            <Gift className="h-4 w-4 text-gray-400" />
            <h3 className="text-sm font-bold text-gray-100">امکاناتی که در ۳ روز رایگان می‌بینید:</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-2.5 bg-black/20 p-4 rounded-xl">
            {[
              "تحلیل تکنیکال کریپتو (۴ صرافی)",
              "تحلیل تکنیکال فارکس (طلا، نفت، شاخص‌ها)",
              "تحلیل تکنیکال بورس تهران",
              "کارت سیگنال + جدول تایم‌فریم",
              "عمق بازار",
              "شاخص ترس و طمع",
              "سیگنال‌های زنده",
              "سناریوهای پیش رو",
              "نقاط حمایت و مقاومت",
              "چک‌لیست اندیکاتورها",
              "مقایسه قیمت صرافی‌ها",
              "آمار عملکرد سیگنال‌ها",
              "تحلیل بنیادین (به‌زودی)",
              "تقویم اقتصادی (به‌زودی)",
              "ماشین‌حساب سود و ضرر (به‌زودی)",
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                <Check className="h-3.5 w-3.5 text-green-500 shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* ═══════ کارت اصلی (Pro) ═══════ */}
        <motion.div 
          initial={{ opacity: 0, y: 16 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.16 }} 
          className="rounded-2xl border-2 border-[#d6ad60]/60 bg-gradient-to-br from-[#0d1b2d] to-[#051118] p-5 sm:p-6 relative overflow-hidden mb-8 shadow-[0_0_30px_rgba(214,173,96,0.05)]"
        >
          <div className="absolute top-4 left-4 bg-[#d6ad60] text-[#07111f] text-[10px] font-bold px-3 py-1 rounded-full flex items-center gap-1 shadow-lg shadow-[#d6ad60]/30">
            <Sparkles className="h-3 w-3" /> پیشنهاد ویژه
          </div>
          
          <div className="flex items-center gap-3 mb-4 mt-6 sm:mt-2">
            <div className="bg-[#d6ad60]/15 p-2.5 rounded-xl border border-[#d6ad60]/30">
              <Zap className="h-5 w-5 text-[#d6ad60]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[#d6ad60]">اشتراک حرفه‌ای (Pro)</h2>
              <p className="text-[10px] text-gray-400">دسترسی کامل و همیشگی به همه امکانات</p>
            </div>
          </div>
          
          <div className="space-y-2.5 bg-[#d6ad60]/5 p-4 rounded-xl border border-[#d6ad60]/20 mb-5">
            <p className="text-[10px] text-[#d6ad60] mb-2 font-bold">امکانات اختصاصی این پلن:</p>
            <div className="flex items-center gap-2 text-xs text-gray-200 font-bold">
              <Check className="h-3.5 w-3.5 text-green-500 shrink-0" /> 
              <span>همه امکانات دوره آشنایی +</span>
            </div>
            {[
              { label: "اسکنر فرصت‌ها" },
              { label: "مشاوره هوشمند با استفاده از هوش مصنوعی" },
              { label: "کپی داده های خام" },
              { label: "دانلود افزونه اختصاصی کروم (دریا گلد و آلفا گلد)" },
              { label: "درخواست افزونه سفارشی از طریق ثبت تیکت" },
            ].map((item, i) => (
              <div key={i} className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2 text-xs text-gray-200">
                  <Check className="h-3.5 w-3.5 text-green-500 shrink-0" />
                  <span>{item.label}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <h3 className="text-xs font-bold text-white flex items-center gap-2">
                <Zap className="h-3 w-3 text-[#d6ad60]" /> انتخاب مدت زمان اشتراک
              </h3>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
              {/* 🔴 اینجا از plans استفاده می‌کنیم */}
              {plans.map((plan) => {
                const isSelected = selectedPlan === plan.id;
                return (
                  <button
                    key={plan.id}
                    onClick={() => setSelectedPlan(plan.id)}
                    className={`relative p-3 sm:p-4 rounded-xl text-right transition-all duration-200 ${
                      isSelected
                        ? "bg-[#d6ad60]/10 border-2 border-[#d6ad60] ring-1 ring-[#d6ad60]/30"
                        : "bg-black/30 border border-white/5 hover:border-[#d6ad60]/40 hover:bg-white/5"
                    }`}
                  >
                    {plan.popular && (
                      <span className="absolute -top-2.5 right-3 bg-[#d6ad60] text-[#07111f] text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-md shadow-[#d6ad60]/30">
                        <Sparkles className="h-2.5 w-2.5" /> پرفروش
                      </span>
                    )}
                    
                    <div className="flex justify-between items-center mb-1 sm:mb-2">
                      <span className="font-bold text-xs sm:text-sm text-white">{plan.title}</span>
                      {plan.discount > 0 && (
                        <span className="text-[9px] sm:text-[10px] bg-green-500/15 text-green-400 px-1.5 py-0.5 rounded font-bold border border-green-500/20">
                          {plan.discount}٪
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-baseline gap-1 mt-1 sm:mt-0">
                      <span className="font-bold text-sm sm:text-base text-white">{plan.price.toLocaleString("fa-IR")}</span>
                      <span className="text-[9px] text-gray-400">تومان</span>
                    </div>
                    
                    {plan.oldPrice > 0 && (
                      <div className="text-[13px] text-gray-500 line-through mt-0.5">
                        {plan.oldPrice.toLocaleString("fa-IR")}
                      </div>
                    )}
                    
                    {isSelected && (
                      <div className="absolute bottom-2 left-2 w-4 h-4 rounded-full bg-[#d6ad60] flex items-center justify-center">
                        <Check className="h-2.5 w-2.5 text-[#07111f]" strokeWidth={3} />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>

        {/* ═══════ پرداخت ═══════ */}
        <motion.div 
          initial={{ opacity: 0, y: 16 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.24 }} 
          className="rounded-2xl border border-white/5 bg-[#051118] p-5 shadow-sm"
        >
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#d6ad60]" /> روش پرداخت
          </h3>
          
          {success ? (
            <div className="flex flex-col items-center gap-4 py-6">
              <div className="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-green-500" />
              </div>
              <div className="text-center">
                <h4 className="text-base font-bold text-white mb-1">درخواست شما با موفقیت ثبت شد</h4>
                <p className="text-xs text-gray-400 leading-relaxed max-w-md">
                  درخواست شما در حال بررسی توسط ادمین است. پس از تایید، اشتراک شما فعال می‌شود و از طریق <b className="text-gray-200">داشبورد و پیامک</b> مطلع خواهید شد.
                </p>
              </div>
              
              <div className="bg-[#d6ad60]/5 border border-[#d6ad60]/20 rounded-xl p-3 w-full max-w-md">
                <p className="text-[10px] text-gray-400 text-center flex items-center justify-center gap-1.5">
                  <Clock className="h-3 w-3 text-[#d6ad60]" />
                  زمان بررسی معمولاً کمتر از ۲۴ ساعت است
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 w-full max-w-md mt-2">
                <Link href="/dashboard" className="flex-1">
                  <Button className="w-full h-11 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#07111f] font-bold text-sm gap-2">
                    <LayoutDashboard className="h-4 w-4" /> رفتن به داشبورد
                  </Button>
                </Link>
                <Link href="/" className="flex-1">
                  <Button variant="outline" className="w-full h-11 border-white/10 text-gray-300 hover:bg-white/5 text-sm">
                    بازگشت به خانه
                  </Button>
                </Link>
              </div>
            </div>
          ) : !token ? (
            <div className="text-center bg-black/30 p-6 rounded-xl border border-white/5">
              <p className="text-sm text-gray-400 mb-4">برای مشاهده روش‌های پرداخت و خرید اشتراک، لطفاً وارد حساب کاربری خود شوید.</p>
              <Link href="/login" className="w-full inline-block">
                <Button className="w-full sm:w-auto px-8 h-11 text-sm font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#07111f] hover:opacity-90">
                  ورود / ثبت‌نام
                </Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <button
                  onClick={() => setPaymentMethod("zibal")}
                  className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    paymentMethod === "zibal"
                      ? "border-[#d6ad60] bg-[#d6ad60]/10 ring-1 ring-[#d6ad60]/30"
                      : "border-white/5 bg-black/30 hover:bg-white/5 hover:border-[#d6ad60]/40"
                  }`}
                >
                  <Wallet className="h-6 w-6 text-[#d6ad60]" />
                  <span className="text-xs font-bold text-white">درگاه زیبال</span>
                  <span className="text-[9px] bg-green-500/15 text-green-400 px-2 py-0.5 rounded-full font-bold border border-green-500/20">فعال‌سازی آنی</span>
                </button>
                <button
                  onClick={() => setPaymentMethod("card")}
                  className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    paymentMethod === "card"
                      ? "border-[#d6ad60] bg-[#d6ad60]/10 ring-1 ring-[#d6ad60]/30"
                      : "border-white/5 bg-black/30 hover:bg-white/5 hover:border-[#d6ad60]/40"
                  }`}
                >
                  <CreditCard className="h-6 w-6 text-[#d6ad60]" />
                  <span className="text-xs font-bold text-white">کارت به کارت</span>
                  <span className="text-[9px] bg-yellow-500/15 text-yellow-400 px-2 py-0.5 rounded-full font-bold border border-yellow-500/20">تا ۲۴ ساعت</span>
                </button>
              </div>

              {paymentMethod === "zibal" && (
                <div className="animate-in fade-in slide-in-from-top-2 duration-300 bg-black/30 p-4 rounded-xl border border-white/5 text-center">
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mb-3 inline-flex items-center gap-2">
                    <Clock className="h-4 w-4 text-yellow-400" />
                    <span className="text-xs text-yellow-400 font-bold">درگاه پرداخت زیبال به زودی فعال می‌شود</span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    فعلاً از روش <b className="text-white">کارت به کارت</b> استفاده کنید.
                  </p>
                </div>
              )}

              {paymentMethod === "card" && (
                <div className="animate-in fade-in slide-in-from-top-2 duration-300 bg-black/30 p-4 rounded-xl border border-white/5">
                  
                  <div className="mb-4 flex items-start gap-2 bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-2.5">
                    <Info className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
                    <p className="text-[10px] text-yellow-400/90 leading-relaxed">
                      <b>قبل از واریز</b> لطفاً از طریق راه‌های ارتباطی (پشتیبانی یا تیکت) برای پرداخت هماهنگ کنید تا فعال‌سازی تسریع شود.
                    </p>
                  </div>

                  <div className="mb-4 p-3 rounded-xl bg-[#d6ad60]/10 border-2 border-[#d6ad60]/40 text-center">
                    <p className="text-[10px] text-[#d6ad60] mb-1 font-bold">مبلغ دقیق قابل پرداخت:</p>
                    <p className="text-2xl font-bold text-white" dir="ltr">
                      {selectedPlanData?.price.toLocaleString("fa-IR")}
                      <span className="text-xs text-gray-400 mr-1.5">تومان</span>
                    </p>
                  </div>
                  
                  <div className="text-center mb-5">
                    <div className="text-[10px] text-[#d6ad60] mb-1.5 font-bold">شماره کارت:</div>
                    <div className="font-mono text-lg md:text-xl font-bold dir-ltr tracking-widest text-white mb-1">{CARD_NUMBER}</div>
                    <div className="text-[10px] text-gray-400">به نام: {CARD_HOLDER}</div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={copyCard} 
                      className="mt-2 h-8 px-4 rounded-full border-white/10 text-[#d6ad60] hover:bg-[#d6ad60]/10 gap-2 text-xs"
                    >
                      {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                      {copied ? "کپی شد" : "کپی شماره کارت"}
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                    <div className="space-y-1">
                      <label className="text-[10px] text-gray-400 mr-1 flex items-center gap-1">
                        زمان واریز <span className="text-red-500 font-bold">*</span>
                        <span className="text-[9px] text-gray-600">(اجباری برای تایید)</span>
                      </label>
                      <Input 
                        placeholder="1404/10/25 - 16:42" 
                        value={paymentTime} 
                        onChange={(e) => setPaymentTime(e.target.value)} 
                        className="h-10 bg-black/40 border-white/5 text-white text-sm dir-ltr text-center" 
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] text-gray-400 mr-1">کد پیگیری (اختیاری)</label>
                      <Input 
                        placeholder="۱۲۳۴۵۶" 
                        value={note} 
                        onChange={(e) => setNote(e.target.value)} 
                        className="h-10 bg-black/40 border-white/5 text-white text-sm text-center" 
                      />
                    </div>
                  </div>

                  <div className="mb-4 p-3 rounded-lg bg-[#d6ad60]/10 border border-[#d6ad60]/25 text-center">
                    <p className="text-xs text-gray-300 leading-relaxed">
                      شما در حال خرید <b className="text-white">{selectedPlanData?.title}</b> با مبلغ <b className="text-[#d6ad60]">{selectedPlanData?.price.toLocaleString("fa-IR")} تومان</b> از طریق <b className="text-white">کارت به کارت</b> هستید.
                    </p>
                  </div>

                  <Button 
                    onClick={handleRequest} 
                    disabled={loading} 
                    className="w-full h-11 text-sm font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#07111f] hover:opacity-90 shadow-lg shadow-[#d6ad60]/20"
                  >
                    {loading ? "در حال ارسال..." : "ثبت درخواست و ارسال رسید"}
                  </Button>

                  <div className="mt-6 flex w-full justify-center">
                    <Link href="/dashboard">
                      <Button className="h-9 bg-white/5 hover:bg-white/10 text-white border border-white/10 text-xs font-bold gap-1.5">
                        بازگشت به داشبورد
                      </Button>
                    </Link>
                  </div>

                </div>
              )}
            </>
          )}
        </motion.div>

      </main>
      <PublicFooter />
    </div>
  );
}