"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken, setUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LogOut, CheckCircle2, Copy, CreditCard, Sparkles, ShieldCheck, Pencil, MessageSquare, Home, Globe, Send } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import Link from "next/link";
import { motion } from "framer-motion";

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
    "free": "رایگان (تست ۳ روزه)", "1_month": "اشتراک یک ماهه", "3_months": "اشتراک سه ماهه", "6_months": "اشتراک شش ماهه", "12_months": "اشتراک یک ساله", "نامحدود (مدیر)": "نامحدود (مدیر)"
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
  const [paymentTime, setPaymentTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  useEffect(() => {
    const u = getUser();
    if (!u) { router.replace("/login"); return; }
    setUserData(u);
    setNewName(u.full_name || "");
    fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.json()).then(data => setSub(data.subscription)).catch(err => console.error(err));
  }, [router, apiUrl, token]);

  const handleLogout = () => { removeToken(); router.replace("/login"); };
  
  const copyCard = () => { navigator.clipboard.writeText(CARD_NUMBER.replace(/-/g, "")); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  const handleUpdateName = async () => {
    if (!newName || newName.length < 2) return alert("نام باید حداقل ۲ حرف باشد");
    setEditLoading(true);
    try {
      const res = await fetch(`${apiUrl}/auth/me`, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ full_name: newName }) });
      if (!res.ok) throw new Error("خطا");
      const updatedUser = { ...user, full_name: newName };
      setUserData(updatedUser); setUser(updatedUser); setIsEditOpen(false);
    } catch (err) { alert("مشکلی پیش آمد"); } finally { setEditLoading(false); }
  };

  const handleRequest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/subscription/request`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ plan: selectedPlan, receipt_note: note, payment_time: paymentTime }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSuccess(true); setShowForm(false);
    } catch (err: any) { alert(err.message); } finally { setLoading(false); }
  };

  if (!user) return <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">در حال بارگذاری...</div>;

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#07111f] text-white">
      {/* پس‌زمینه */}
      <div className="absolute inset-0 z-0 opacity-30">
        <div className="absolute inset-0 bg-gradient-to-br from-[#d6ad6010] via-transparent to-[#10b98110]" />
      </div>

      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6 border-b border-white/5">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img src="/icon-192.png" alt="Trademun" className="h-10 w-10 rounded-xl object-contain" />
          <span className="text-xl font-bold">تریدمون</span>
        </Link>
        <Button variant="destructive" size="sm" onClick={handleLogout} className="gap-2">
          <LogOut className="h-4 w-4" /> خروج
        </Button>
      </header>

      <main className="relative z-10 container mx-auto p-4 py-8 max-w-3xl space-y-6">
        
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-[#d6ad60]">داشبورد کاربری</h1>
          <Link href="/">
            <Button variant="outline" size="sm" className="gap-2 border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10">
              <Home className="h-4 w-4" /> صفحه اصلی
            </Button>
          </Link>
        </div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="rounded-2xl border border-white/10 bg-[#0d1b2dd0] p-6 shadow-xl backdrop-blur-xl space-y-4">
          <h2 className="text-lg font-semibold border-b border-white/10 pb-2 text-[#d6ad60]">اطلاعات حساب</h2>
          <div className="flex justify-between items-center"><span className="text-gray-400">شماره موبایل:</span><span className="font-mono dir-ltr text-white">{user.phone}</span></div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400">نام نمایشی:</span>
            <div className="flex items-center gap-2">
              <span className="font-medium text-white">{user.full_name || "ثبت نشده"}</span>
              <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
                <DialogTrigger className="text-[#d6ad60] hover:text-[#d6ad60]/80 transition-colors"><Pencil className="h-4 w-4" /></DialogTrigger>
                <DialogContent className="sm:max-w-[425px] bg-[#0d1b2d] border-white/10 text-white">
                  <DialogHeader><DialogTitle>ویرایش نام نمایشی</DialogTitle></DialogHeader>
                  <div className="space-y-4 pt-4">
                    <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="نام جدید" className="bg-black/30 border-white/10" />
                    <Button onClick={handleUpdateName} disabled={editLoading} className="w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold">{editLoading ? "در حال ذخیره..." : "ذخیره"}</Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>
          <div className="flex justify-between items-center"><span className="text-gray-400">وضعیت:</span><span className="text-green-500 font-medium bg-green-500/10 px-2 py-1 rounded">فعال</span></div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="rounded-2xl border border-white/10 bg-[#0d1b2dd0] p-6 shadow-xl backdrop-blur-xl space-y-4">
          <h2 className="text-lg font-semibold border-b border-white/10 pb-2 text-[#d6ad60]">وضعیت اشتراک</h2>
          {sub ? (
            <>
              <div className="flex justify-between items-center"><span className="text-gray-400">نوع پلن:</span><span className="font-bold text-white bg-[#d6ad60]/10 text-[#d6ad60] px-3 py-1 rounded-full">{getPlanNameFa(sub.plan)}</span></div>
              <div className="flex justify-between items-center"><span className="text-gray-400">تاریخ انقضا:</span><span className="text-white">{sub.end_date ? new Date(sub.end_date).toLocaleDateString('fa-IR') : "نامحدود"}</span></div>
              
              <div className="pt-4 border-t border-white/10 mt-4">
                {success ? (
                  <div className="flex items-center gap-2 text-green-500 bg-green-500/10 p-3 rounded-lg"><CheckCircle2 className="h-5 w-5" /><span className="text-sm">درخواست شما ثبت شد.</span></div>
                ) : showForm ? (
                  <div className="space-y-5 bg-black/20 p-5 rounded-xl border border-white/10">
                    <div className="text-center space-y-1 mb-4"><h3 className="font-bold text-lg text-[#d6ad60]">ارتقا به نسخه حرفه‌ای</h3></div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {PLANS.map((plan) => (
                        <button key={plan.id} onClick={() => setSelectedPlan(plan.id)} className={`relative p-4 rounded-xl border-2 text-right transition-all ${selectedPlan === plan.id ? "border-[#d6ad60] bg-[#d6ad60]/10 shadow-md ring-2 ring-[#d6ad60]/20" : "border-white/10 hover:border-[#d6ad60]/50 hover:bg-white/5"}`}>
                          {plan.popular && (<span className="absolute -top-3 right-4 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm"><Sparkles className="h-3 w-3" /> پرفروش‌ترین</span>)}
                          <div className="flex justify-between items-center mb-1"><span className="font-bold text-sm text-white">{plan.title}</span>{plan.discount > 0 && (<span className="text-xs bg-green-500/20 text-green-500 px-2 py-0.5 rounded-full font-bold">{plan.discount}% تخفیف</span>)}</div>
                          <div className="flex items-baseline gap-2 mt-2"><span className="font-bold text-lg text-white">{plan.price.toLocaleString('fa-IR')}</span><span className="text-xs text-gray-400">تومان</span></div>
                          {plan.oldPrice > 0 && (<div className="text-xs text-red-400/80 line-through mt-1 decoration-red-400/50">{plan.oldPrice.toLocaleString('fa-IR')} تومان</div>)}
                        </button>
                      ))}
                    </div>
                    <div className="bg-black/30 border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                      <div className="text-center sm:text-right w-full">
                        <div className="text-xs text-[#d6ad60] mb-1 flex items-center gap-1 justify-center sm:justify-start"><ShieldCheck className="h-4 w-4" /> پرداخت با هماهنگی (کارت به کارت)</div>
                        <div className="font-mono text-lg dir-ltr tracking-wider text-white">{CARD_NUMBER}</div>
                        <div className="text-xs text-gray-400 mt-1">به نام: {CARD_HOLDER} (بانک خاورمیانه)</div>
                      </div>
                      <Button variant="outline" size="icon" onClick={copyCard} className="shrink-0 h-12 w-12 rounded-full border-white/20 text-[#d6ad60] hover:bg-[#d6ad60]/10">{copied ? <CheckCircle2 className="h-5 w-5 text-green-500" /> : <Copy className="h-5 w-5" />}</Button>
                    </div>
                    <div className="space-y-2"><label className="text-xs text-gray-400">زمان واریز (اختیاری)</label><Input placeholder="مثلاً: ۱۴:۳۰ - ۱۴۰۳/۰۸/۰۳" value={paymentTime} onChange={(e) => setPaymentTime(e.target.value)} className="h-12 bg-black/30 border-white/10 text-white" /></div>
                    <div className="space-y-2"><label className="text-xs text-gray-400">توضیحات یا کد پیگیری (اختیاری)</label><Input placeholder="کد پیگیری ۱۲۳۴" value={note} onChange={(e) => setNote(e.target.value)} className="h-12 bg-black/30 border-white/10 text-white text-center" /></div>
                    <div className="flex gap-3 pt-2">
                      <Button onClick={handleRequest} disabled={loading} className="flex-1 h-12 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90">{loading ? "در حال ارسال..." : "ثبت درخواست"}</Button>
                      <Button variant="outline" onClick={() => setShowForm(false)} className="h-12 border-white/20 text-white hover:bg-white/10">انصراف</Button>
                    </div>
                  </div>
                ) : (
                  <Button onClick={() => setShowForm(true)} className="w-full h-12 gap-2 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90 shadow-lg shadow-[#d6ad60]/20"><CreditCard className="h-5 w-5" /> ارتقا و تمدید اشتراک</Button>
                )}
              </div>
            </>
          ) : (<p className="text-gray-400 text-sm text-center py-4">در حال دریافت...</p>)}
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Button variant="outline" className="h-14 gap-2 text-sm font-bold border-white/10 bg-[#0d1b2dd0] text-white hover:bg-white/5"><MessageSquare className="h-5 w-5 text-[#d6ad60]" /> ارسال تیکت به پشتیبانی</Button>
          <Button variant="outline" className="h-14 gap-2 text-sm font-bold border-white/10 bg-[#0d1b2dd0] text-white hover:bg-white/5"><Sparkles className="h-5 w-5 text-[#d6ad60]" /> تنظیمات هوش مصنوعی</Button>
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/5 bg-[#07111f]/50 px-4 py-4 text-center text-[10px] text-gray-500 backdrop-blur-sm sm:px-6 mt-auto">
        <div className="flex flex-wrap items-center justify-center gap-4">
          <span>© 2026 تریدمون</span>
          <span className="hidden sm:inline">•</span>
          <span>دستیار هوشمند بازارهای مالی</span>
          <span className="hidden sm:inline">•</span>
          <a href="https://trademun.ir" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-[#d6ad60] transition-colors"><Globe className="h-3 w-3" /> trademun.ir</a>
          <a href="https://t.me/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-[#d6ad60] transition-colors"><Send className="h-3 w-3" /> t.me/trademun</a>
        </div>
        <p className="mt-2 text-[9px] opacity-70">⚠️ تحلیل‌ها صرفاً جنبه آموزشی دارند.</p>
      </footer>
    </main>
  );
}