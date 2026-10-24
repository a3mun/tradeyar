"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LogOut, CheckCircle2, Copy, CreditCard, Sparkles, ShieldCheck } from "lucide-react";

const PLANS = [
  { id: "1_month", title: "یک ماهه", price: 300000, oldPrice: 0, discount: 0, days: 30, popular: false },
  { id: "3_months", title: "سه ماهه", price: 810000, oldPrice: 900000, discount: 10, days: 90, popular: true },
  { id: "6_months", title: "شش ماهه", price: 1440000, oldPrice: 1800000, discount: 20, days: 180, popular: false },
  { id: "12_months", title: "یک ساله", price: 2520000, oldPrice: 3600000, discount: 30, days: 365, popular: false },
];

const CARD_NUMBER = "5859-4710-2303-7983";
const CARD_HOLDER = "محمدمهدی";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "free": "رایگان (تست ۳ روزه)",
    "1_month": "اشتراک یک ماهه",
    "3_months": "اشتراک سه ماهه",
    "6_months": "اشتراک شش ماهه",
    "12_months": "اشتراک یک ساله",
  };
  return map[plan] || plan;
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [sub, setSub] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string>("3_months");
  const [note, setNote] = useState("");
  const [fullName, setFullName] = useState(""); // ⬅️ نام و نام خانوادگی
  const [paymentTime, setPaymentTime] = useState(""); // ⬅️ زمان واریز
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  useEffect(() => {
    const u = getUser();
    if (!u) { router.replace("/login"); return; }
    setUserData(u);
    if (u.full_name) setFullName(u.full_name); // ⬅️ اضافه شد
    
  
    fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error("خطا در دریافت اطلاعات");
      return res.json();
    })
    .then(data => setSub(data.subscription))
    .catch(err => console.error("خطا در دریافت اشتراک", err));
  }, [router, apiUrl, token]);

  const handleLogout = () => { removeToken(); router.replace("/login"); };
  
  const copyCard = () => {
    navigator.clipboard.writeText(CARD_NUMBER.replace(/-/g, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRequest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/subscription/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ 
          plan: selectedPlan, 
          receipt_note: note,
          full_name: fullName,
          payment_time: paymentTime
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSuccess(true);
      setShowForm(false);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">داشبورد کاربری</h1>
            <Button variant="destructive" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 ml-2" /> خروج
            </Button>
          </div>

          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold border-b pb-2">اطلاعات حساب</h2>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">شماره موبایل:</span>
              <span className="font-mono dir-ltr">{user.phone}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">وضعیت:</span>
              <span className="text-green-500 font-medium">فعال</span>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold border-b pb-2">وضعیت اشتراک</h2>
            {sub ? (
              <>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">نوع پلن:</span>
                  <span className="font-bold">{getPlanNameFa(sub.plan)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">تاریخ انقضا:</span>
                  <span>{new Date(sub.end_date).toLocaleDateString('fa-IR')}</span>
                </div>

                <div className="pt-4 border-t mt-4">
                  {success ? (
                    <div className="flex items-center gap-2 text-green-500 bg-green-500/10 p-3 rounded-lg">
                      <CheckCircle2 className="h-5 w-5" />
                      <span className="text-sm">درخواست شما ثبت شد. پس از تایید ادمین، اشتراک شما فعال می‌شود.</span>
                    </div>
                  ) : showForm ? (
                    <div className="space-y-5 bg-muted/20 p-5 rounded-xl border">
                      <div className="text-center space-y-1 mb-4">
                        <h3 className="font-bold text-lg text-primary">ارتقا به نسخه حرفه‌ای</h3>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {PLANS.map((plan) => (
                          <button
                            key={plan.id}
                            onClick={() => setSelectedPlan(plan.id)}
                            className={`relative p-4 rounded-xl border-2 text-right transition-all ${
                              selectedPlan === plan.id 
                                ? "border-primary bg-primary/10 shadow-md ring-2 ring-primary/20" 
                                : "border-border hover:border-primary/50 hover:bg-muted/50"
                            }`}
                          >
                            {plan.popular && (
                              <span className="absolute -top-3 right-4 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                                <Sparkles className="h-3 w-3" /> پرفروش‌ترین
                              </span>
                            )}
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-bold text-sm">{plan.title}</span>
                              {plan.discount > 0 && (
                                <span className="text-xs bg-green-500/20 text-green-500 px-2 py-0.5 rounded-full font-bold">
                                  {plan.discount}% تخفیف
                                </span>
                              )}
                            </div>
                            <div className="flex items-baseline gap-2 mt-2">
                              <span className="font-bold text-lg">{plan.price.toLocaleString('fa-IR')}</span>
                              <span className="text-xs text-muted-foreground">تومان</span>
                            </div>
                            {plan.oldPrice > 0 && (
                              <div className="text-xs text-red-400/80 line-through mt-1 decoration-red-400/50">
                                {plan.oldPrice.toLocaleString('fa-IR')} تومان
                              </div>
                            )}
                          </button>
                        ))}
                      </div>

                      <div className="bg-background border rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <div className="text-center sm:text-right w-full">
                          <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1 justify-center sm:justify-start">
                            <ShieldCheck className="h-4 w-4 text-green-500" /> پرداخت با هماهنگی (کارت به کارت)
                          </div>
                          <div className="font-mono text-lg dir-ltr tracking-wider">{CARD_NUMBER}</div>
                          <div className="text-xs text-muted-foreground mt-1">به نام: {CARD_HOLDER} (بانک خاورمیانه)</div>
                        </div>
                        <Button variant="outline" size="icon" onClick={copyCard} className="shrink-0 h-12 w-12 rounded-full">
                          {copied ? <CheckCircle2 className="h-5 w-5 text-green-500" /> : <Copy className="h-5 w-5" />}
                        </Button>
                      </div>

                      {/* بخش نام و زمان واریز */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">نام و نام خانوادگی</label>
                            <Input 
                            value={user.full_name || "ثبت نشده"} 
                            disabled
                            className="h-12 bg-muted/50 cursor-not-allowed" 
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs text-muted-foreground">زمان واریز</label>
                            <Input 
                            placeholder="مثلاً: ۱۴:۳۰ - ۱۴۰۳/۰۸/۰۳" 
                            value={paymentTime} 
                            onChange={(e) => setPaymentTime(e.target.value)} 
                            className="h-12"
                            />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">توضیحات یا کد پیگیری (اختیاری)</label>
                        <Input 
                          placeholder="کد پیگیری ۱۲۳۴" 
                          value={note} 
                          onChange={(e) => setNote(e.target.value)} 
                          className="h-12 text-center"
                        />
                      </div>

                      <div className="flex gap-3 pt-2">
                        <Button onClick={handleRequest} disabled={loading} className="flex-1 h-12 text-base font-bold bg-primary hover:bg-primary/90">
                          {loading ? "در حال ارسال..." : "ثبت درخواست"}
                        </Button>
                        <Button variant="outline" onClick={() => setShowForm(false)} className="h-12">انصراف</Button>
                      </div>
                    </div>
                  ) : (
                    <Button onClick={() => setShowForm(true)} className="w-full h-12 gap-2 text-base font-bold bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20">
                      <CreditCard className="h-5 w-5" />
                      ارتقا و تمدید اشتراک
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <p className="text-muted-foreground text-sm">در حال دریافت اطلاعات...</p>
            )}
          </div>

        </div>
      </main>
      <Footer />
    </div>
  );
}