"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken, setUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import { 
  LogOut, CheckCircle2, Copy, Sparkles, ShieldCheck, 
  Pencil, MessageSquare, Home, Mail, Lock, User as UserIcon, 
  Crown, Clock, Zap, X, Send, Bot, Download, BookOpen, Gift
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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
    "free": "پلن رایگان", 
    "1_month": "اشتراک یک ماهه", 
    "3_months": "اشتراک سه ماهه", 
    "6_months": "اشتراک شش ماهه", 
    "12_months": "اشتراک یک ساله", 
    "نامحدود (مدیر)": "نامحدود (مدیر)"
  };
  return map[plan] || plan || "نامشخص";
};

const getSubStatus = (sub: any) => {
  if (!sub) return { active: false, text: "نامشخص" };
  const endDate = sub.end_date ? new Date(sub.end_date) : null;
  const now = new Date();
  const isExpired = endDate ? endDate.getTime() < now.getTime() : false;
  if (sub.status === "active" && !isExpired) return { active: true, text: "فعال" };
  return { active: false, text: "منقضی" };
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [sub, setSub] = useState<any>(null);
  const [ticketStats, setTicketStats] = useState<any>(null);
  
  const [showForm, setShowForm] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string>("3_months");
  const [note, setNote] = useState("");
  const [paymentTime, setPaymentTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

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

    fetch(`${apiUrl}/tickets/stats`, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch stats");
      return res.json();
    })
    .then(data => setTicketStats(data))
    .catch(err => {
      console.warn("Ticket stats fetch failed:", err);
      setTicketStats({ open_count: 0, closed_count: 0, unread_count: 0, total_count: 0 });
    });
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
          full_name: newName, email: newEmail || undefined,
          old_password: oldPassword || undefined, new_password: newPassword || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا در ذخیره");
      setUser(data.user); setUserData(data.user); setIsEditOpen(false);
      setOldPassword(""); setNewPassword(""); setConfirmPassword("");
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
      setSuccess(true); setShowForm(false);
    } catch (err: any) { alert(err.message); } finally { setLoading(false); }
  };

  if (!user) return <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">در حال بارگذاری...</div>;
  const subStatus = getSubStatus(sub);
  const displayName = user.full_name || user.phone;

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-6 max-w-5xl space-y-6">
        
        {/* هدر خوش‌آمدگویی */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-white truncate">
                خوش آمدی، <span className="text-[#d6ad60]">{displayName}</span> 👋
              </h1>
              <p className="text-gray-400 mt-1 text-xs sm:text-sm">امروز چه خبر؟ بازار منتظرته.</p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Link href="/">
                <Button variant="outline" size="icon" className="h-9 w-9 border-white/10 text-gray-300 hover:bg-white/5">
                  <Home className="h-4 w-4" />
                </Button>
              </Link>
              <Button variant="destructive" size="icon" onClick={handleLogout} className="h-9 w-9">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>

        {/* کارت وضعیت اشتراک */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="relative overflow-hidden rounded-3xl border border-[#d6ad60]/30 bg-gradient-to-r from-[#0d1b2d] via-[#14263e] to-[#07111f] p-5 sm:p-6 shadow-2xl">
          <div className="absolute -top-10 -right-10 p-4 opacity-5"><Crown className="h-48 w-48 text-[#d6ad60]" /></div>
          
          <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2 w-full sm:w-auto">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#d6ad60]/10 border border-[#d6ad60]/20 text-[#d6ad60]">
                <Crown className="h-3.5 w-3.5" />
                <span className="text-[10px] sm:text-xs font-bold">وضعیت اشتراک شما</span>
              </div>
              
              {sub ? (
                <div className="space-y-1">
                  <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2 flex-wrap">
                    {sub.plan === "free" ? <Gift className="h-5 w-5 text-[#d6ad60]" /> : <ShieldCheck className="h-5 w-5 text-green-400" />}
                    {getPlanNameFa(sub.plan)}
                    {sub.plan === "free" && <span className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full font-bold">۳ روز رایگان</span>}
                    <span className={`inline-block h-2 w-2 rounded-full ${subStatus.active ? "bg-green-500 shadow-[0_0_8px_#22c55e]" : "bg-red-500 shadow-[0_0_8px_#ef4444]"}`} />
                  </h2>
                  <div className="flex items-center gap-2 text-xs sm:text-sm text-gray-400">
                    <Clock className="h-3.5 w-3.5" />
                    <span>تاریخ انقضا: {sub.end_date ? new Date(sub.end_date).toLocaleDateString('fa-IR') : "نامحدود"}</span>
                  </div>
                </div>
              ) : (
                <h2 className="text-xl sm:text-2xl font-bold text-white">در حال دریافت...</h2>
              )}
            </div>
            
            {!showForm && !success && (
              <Button onClick={() => setShowForm(true)} className="h-11 sm:h-12 px-5 sm:px-6 gap-2 text-sm sm:text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90 shadow-lg shadow-[#d6ad60]/20 w-full sm:w-auto shrink-0 transition-transform hover:scale-[1.02]">
                <Zap className="h-4 w-4 sm:h-5 sm:w-5" /> ارتقا / تمدید
              </Button>
            )}
          </div>

          <AnimatePresence>
            {success ? (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="relative z-10 mt-6 flex items-center gap-2 text-green-500 bg-green-500/10 p-4 rounded-xl border border-green-500/20">
                <CheckCircle2 className="h-5 w-5 shrink-0" />
                <span className="text-xs sm:text-sm">درخواست شما ثبت شد. پس از تایید ادمین، اشتراک فعال می‌شود.</span>
              </motion.div>
            ) : showForm ? (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="relative z-10 mt-5 space-y-4 bg-black/20 p-4 sm:p-5 rounded-2xl border border-white/10">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-base sm:text-lg text-[#d6ad60]">ارتقا به نسخه حرفه‌ای</h3>
                  <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white"><X className="h-5 w-5" /></button>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
                  {PLANS.map((plan) => (
                    <button key={plan.id} onClick={() => setSelectedPlan(plan.id)} className={`relative p-3 sm:p-4 rounded-xl border-2 text-right transition-all ${selectedPlan === plan.id ? "border-[#d6ad60] bg-[#d6ad60]/10 shadow-md" : "border-white/10 hover:border-[#d6ad60]/50 hover:bg-white/5"}`}>
                      {plan.popular && (
                        <span className="absolute -top-2.5 right-3 bg-orange-500 text-white text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                          <Sparkles className="h-2.5 w-2.5" /> پرفروش‌ترین
                        </span>
                      )}
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-xs sm:text-sm text-white">{plan.title}</span>
                        {plan.discount > 0 && (<span className="text-[10px] bg-green-500/20 text-green-500 px-1.5 py-0.5 rounded-full font-bold">{plan.discount}%</span>)}
                      </div>
                      <div className="flex items-baseline gap-1.5 mt-1">
                        <span className="font-bold text-sm sm:text-lg text-white">{plan.price.toLocaleString('fa-IR')}</span>
                        <span className="text-[10px] sm:text-xs text-gray-400">تومان</span>
                      </div>
                      {plan.oldPrice > 0 && (<div className="text-[10px] sm:text-xs text-red-400/80 line-through mt-0.5">{plan.oldPrice.toLocaleString('fa-IR')} تومان</div>)}
                    </button>
                  ))}
                </div>

                <div className="bg-black/30 border border-white/10 rounded-xl p-3 sm:p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="text-center sm:text-right w-full">
                    <div className="text-[10px] sm:text-xs text-[#d6ad60] mb-1 flex items-center gap-1 justify-center sm:justify-start"><ShieldCheck className="h-3 w-3" /> پرداخت با هماهنگی (کارت به کارت)</div>
                    <div className="font-mono text-sm sm:text-lg dir-ltr tracking-wider text-white">{CARD_NUMBER}</div>
                    <div className="text-[10px] sm:text-xs text-gray-400 mt-0.5">به نام: {CARD_HOLDER}</div>
                  </div>
                  <Button variant="outline" size="icon" onClick={copyCard} className="shrink-0 h-10 w-10 sm:h-12 sm:w-12 rounded-full border-white/20 text-[#d6ad60] hover:bg-[#d6ad60]/10">
                    {copied ? <CheckCircle2 className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" /> : <Copy className="h-4 w-4 sm:h-5 sm:w-5" />}
                  </Button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
                  <div className="space-y-1.5">
                    <label className="text-[10px] sm:text-xs text-gray-400">زمان واریز (اختیاری)</label>
                    <Input placeholder="۱۴:۳۰ - ۱۴۰۳/۰۸/۰۳" value={paymentTime} onChange={(e) => setPaymentTime(e.target.value)} className="h-10 sm:h-12 bg-black/30 border-white/10 text-white text-sm" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] sm:text-xs text-gray-400">کد پیگیری (اختیاری)</label>
                    <Input placeholder="۱۲۳۴" value={note} onChange={(e) => setNote(e.target.value)} className="h-10 sm:h-12 bg-black/30 border-white/10 text-white text-center text-sm" />
                  </div>
                </div>

                <div className="flex gap-2 sm:gap-3 pt-1">
                  <Button onClick={handleRequest} disabled={loading} className="flex-1 h-10 sm:h-12 text-xs sm:text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90">
                    {loading ? "در حال ارسال..." : "ثبت درخواست"}
                  </Button>
                  <Button variant="outline" onClick={() => setShowForm(false)} className="h-10 sm:h-12 border-white/20 text-white hover:bg-white/10 text-xs sm:text-sm">انصراف</Button>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </motion.div>

        {/* کارت افزونه کروم */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-4 sm:p-5 transition-all hover:border-[#d6ad60]/40">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#d6ad60]/10 rounded-bl-full blur-2xl group-hover:bg-[#d6ad60]/20 transition-all" />
            
            <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-3 w-full">
                <div className="bg-[#d6ad60]/10 p-2.5 sm:p-3 rounded-xl text-[#d6ad60] shrink-0 mt-1">
                  <Zap className="h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <div>
                  <p className="font-bold text-sm sm:text-base">افزونه کروم (Extension) نوسان‌گیر لحظه‌ای تریدمون</p>
                  <p className="text-[10px] sm:text-xs text-gray-400 mt-1 leading-relaxed text-justify">
                    مخصوص صرافی‌های <b>دریا گلد</b> و <b>آلفا گلد</b>. این صرافی‌ها روی <b>انس طلا (XAU/USD)</b> معاملات تعهدی (مارجین) ارائه می‌دهند. افزونه با اتصال به WebSocket داخلی این صرافی‌ها، قیمت‌ها را بدون دستکاری در حساب شما دریافت کرده و تحلیل تکنیکال لحظه‌ای ارائه می‌دهد. <br />
                    <span className="text-red-400/80 text-[9px] mt-1 block">⚠️ تصمیم‌گیری نهایی و مسئولیت معاملات با شماست.</span>
                  </p>
                </div>
              </div>
              <div className="flex gap-2 w-full md:w-auto shrink-0 mt-3 md:mt-0">
                <Link href="/extension/guide" className="flex-1 md:flex-none">
                  <Button variant="outline" className="w-full border-white/10 text-gray-300 hover:bg-white/5 text-xs sm:text-sm h-9 gap-2">
                    <BookOpen className="h-4 w-4" /> راهنما
                  </Button>
                </Link>
                <a href="/downloads/trademun-extension.zip" target="_blank" rel="noreferrer" className="flex-1 md:flex-none" download>
                  <Button className="w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] text-xs sm:text-sm font-bold h-9 gap-2">
                    <Download className="h-4 w-4" /> دانلود افزونه
                  </Button>
                </a>
              </div>
            </div>
          </div>
        </motion.div>

        {/* کارت اطلاعات حساب */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4 sm:p-6 shadow-xl">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <h2 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
              <UserIcon className="h-4 w-4 sm:h-5 sm:w-5 text-[#d6ad60]" /> اطلاعات حساب
            </h2>
            <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
              <button onClick={() => setIsEditOpen(true)} className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-transparent px-2.5 sm:px-3 text-[10px] sm:text-xs font-medium text-gray-300 transition-colors hover:bg-white/5 hover:text-white">
                <Pencil className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> ویرایش
              </button>
              <DialogContent className="sm:max-w-[425px] bg-[#0d1b2d] border-white/10 text-white">
                <DialogHeader>
                  <DialogTitle className="text-[#d6ad60] text-base sm:text-lg">ویرایش پروفایل</DialogTitle>
                </DialogHeader>
                <div className="space-y-3 sm:space-y-4 pt-3 sm:pt-4">
                  <div>
                    <label className="text-[10px] sm:text-xs text-gray-400 mb-1 block">نام نمایشی</label>
                    <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="نام جدید" className="bg-black/30 border-white/10 text-sm" />
                  </div>
                  <div>
                    <label className="text-[10px] sm:text-xs text-gray-400 mb-1 block">ایمیل</label>
                    <Input value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="example@email.com" dir="ltr" className="bg-black/30 border-white/10 text-center text-sm" />
                  </div>
                  <div className="border-t border-white/10 pt-3 sm:pt-4 space-y-2 sm:space-y-3">
                    <h3 className="text-xs sm:text-sm font-bold text-[#d6ad60]">تغییر رمز عبور</h3>
                    {user?.hashed_password && (
                      <div>
                        <label className="text-[10px] sm:text-xs text-gray-400 mb-1 block">رمز فعلی</label>
                        <Input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} placeholder="رمز فعلی" dir="ltr" className="bg-black/30 border-white/10 text-center text-sm" />
                      </div>
                    )}
                    <div>
                      <label className="text-[10px] sm:text-xs text-gray-400 mb-1 block">رمز جدید</label>
                      <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="حداقل ۶ حرف" dir="ltr" className="bg-black/30 border-white/10 text-center text-sm" />
                    </div>
                    <div>
                      <label className="text-[10px] sm:text-xs text-gray-400 mb-1 block">تکرار رمز</label>
                      <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="تکرار رمز" dir="ltr" className="bg-black/30 border-white/10 text-center text-sm" />
                    </div>
                  </div>
                  <Button onClick={handleUpdateProfile} disabled={editLoading} className="w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold text-sm h-10 sm:h-11">
                    {editLoading ? "در حال ذخیره..." : "ذخیره تغییرات"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
          
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            {/* 👈 این باکس تغییر کرد که اسم هم داخلش باشه */}
            <div className="flex items-center gap-2 sm:gap-3 rounded-xl bg-white/5 p-2 sm:p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-1.5 sm:p-2 rounded-lg text-[#d6ad60]"><UserIcon className="h-3.5 w-3.5 sm:h-4 sm:w-4" /></div>
              <div className="min-w-0 flex flex-col">
                <p className="text-[9px] sm:text-[10px] text-gray-400">نام</p>
                <p className="text-xs sm:text-sm text-white truncate">{user.full_name || "ثبت نشده"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 rounded-xl bg-white/5 p-2 sm:p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-1.5 sm:p-2 rounded-lg text-[#d6ad60]"><Mail className="h-3.5 w-3.5 sm:h-4 sm:w-4" /></div>
              <div className="min-w-0">
                <p className="text-[9px] sm:text-[10px] text-gray-400">ایمیل</p>
                <p className="text-xs sm:text-sm text-white truncate" dir="ltr">{user.email || "ثبت نشده"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 rounded-xl bg-white/5 p-2 sm:p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-1.5 sm:p-2 rounded-lg text-[#d6ad60]"><Lock className="h-3.5 w-3.5 sm:h-4 sm:w-4" /></div>
              <div className="min-w-0">
                <p className="text-[9px] sm:text-[10px] text-gray-400">رمز عبور</p>
                <p className={`text-xs sm:text-sm ${user.hashed_password ? "text-green-500" : "text-yellow-500"}`}>{user.hashed_password ? "تعیین شده" : "تعیین نشده"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 rounded-xl bg-white/5 p-2 sm:p-3 border border-white/5">
              <div className="bg-[#d6ad60]/10 p-1.5 sm:p-2 rounded-lg text-[#d6ad60]"><UserIcon className="h-3.5 w-3.5 sm:h-4 sm:w-4" /></div>
              <div className="min-w-0">
                <p className="text-[9px] sm:text-[10px] text-gray-400">موبایل</p>
                <p className="text-xs sm:text-sm text-white font-mono dir-ltr truncate">{user.phone}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* شبکه ارتباطی و پشتیبانی */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="grid grid-cols-1 md:grid-cols-3 gap-3">
          
          {/* تیکت پشتیبانی */}
          <Link href="/dashboard/tickets" className="block">
            <div className="group relative overflow-hidden rounded-2xl border-2 border-[#d6ad60]/40 bg-gradient-to-br from-[#1a2c45] to-[#07111f] p-4 h-full transition-all hover:border-[#d6ad60] hover:scale-[1.02]">
              <div className="absolute top-0 right-0 w-24 h-24 bg-[#d6ad60]/20 rounded-bl-full blur-xl group-hover:bg-[#d6ad60]/30 transition-all" />
              <div className="relative flex items-start gap-3 h-full">
                <div className="relative bg-[#d6ad60] p-2.5 rounded-xl text-[#101827] shrink-0 shadow-lg shadow-[#d6ad60]/20">
                  <MessageSquare className="h-5 w-5" />
                  {ticketStats?.unread_count > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white animate-pulse">
                      {ticketStats.unread_count}
                    </span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-bold text-sm">تیکت پشتیبانی</p>
                  <p className="text-[10px] text-gray-300 mt-1 font-medium">
                    {ticketStats?.open_count > 0 ? `${ticketStats.open_count} تیکت باز داری` : "پاسخگویی سریع به سوالات شما"}
                  </p>
                </div>
              </div>
            </div>
          </Link>

          {/* کانال‌ها */}
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-4 flex flex-col justify-center">
            <p className="font-bold text-sm mb-2 text-gray-200">کانال‌های رسمی</p>
            <div className="flex flex-col gap-2">
              <a href="https://t.me/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-xs text-gray-400 hover:text-[#d6ad60] transition-colors">
                <Send className="h-3.5 w-3.5" /> کانال تلگرام (ارسال خودکار سیگنال‌های لحظه‌ای)
              </a>
              <a href="https://ble.ir/trademun" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-xs text-gray-400 hover:text-[#d6ad60] transition-colors">
                <Send className="h-3.5 w-3.5" /> کانال بله (ارسال خودکار سیگنال‌های لحظه‌ای)
              </a>
            </div>
          </div>

          {/* ربات هوشمند (به زودی) */}
          <div className="rounded-2xl border border-white/10 border-dashed bg-white/5 p-4 flex flex-col justify-center relative overflow-hidden opacity-70">
            <div className="absolute top-2 left-2 bg-yellow-500/20 text-yellow-500 text-[9px] px-1.5 py-0.5 rounded font-bold">به زودی</div>
            <p className="font-bold text-sm mb-2 text-gray-200 flex items-center gap-1.5">
              <Bot className="h-4 w-4" /> ربات هوشمند اختصاصی
            </p>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              دریافت سیگنال‌های شخصی‌سازی شده و تعامل هوشمند در تلگرام و بله.
            </p>
          </div>

        </motion.div>

      </main>
      <Footer />
    </div>
  );
}