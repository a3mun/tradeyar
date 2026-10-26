"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken, setUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { 
  LogOut, CheckCircle2, Copy, CreditCard, Sparkles, ShieldCheck, 
  Pencil, MessageSquare, Home, Mail, Lock, User as UserIcon, Calendar, 
  Crown, Clock, Zap, ArrowRight
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import Link from "next/link";

const PLANS = [
  { id: "1_month", title: "یک ماهه", price: 390000, oldPrice: 590000, discount: 33, days: 30, popular: false },
  { id: "3_months", title: "سه ماهه", price: 1050000, oldPrice: 1770000, discount: 40, days: 90, popular: true },
  { id: "6_months", title: "شش ماهه", price: 1870000, oldPrice: 3540000, discount: 47, days: 180, popular: false },
  { id: "12_months", title: "یک ساله", price: 3270000, oldPrice: 7080000, discount: 54, days: 365, popular: false },
];
const CARD_NUMBER = "5859-4710-2303-7983";
const CARD_HOLDER = "محمدمهدی";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "free": "رایگان (تست ۳ روزه)", "1_month": "اشتراک یک ماهه", "3_months": "اشتراک سه ماهه", "6_months": "اشتراک شش ماهه", "12_months": "اشتراک یک ساله", "نامحدود (مدیر)": "نامحدود (مدیر)"
  };
  return map[plan] || plan || "نامشخص";
};

// ⬅️ تابع جدید برای تشخیص وضعیت فعال/منقضی
const getSubStatus = (sub: any) => {
  if (!sub) return { active: false, text: "نامشخص" };
  const endDate = sub.end_date ? new Date(sub.end_date) : null;
  const now = new Date();
  const isExpired = endDate ? endDate.getTime() < now.getTime() : false;
  
  if (sub.status === "active" && !isExpired) {
    return { active: true, text: "فعال" };
  }
  return { active: false, text: "منقضی" };
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [sub, setSub] = useState<any>(null);
  
  // فرم تمدید اشتراک
  const [showForm, setShowForm] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string>("3_months");
  const [note, setNote] = useState("");
  const [paymentTime, setPaymentTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  // فرم ویرایش پروفایل
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  useEffect(() => {
    const u = getUser();
    if (!u) { router.replace("/login"); return; }
    setUserData(u);
    setNewName(u.full_name || "");
    setNewEmail(u.email || "");
    
    fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.json()).then(data => setSub(data.subscription)).catch(err => console.error(err));
  }, [router, apiUrl, token]);

  const handleLogout = () => { removeToken(); router.replace("/login"); };
  
  const copyCard = () => { navigator.clipboard.writeText(CARD_NUMBER.replace(/-/g, "")); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  const handleUpdateProfile = async () => {
    if (!newName || newName.length < 2) return alert("نام باید حداقل ۲ حرف باشد");
    
    if (newPassword) {
      if (newPassword.length < 6) return alert("رمز جدید باید حداقل ۶ حرف باشد");
      if (newPassword !== confirmPassword) return alert("رمز جدید و تکرار آن مطابقت ندارند");
    }
    
    setEditLoading(true);
    try {
      const res = await fetch(`${apiUrl}/auth/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          full_name: newName,
          email: newEmail || undefined,
          old_password: oldPassword || undefined,
          new_password: newPassword || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا در ذخیره");
      
      setUser(data.user);
      setUserData(data.user);
      setIsEditOpen(false);
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) { alert(err.message); } finally { setEditLoading(false); }
  };

  const handleRequest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/subscription/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan: selectedPlan, receipt_note: note, payment_time: paymentTime }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSuccess(true);
      setShowForm(false);
    } catch (err: any) { alert(err.message); } finally { setLoading(false); }
  };

  if (!user) return <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">در حال بارگذاری...</div>;

  const subStatus = getSubStatus(sub);

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-4xl space-y-8">
        
        {/* ═══ هدر خوش‌آمدگویی ═══ */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">
              خوش آمدی، <span className="text-[#d6ad60]">{user.full_name || "کاربر تریدمون"}</span> 👋
            </h1>
            <p className="text-gray-400 mt-1 text-sm">امروز چه خبر؟ بازار منتظرته.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/">
              <Button variant="outline" size="sm" className="gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white">
                <Home className="h-4 w-4" /> صفحه اصلی
              </Button>
            </Link>
            <Button variant="destructive" size="sm" onClick={handleLogout} className="gap-2">
              <LogOut className="h-4 w-4" /> خروج
            </Button>
          </div>
        </motion.div>

        {/* ═══ کارت وضعیت اشتراک (برجسته) ═══ */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="relative overflow-hidden rounded-3xl border border-[#d6ad60]/20 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-6 shadow-2xl">
          <div className="absolute top-0 right-0 p-4 opacity-10"><Crown className="h-24 w-24 text-[#d6ad60]" /></div>
          
          <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-[#d6ad60]">
                <Crown className="h-5 w-5" />
                <span className="text-sm font-bold">وضعیت اشتراک</span>
              </div>
              {sub ? (
                <>
                  <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                    {getPlanNameFa(sub.plan)}
                    {/* ⬅️ نقطه رنگی وضعیت */}
                    <span className={`inline-block h-2.5 w-2.5 rounded-full ${subStatus.active ? "bg-green-500" : "bg-red-500"}`} />
                  </h2>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Clock className="h-4 w-4" />
                    <span>انقضا: {sub.end_date ? new Date(sub.end_date).toLocaleDateString('fa-IR') : "نامحدود"}</span>
                  </div>
                </>
              ) : (
                <h2 className="text-2xl font-bold text-white">در حال دریافت...</h2>
              )}
            </div>

            {!showForm && !success && (
              <Button onClick={() => setShowForm(true)} className="h-12 px-6 gap-2 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90 shadow-lg shadow-[#d6ad60]/20 shrink-0">
                <Zap className="h-5 w-5" /> ارتقا / تمدید
              </Button>
            )}
          </div>

          {/* فرم تمدید — بدون تغییر */}
          {success ? (
            <div className="relative z-10 mt-6 flex items-center gap-2 text-green-500 bg-green-500/10 p-4 rounded-xl border border-green-500/20">
              <CheckCircle2 className="h-5 w-5" />
              <span className="text-sm">درخواست شما ثبت شد. پس از تایید ادمین، اشتراک فعال می‌شود.</span>
            </div>
          ) : showForm ? (
            <div className="relative z-10 mt-6 space-y-5 bg-black/20 p-5 rounded-2xl border border-white/10">
              <div className="text-center space-y-1">
                <h3 className="font-bold text-lg text-[#d6ad60]">ارتقا به نسخه حرفه‌ای</h3>
                <p className="text-xs text-gray-400">با خرید اشتراک، از تمام امکانات بدون محدودیت استفاده کن.</p>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {PLANS.map((plan) => (
                  <button key={plan.id} onClick={() => setSelectedPlan(plan.id)} className={`relative p-4 rounded-xl border-2 text-right transition-all ${selectedPlan === plan.id ? "border-[#d6ad60] bg-[#d6ad60]/10 shadow-md" : "border-white/10 hover:border-[#d6ad60]/50 hover:bg-white/5"}`}>
                    {plan.popular && (
                      <span className="absolute -top-3 right-4 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                        <Sparkles className="h-3 w-3" /> پرفروش‌ترین
                      </span>
                    )}
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-sm text-white">{plan.title}</span>
                      {plan.discount > 0 && (
                        <span className="text-xs bg-green-500/20 text-green-500 px-2 py-0.5 rounded-full font-bold">{plan.discount}% تخفیف</span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="font-bold text-lg text-white">{plan.price.toLocaleString('fa-IR')}</span>
                      <span className="text-xs text-gray-400">تومان</span>
                    </div>
                    {plan.oldPrice > 0 && (
                      <div className="text-xs text-red-400/80 line-through mt-1 decoration-red-400/50">{plan.oldPrice.toLocaleString('fa-IR')} تومان</div>
                    )}
                  </button>
                ))}
              </div>

              <div className="bg-black/30 border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-center sm:text-right w-full">
                  <div className="text-xs text-[#d6ad60] mb-1 flex items-center gap-1 justify-center sm:justify-start"><ShieldCheck className="h-4 w-4" /> پرداخت با هماهنگی (کارت به کارت)</div>
                  <div className="font-mono text-lg dir-ltr tracking-wider text-white">{CARD_NUMBER}</div>
                  <div className="text-xs text-gray-400 mt-1">به نام: {CARD_HOLDER} (بانک خاورمیانه)</div>
                </div>
                <Button variant="outline" size="icon" onClick={copyCard} className="shrink-0 h-12 w-12 rounded-full border-white/20 text-[#d6ad60] hover:bg-[#d6ad60]/10">
                  {copied ? <CheckCircle2 className="h-5 w-5 text-green-500" /> : <Copy className="h-5 w-5" />}
                </Button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs text-gray-400">زمان واریز (اختیاری)</label>
                  <Input placeholder="مثلاً: ۱۴:۳۰ - ۱۴۰۳/۰۸/۰۳" value={paymentTime} onChange={(e) => setPaymentTime(e.target.value)} className="h-12 bg-black/30 border-white/10 text-white" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-gray-400">توضیحات یا کد پیگیری (اختیاری)</label>
                  <Input placeholder="کد پیگیری ۱۲۳۴" value={note} onChange={(e) => setNote(e.target.value)} className="h-12 bg-black/30 border-white/10 text-white text-center" />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <Button onClick={handleRequest} disabled={loading} className="flex-1 h-12 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90">
                  {loading ? "در حال ارسال..." : "ثبت درخواست"}
                </Button>
                <Button variant="outline" onClick={() => setShowForm(false)} className="h-12 border-white/20 text-white hover:bg-white/10">انصراف</Button>
              </div>
            </div>
          ) : null}
        </motion.div>

        {/* ═══ کارت اطلاعات حساب (فشرده) ═══ */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="rounded-2xl border border-white/10 bg-[#0d1b2dd0] p-6 shadow-xl backdrop-blur-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <UserIcon className="h-5 w-5 text-[#d6ad60]" /> اطلاعات حساب
            </h2>
            <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
              <DialogTrigger className="inline-flex h-8 items-center justify-center gap-2 rounded-lg border border-white/10 bg-transparent px-3 text-xs font-medium text-gray-300 transition-colors hover:bg-white/5 hover:text-white">
                <Pencil className="h-3.5 w-3.5" /> ویرایش
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px] bg-[#0d1b2d] border-white/10 text-white">
                <DialogHeader>
                  <DialogTitle className="text-[#d6ad60]">ویرایش پروفایل</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 pt-4">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">نام نمایشی</label>
                    <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="نام جدید" className="bg-black/30 border-white/10" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">ایمیل (برای اطلاع‌رسانی)</label>
                    <Input value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="example@email.com" dir="ltr" className="bg-black/30 border-white/10 text-center" />
                  </div>
                  
                  <div className="border-t border-white/10 pt-4 mt-2 space-y-3">
                    <h3 className="text-sm font-bold text-[#d6ad60]">تغییر رمز عبور</h3>
                    {user?.hashed_password && (
                      <div>
                        <label className="text-xs text-gray-400 mb-1 block">رمز عبور فعلی</label>
                        <Input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} placeholder="رمز فعلی" dir="ltr" className="bg-black/30 border-white/10 text-center" />
                      </div>
                    )}
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">رمز عبور جدید</label>
                      <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="حداقل ۶ حرف" dir="ltr" className="bg-black/30 border-white/10 text-center" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">تکرار رمز جدید</label>
                      <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="تکرار رمز" dir="ltr" className="bg-black/30 border-white/10 text-center" />
                    </div>
                  </div>
                  
                  <Button onClick={handleUpdateProfile} disabled={editLoading} className="w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold">
                    {editLoading ? "در حال ذخیره..." : "ذخیره تغییرات"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><Mail className="h-4 w-4" /></div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400">ایمیل</p>
                <p className="text-sm text-white truncate" dir="ltr">{user.email || "ثبت نشده"}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><Lock className="h-4 w-4" /></div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400">رمز عبور</p>
                <p className={`text-sm ${user.hashed_password ? "text-green-500" : "text-yellow-500"}`}>
                  {user.hashed_password ? "تعیین شده" : "تعیین نشده"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><UserIcon className="h-4 w-4" /></div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400">شماره موبایل</p>
                <p className="text-sm text-white font-mono dir-ltr">{user.phone}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><ShieldCheck className="h-4 w-4" /></div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-400">وضعیت</p>
                {/* ⬅️ نمایش پویا */}
                <p className={`text-sm ${subStatus.active ? "text-green-500" : "text-red-500"}`}>
                  {subStatus.text}
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ═══ دسترسی سریع ═══ */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link href="/dashboard/tickets" className="block">
            <Button variant="outline" className="group h-20 w-full justify-between rounded-2xl border-white/10 bg-[#0d1b2dd0] px-6 text-white hover:bg-white/5 hover:border-[#d6ad60]/30 transition-all">
              <div className="flex items-center gap-3 text-right">
                <div className="bg-[#d6ad60]/10 p-3 rounded-xl text-[#d6ad60] group-hover:scale-110 transition-transform"><MessageSquare className="h-6 w-6" /></div>
                <div>
                  <p className="font-bold text-sm">ارسال تیکت به پشتیبانی</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">سوال یا مشکلی داری؟ بهمون بگو</p>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-gray-500 group-hover:text-[#d6ad60] transition-colors" />
            </Button>
          </Link>
          <Button variant="outline" className="group h-20 justify-between rounded-2xl border-white/10 bg-[#0d1b2dd0] px-6 text-white hover:bg-white/5 hover:border-[#d6ad60]/30 transition-all">
            <div className="flex items-center gap-3 text-right">
              <div className="bg-[#d6ad60]/10 p-3 rounded-xl text-[#d6ad60] group-hover:scale-110 transition-transform"><Sparkles className="h-6 w-6" /></div>
              <div>
                <p className="font-bold text-sm">تنظیمات هوش مصنوعی</p>
                <p className="text-[10px] text-gray-400 mt-0.5">کلید API خودت رو وصل کن</p>
              </div>
            </div>
            <ArrowRight className="h-5 w-5 text-gray-500 group-hover:text-[#d6ad60] transition-colors" />
          </Button>
        </motion.div>

      </main>
      <Footer />
    </div>
  );
}