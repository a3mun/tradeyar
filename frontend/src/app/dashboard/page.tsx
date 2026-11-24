"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken, setUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import { InstallAppCard } from "@/components/pwa/InstallAppCard";
import {
  LogOut, CheckCircle2, Pencil, MessageSquare,
  Home, Mail, Lock, User as UserIcon, Crown, Clock, Zap,
  Download, BookOpen, Gift, AlertTriangle, ArrowRight,
  Puzzle, Hourglass, Wallet, CreditCard, History, XCircle,
  Receipt, LayoutDashboard, UserCircle, RefreshCw, Calendar,
  TrendingUp, CalendarDays
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Link from "next/link";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    free: "پلن آشنایی رایگان", "1_month": "اشتراک یک ماهه", "3_months": "اشتراک سه ماهه",
    "6_months": "اشتراک شش ماهه", "12_months": "اشتراک یک ساله",
    "نامحدود (مدیر)": "نامحدود (مدیر)", refund: "عودت وجه", no_change: "بدون تغییر (فقط عودت وجه)",
  };
  return map[plan] || plan || "نامشخص";
};

const getPaymentStatus = (status: string) => {
  switch (status) {
    case "approved": return { text: "تایید شده", color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30", icon: CheckCircle2 };
    case "pending": return { text: "در حال بررسی", color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/30", icon: Hourglass };
    case "rejected": return { text: "رد شده", color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30", icon: XCircle };
    case "refunded": return { text: "عودت شده", color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/30", icon: RefreshCw };
    default: return { text: status, color: "text-gray-400", bg: "bg-white/5", border: "border-white/10", icon: History };
  }
};

const getPaymentMethodFa = (method: string | null | undefined) => {
  if (!method) return "—";
  if (method === "zibal") return "درگاه زیبال";
  if (method === "card") return "کارت به کارت";
  if (method === "refund") return "عودت وجه";
  return method;
};

const PENDING_KEY = "trademun_pending_request";
const EXTENSION_VERSION = "7.1.0";
const EXTENSION_UPDATED_AT = "1405/08/17";

type TabKey = "dashboard" | "financial" | "account";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [sub, setSub] = useState<any>(null);
  const [allSubs, setAllSubs] = useState<any[]>([]);
  const [ticketStats, setTicketStats] = useState<any>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [txLoading, setTxLoading] = useState(true);
  const [subsLoading, setSubsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [swipeDirection, setSwipeDirection] = useState<1 | -1>(1);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [hasPassword, setHasPassword] = useState(false);

  const [isUserTxDetailOpen, setIsUserTxDetailOpen] = useState(false);
  const [selectedUserTx, setSelectedUserTx] = useState<any>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  // 🔴 تشخیص درخواست در حال بررسی
  const hasPendingTransaction = useMemo(() => {
    const localPending = typeof window !== "undefined" && localStorage.getItem(PENDING_KEY) === "true";
    const zibalPending = transactions.some((tx) => tx.payment_method === "zibal" && tx.status === "pending");
    return localPending || zibalPending;
  }, [transactions]);

  const pendingTransaction = useMemo(() => {
    return transactions.find((tx) => tx.status === "pending");
  }, [transactions]);

  // 🔴 ref برای سوایپ
  const touchStartX = useRef<number | null>(null);
  const touchEndX = useRef<number | null>(null);
  const minSwipeDistance = 50;

  useEffect(() => {
    const u = getUser();
    if (!u) { router.replace("/login"); return; }
    setUserData(u);
    setNewName(u.full_name || "");
    setNewEmail(u.email || "");

    fetch(`${apiUrl}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.user) {
          setUser(data.user);
          setUserData(data.user);
          setHasPassword(!!data.user.has_password);
        }
      }).catch(console.error);

    fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.json())
      .then((data) => {
        setSub(data.subscription);
        if (data.subscription?.status === "active" && typeof window !== "undefined") {
          localStorage.removeItem(PENDING_KEY);
        }
      }).catch((err) => console.error(err));

    fetch(`${apiUrl}/tickets/stats`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.ok ? res.json() : { open_count: 0, closed_count: 0, unread_count: 0, total_count: 0 })
      .then((data) => setTicketStats(data))
      .catch(() => setTicketStats({ open_count: 0, closed_count: 0, unread_count: 0, total_count: 0 }));

    fetch(`${apiUrl}/subscription/history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : { items: [] }))
      .then((data) => setAllSubs(data.items || []))
      .catch(() => setAllSubs([]))
      .finally(() => setSubsLoading(false));

    fetch(`${apiUrl}/subscription/my-transactions`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : { items: [] }))
      .then((data) => setTransactions(data.items || []))
      .catch(() => setTransactions([]))
      .finally(() => setTxLoading(false));
  }, [router, apiUrl, token]);

  // Refresh subscription status while the dashboard stays open.
  // The API synchronizes a due reservation when these endpoints are read.
  useEffect(() => {
    if (!token) return;
    const refreshSubscription = async () => {
      try {
        const [currentRes, historyRes] = await Promise.all([
          fetch(`${apiUrl}/subscription/my`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }),
          fetch(`${apiUrl}/subscription/history`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }),
        ]);
        if (currentRes.ok) {
          const currentData = await currentRes.json();
          setSub(currentData.subscription || null);
        }
        if (historyRes.ok) {
          const historyData = await historyRes.json();
          setAllSubs(historyData.items || []);
        }
      } catch {
        // Retain the last known state on transient network failures.
      }
    };
    const timer = window.setInterval(refreshSubscription, 60000);
    return () => window.clearInterval(timer);
  }, [apiUrl, token]);

  // 🔴 polling تراکنش‌ها هر ۳۰ ثانیه
  useEffect(() => {
    if (!token) return;
    const interval = setInterval(() => {
      fetch(`${apiUrl}/subscription/my-transactions`, { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => (res.ok ? res.json() : { items: [] }))
        .then((data) => setTransactions(data.items || []))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [apiUrl, token]);

  const handleLogout = () => { removeToken(); router.replace("/login"); };

  const handleDownload = async () => {
    if (!token) { setDownloadError("لطفاً ابتدا وارد حساب کاربری خود شوید."); return; }
    try {
      const res = await fetch(`${apiUrl}/extension/download`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      if (!res.ok) {
        const data = await res.json();
        setDownloadError(data.detail || "برای دانلود افزونه، نیاز به اشتراک حرفه‌ای (Pro) دارید.");
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "trademun-extension.zip"; a.click();
      window.URL.revokeObjectURL(url);
    } catch { setDownloadError("خطا در ارتباط با سرور"); }
  };

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
        body: JSON.stringify({ full_name: newName, email: newEmail || undefined, new_password: newPassword || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا در ذخیره");
      setUser(data.user); setUserData(data.user); setHasPassword(!!data.user.has_password);
      setIsEditOpen(false); setNewPassword(""); setConfirmPassword("");
    } catch (err: any) { alert(err.message); }
    finally { setEditLoading(false); }
  };

  const subStatus = useMemo(() => {
    if (!sub) return { active: false, text: "نامشخص", daysLeft: null };
    const now = new Date();
    const startDate = sub.start_date ? new Date(sub.start_date) : null;
    const endDate = sub.end_date ? new Date(sub.end_date) : null;
    const isExpired = endDate ? endDate.getTime() <= now.getTime() : false;
    const isReserved =
      !isExpired &&
      (sub.status === "reserved" ||
        (startDate !== null && startDate.getTime() > now.getTime()));
    if (isReserved) {
      const daysUntilStart = startDate
        ? Math.max(0, Math.ceil((startDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
        : null;
      return { active: false, text: "در انتظار شروع", daysLeft: daysUntilStart };
    }
    if (sub.status === "active" && !isExpired) {
      const daysLeft = endDate ? Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)) : null;
      return { active: true, text: "فعال", daysLeft };
    }
    return { active: false, text: "منقضی", daysLeft: 0 };
  }, [sub]);

  const { activeSubs, reservedSubs, expiredSubs } = useMemo(() => {
    const now = new Date();
    const active: any[] = [];
    const reserved: any[] = [];
    const expired: any[] = [];

    allSubs.forEach((s) => {
      const endDate = s.end_date ? new Date(s.end_date) : null;
      const startDate = s.start_date ? new Date(s.start_date) : null;
      const isExpired = !!endDate && endDate.getTime() <= now.getTime();
      const isReserved =
        !isExpired &&
        (s.status === "reserved" ||
          (startDate !== null && startDate.getTime() > now.getTime()));

      if (isExpired || s.status === "expired") {
        expired.push(s);
      } else if (isReserved) {
        reserved.push(s);
      } else if (s.status === "active") {
        active.push(s);
      } else {
        expired.push(s);
      }
    });

    return { activeSubs: active, reservedSubs: reserved, expiredSubs: expired };
  }, [allSubs]);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (touchStartX.current === null || touchEndX.current === null) return;

    const distance = touchStartX.current - touchEndX.current;
    const isSwipeLeft = distance > minSwipeDistance;
    const isSwipeRight = distance < -minSwipeDistance;

    const tabs: TabKey[] = ["dashboard", "financial", "account"];
    const currentIndex = tabs.indexOf(activeTab);

    if (isSwipeLeft && currentIndex > 0) {
      setSwipeDirection(-1);
      setActiveTab(tabs[currentIndex - 1]);
    } else if (isSwipeRight && currentIndex < tabs.length - 1) {
      setSwipeDirection(1);
      setActiveTab(tabs[currentIndex + 1]);
    }

    touchStartX.current = null;
    touchEndX.current = null;
  };

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#030712] text-white">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#d6ad60]" />
      </div>
    );
  }

  const displayName = user.full_name || user.phone;

  // 🔴 انیمیشن مشترک
  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 60 : -60, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -60 : 60, opacity: 0 }),
  };

  const slideTransition = {
    duration: 0.28,
    ease: [0.32, 0.72, 0, 1] as [number, number, number, number],
    opacity: { duration: 0.2 },
  };

  return (
    <div className="relative isolate flex min-h-screen flex-col overflow-hidden bg-[#030811] text-white">
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -right-40 -top-48 h-[34rem] w-[34rem] rounded-full bg-[#b98b3d]/[0.045] blur-[140px]" />
        <div className="absolute -left-48 top-[38%] h-[30rem] w-[30rem] rounded-full bg-[#17384a]/[0.025] blur-[150px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(214,173,96,0.022),transparent_58%)]" />
      </div>
      <Header />
      <main className="container mx-auto w-full max-w-6xl flex-1 space-y-5 px-4 py-5 sm:space-y-6 sm:px-6 sm:py-7 lg:px-8">
        
        {/* ═══ هدر خوش‌آمدگویی ═══ */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-2xl border border-[#d6ad60]/14 bg-[#111a24] px-4 py-4 shadow-[0_8px_24px_rgba(0,0,0,0.20)] sm:px-5 sm:py-5">
          <div aria-hidden="true" className="pointer-events-none absolute -left-8 -top-20 h-64 w-64 rounded-full border border-[#d6ad60]/10 shadow-[0_0_0_24px_rgba(214,173,96,0.025),0_0_0_52px_rgba(214,173,96,0.018)]" />
          <div className="relative z-10 flex items-center justify-between gap-4">
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[#e7c77e]/35 bg-[#242a30] text-xl font-black text-[#f0d493] shadow-sm sm:h-12 sm:w-12 sm:text-xl">
              {(displayName || "ت").toString().trim().charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="mb-1.5 text-[10px] font-bold tracking-[0.22em] text-[#d6ad60] sm:text-xs">حساب کاربری</p>
              <h1 className="truncate text-lg font-bold tracking-tight text-white sm:text-2xl">
                {displayName}
              </h1>
              <p className="mt-1.5 hidden text-xs text-slate-400 sm:block">تریدمون نشه؟</p>
            </div>
          </div>
          <div className="relative z-10 flex shrink-0 gap-2">
            <Link href="/">
              <Button variant="outline" size="icon" className="h-10 w-10 rounded-xl border-white/10 bg-white/[0.06] text-gray-200 shadow-lg backdrop-blur hover:border-[#d6ad60]/40 hover:bg-white/10 sm:h-11 sm:w-11">
                <Home className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              </Button>
            </Link>
            <Button variant="destructive" size="icon" onClick={handleLogout} className="h-10 w-10 rounded-xl shadow-lg sm:h-11 sm:w-11">
              <LogOut className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </Button>
          </div>
          </div>
        </motion.div>

        {/* ═══ هشدار در انتظار تایید ═══ */}
        <AnimatePresence>
          {hasPendingTransaction && (
            <motion.div 
              initial={{ opacity: 0, y: -8, height: 0 }} 
              animate={{ opacity: 1, y: 0, height: "auto" }} 
              exit={{ opacity: 0, y: -8, height: 0 }}
              className="overflow-hidden"
            >
              <div className="flex items-start gap-2.5 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 sm:gap-3 sm:rounded-2xl sm:p-4">
                <div className="shrink-0 rounded-lg bg-yellow-500/10 p-1.5 sm:p-2">
                  <Hourglass className="h-4 w-4 animate-pulse text-yellow-500 sm:h-5 sm:w-5" />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-bold text-yellow-500 sm:text-sm">درخواست اشتراک شما در حال بررسی است</p>
                  <p className="mt-0.5 text-[10px] leading-relaxed text-gray-400 sm:mt-1 sm:text-[11px]">
                    {pendingTransaction?.payment_method === "zibal"
                      ? "پرداخت شما در درگاه در حال بررسی است و حداکثر ۱۵ دقیقه دیگه وضعیت آن مشخص می‌شه."
                      : "تیم پشتیبانی ظرف ۲۴ ساعت آینده درخواست شما را بررسی می‌کند."}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ═══ تب‌ها ═══ */}
        <div className="grid grid-cols-3 gap-1.5 rounded-2xl border border-white/[0.09] bg-[#0c141e]/90 p-2 shadow-[0_5px_16px_rgba(0,0,0,0.16)] backdrop-blur-xl sm:gap-2.5 sm:p-2.5">
          {[
            { id: "dashboard", label: "داشبورد", icon: LayoutDashboard },
            { id: "financial", label: "مالی", icon: Receipt },
            { id: "account", label: "حساب کاربری", icon: UserCircle },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const tabsArr: TabKey[] = ["dashboard", "financial", "account"];
            const currentIndex = tabsArr.indexOf(activeTab);
            const tabIndex = tabsArr.indexOf(tab.id as TabKey);
            
            return (
              <button 
                key={tab.id} 
                onClick={() => {
                  setSwipeDirection(tabIndex > currentIndex ? 1 : -1);
                  setActiveTab(tab.id as TabKey);
                }} 
                className={`flex min-h-11 items-center justify-center gap-2 rounded-xl px-2 py-3 text-[11px] font-bold transition-all duration-300 sm:min-h-12 sm:px-3 sm:text-[13px] ${isActive ? "bg-[#c6a15b] text-[#111720] shadow-[0_3px_10px_rgba(0,0,0,0.18)]" : "text-slate-400 hover:bg-white/[0.07] hover:text-white"}`}
              >
                <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ═══ محتوای تب‌ها با سوایپ ═══ */}
        <div 
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          className="touch-pan-y"
        >
          <AnimatePresence mode="wait" custom={swipeDirection} initial={false}>
            {activeTab === "dashboard" && (
              <motion.div 
                key="dashboard" 
                custom={swipeDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slideTransition}
                className="space-y-4 sm:space-y-5"
              >
                
                {/* بنر اشتراک فعال */}
                {sub && (
                  <div className="relative overflow-hidden rounded-2xl border border-[#d6ad60]/16 bg-[#111a24] p-4 shadow-[0_8px_24px_rgba(0,0,0,0.18)] sm:p-5">
                    <div className="absolute -right-10 -top-10 p-4 opacity-5">
                    </div>
                    <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
                      <div className="flex items-center gap-2.5 sm:gap-3">
                        <div className="shrink-0 rounded-xl bg-[#d6ad60]/[0.07] p-2.5 border border-[#d6ad60]/14 sm:p-3">
                          {sub.plan === "free" ? <Gift className="h-5 w-5 text-[#d6ad60] sm:h-6 sm:w-6" /> : <Crown className="h-5 w-5 text-[#d6ad60] sm:h-6 sm:w-6" />}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h2 className="text-sm font-bold text-white sm:text-base">{getPlanNameFa(sub.plan)}</h2>
                            <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-bold sm:px-2 sm:text-[10px] ${subStatus.active ? "bg-green-500/10 text-green-400 border border-green-500/20" : subStatus.text === "در انتظار شروع" ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                              <span className={`h-1 w-1 rounded-full sm:h-1.5 sm:w-1.5 ${subStatus.active ? "bg-green-500 animate-pulse" : subStatus.text === "در انتظار شروع" ? "bg-yellow-500" : "bg-red-500"}`} />
                              {subStatus.text}
                            </span>
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-gray-400 sm:mt-1.5 sm:gap-3 sm:text-[11px]">
                            <span className="flex items-center gap-1"><Calendar className="h-2.5 w-2.5 sm:h-3 sm:w-3" /> شروع: {sub.start_date ? new Date(sub.start_date).toLocaleDateString("fa-IR") : "—"}</span>
                            <span className="flex items-center gap-1"><CalendarDays className="h-2.5 w-2.5 sm:h-3 sm:w-3" /> پایان: {sub.end_date ? new Date(sub.end_date).toLocaleDateString("fa-IR") : "نامحدود"}</span>
                            {subStatus.daysLeft != null && subStatus.daysLeft > 0 && (
                              <span className="flex items-center gap-1 text-[#d6ad60] font-bold"><TrendingUp className="h-2.5 w-2.5 sm:h-3 sm:w-3" /> {subStatus.daysLeft} روز</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <Link href="/subscription" className="w-full sm:w-auto sm:min-w-[130px]">
                        <Button className="h-10 w-full sm:h-11 gap-2 bg-[#c6a15b] hover:bg-[#d0ad6c] text-[#030712] font-bold shadow-none text-sm px-5">
                          <Zap className="h-4 w-4" /> {subStatus.active ? "تمدید اشتراک" : subStatus.text === "در انتظار شروع" ? "مشاهده اشتراک" : "خرید اشتراک"}
                        </Button>
                      </Link>
                    </div>
                  </div>
                )}

                {/* کارت افزونه */}
                <div className="group relative overflow-hidden rounded-2xl border border-white/[0.09] bg-[#101923] p-4 shadow-[0_6px_20px_rgba(0,0,0,0.16)] sm:p-5">
                  <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-bl-full bg-[#d6ad60]/[0.035] blur-2xl" />
                  <div className="relative flex flex-col items-start justify-between gap-3 md:flex-row md:items-center sm:gap-4">
                    <div className="flex w-full items-start gap-2.5 md:min-w-0 md:flex-1 sm:gap-3">
                      <div className="shrink-0 rounded-xl border border-[#d6ad60]/14 bg-[#d6ad60]/[0.07] p-2 text-[#d6ad60] sm:p-3">
                        <Puzzle className="h-4 w-4 sm:h-6 sm:w-6" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-xs font-bold text-white sm:text-base">افزونه کروم تریدمون</p>
                        </div>
                        <p className="mt-1 text-[10px] leading-relaxed text-gray-400 sm:text-xs">
                          تحلیل لحظه‌ای <b className="text-gray-200">XAU/USD</b> در صرافی‌های دریا گلد و آلفا گلد.
                        </p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[8px] text-gray-500 sm:mt-2 sm:text-[10px]">
                          <span className="inline-flex items-center gap-1.5">
                            <span className="rounded border border-[#d6ad60]/14 bg-[#d6ad60]/[0.07] px-1.5 py-0.5 font-mono text-[9px] font-bold text-[#d6ad60] sm:px-2 sm:text-[10px]">v.{EXTENSION_VERSION}</span>
                            <span className="text-gray-500">نسخه</span>
                          </span>
                          <span className="text-gray-700">·</span>
                          <span className="inline-flex items-center gap-1.5">
                            <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[9px] font-bold text-gray-400 sm:px-2 sm:text-[10px]">{EXTENSION_UPDATED_AT}</span>
                            <span className="text-gray-500">آخرین آپدیت</span>
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex w-full flex-row gap-2 md:w-auto md:shrink-0">
                      <Link href="/extension/guide" className="flex-1 md:flex-none">
                        <Button 
                          variant="outline" 
                          className="h-9 w-full md:w-auto gap-1.5 border-white/10 px-3 text-[11px] text-gray-300 hover:border-[#d6ad60]/40 hover:bg-white/5 whitespace-nowrap sm:h-10 sm:gap-2 sm:px-4 sm:text-sm"
                        >
                          <BookOpen className="h-3.5 w-3.5 shrink-0 sm:h-4 sm:w-4" /> راهنما
                        </Button>
                      </Link>
                      <Button 
                        onClick={handleDownload} 
                        className="flex-1 md:flex-none h-9 w-full md:w-auto gap-1.5 bg-[#c6a15b] hover:bg-[#d0ad6c] px-3 text-[11px] font-bold text-[#030712] shadow-none whitespace-nowrap sm:h-10 sm:gap-2 sm:px-4 sm:text-sm"
                      >
                        <Download className="h-3.5 w-3.5 shrink-0 sm:h-4 sm:w-4" /> دانلود
                      </Button>
                    </div>
                  </div>
                </div>

                {/* کارت PWA */}
                <InstallAppCard />

              </motion.div>
            )}

            {/* ═══ تب مالی ═══ */}
            {activeTab === "financial" && (
              <motion.div 
                key="financial" 
                custom={swipeDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slideTransition}
                className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5"
              >
                
                {/* ─── ستون ۱: تراکنش‌های مالی ─── */}
                <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-4 shadow-[0_6px_20px_rgba(0,0,0,0.16)] sm:p-5">
                  <div className="mb-3 flex items-center justify-between sm:mb-4">
                    <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-white sm:text-base">
                      <Receipt className="h-4 w-4 text-[#d6ad60] sm:h-5 sm:w-5" /> تراکنش‌های مالی
                    </h2>
                    <span className="rounded-full border border-white/10 bg-white/5 px-1.5 py-0.5 text-[9px] text-gray-500 sm:px-2 sm:text-[10px]">{transactions.length}</span>
                  </div>
                  
                  {txLoading ? (
                    <div className="flex justify-center py-6 sm:py-8"><div className="h-5 w-5 sm:h-6 sm:w-6 animate-spin rounded-full border-b-2 border-t-2 border-[#d6ad60]"></div></div>
                  ) : transactions.length === 0 ? (
                    <div className="rounded-2xl border border-white/[0.08] bg-[#09131d] py-6 sm:py-8 text-center">
                      <History className="mx-auto mb-2 h-7 w-7 text-gray-600 sm:h-8 sm:w-8" />
                      <p className="text-xs text-gray-400 sm:text-sm">هنوز تراکنشی ثبت نکرده‌اید.</p>
                    </div>
                  ) : (
                    <div className="max-h-[500px] space-y-1.5 overflow-y-auto pr-1 sm:space-y-2">
                      {transactions.map((tx: any) => {
                        const st = getPaymentStatus(tx.status);
                        const StatusIcon = st.icon;
                        const MethodIcon = tx.payment_method === "zibal" ? Wallet : tx.payment_method === "refund" ? RefreshCw : CreditCard;
                        const isRefund = tx.payment_method === "refund" || tx.plan === "refund";
                        const cardBg = isRefund ? "bg-purple-500/5 border-purple-500/20" : "bg-black/20 border-white/5 hover:border-[#d6ad60]/14";
                        
                        return (
                          <div key={tx.id} className={`flex cursor-pointer items-center justify-between gap-2 rounded-xl border p-2.5 transition-colors sm:gap-3 sm:p-3 ${cardBg}`} onClick={() => { setSelectedUserTx(tx); setIsUserTxDetailOpen(true); }}>
                            <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
                              <div className={`shrink-0 rounded-lg p-1.5 sm:p-2 ${isRefund ? "bg-purple-500/10" : st.bg + " " + st.border}`}>
                                <StatusIcon className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${isRefund ? "text-purple-400" : st.color}`} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                                  <p className={`text-[11px] font-bold sm:text-xs ${isRefund ? "text-purple-400" : "text-white"}`}>{getPlanNameFa(tx.plan)}</p>
                                  <span className={`rounded-full px-1 py-0.5 text-[8px] font-bold sm:px-1.5 sm:text-[9px] ${isRefund ? "border-purple-500/20 bg-purple-500/10 text-purple-400" : st.bg + " " + st.color + " " + st.border}`}>{st.text}</span>
                                </div>
                                {isRefund && <p className="mt-1 text-[9px] font-medium text-purple-300">{tx.stage_label || (tx.source === "refund_request" ? "درخواست عودت وجه توسط کاربر" : "عودت وجه توسط مدیر")}</p>}
                                <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[9px] text-gray-400 sm:mt-1 sm:gap-3 sm:text-[10px]">
                                  <span className="flex items-center gap-1"><MethodIcon className="h-2.5 w-2.5 sm:h-3 sm:w-3" />{getPaymentMethodFa(tx.payment_method)}</span>
                                  <span className="flex items-center gap-1"><Clock className="h-2.5 w-2.5 sm:h-3 sm:w-3" />{new Date(tx.created_at).toLocaleDateString("fa-IR")}</span>
                                </div>
                              </div>
                            </div>
                            <div className="shrink-0 text-left">
                              <p className={`text-[11px] font-bold sm:text-sm ${isRefund ? "text-purple-400" : "text-white"}`} dir="ltr">{(tx.amount || 0).toLocaleString("fa-IR")}<span className="mr-1 text-[8px] text-gray-400 sm:text-[10px]">ت</span></p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* ─── ستون ۲: تاریخچه اشتراک ─── */}
                <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-4 shadow-[0_6px_20px_rgba(0,0,0,0.16)] sm:p-5">
                  <h2 className="mb-3 font-display flex items-center gap-2 text-sm font-semibold text-white sm:mb-4 sm:text-base">
                    <Crown className="h-4 w-4 text-[#d6ad60] sm:h-5 sm:w-5" /> تاریخچه اشتراک
                  </h2>
                  
                  {subsLoading ? (
                    <div className="flex justify-center py-6 sm:py-8"><div className="h-5 w-5 sm:h-6 sm:w-6 animate-spin rounded-full border-b-2 border-t-2 border-[#d6ad60]"></div></div>
                  ) : allSubs.length === 0 ? (
                    <div className="rounded-2xl border border-white/[0.08] bg-[#09131d] py-8 text-center">
                      <Crown className="mx-auto mb-2 h-8 w-8 text-gray-600 sm:h-10 sm:w-10" />
                      <p className="text-xs text-gray-400 mb-3">هنوز اشتراکی نخریده‌اید.</p>
                      <Link href="/subscription">
                        <Button className="h-9 gap-2 bg-[#c6a15b] hover:bg-[#d0ad6c] text-[#030712] font-bold text-xs">
                          <Zap className="h-3.5 w-3.5" /> خرید اشتراک
                        </Button>
                      </Link>
                    </div>
                  ) : (
                    <div className="max-h-[500px] overflow-y-auto pr-1 space-y-3 sm:space-y-4">
                      {/* فعال */}
                      {activeSubs.length > 0 && (
                        <div>
                          <h3 className="mb-1.5 text-[10px] font-bold text-green-400 flex items-center gap-1.5 sm:mb-2 sm:text-xs">
                            <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> فعال ({activeSubs.length})
                          </h3>
                          <div className="space-y-1.5 sm:space-y-2">
                            {activeSubs.map((s: any) => {
                              const endDate = s.end_date ? new Date(s.end_date) : null;
                              const daysLeft = endDate ? Math.ceil((endDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)) : null;
                              return (
                                <div key={s.id} className="rounded-xl border border-green-500/20 bg-green-500/5 p-2.5 sm:p-3">
                                  <div className="flex items-center justify-between gap-2 sm:gap-3">
                                    <div className="flex items-center gap-2 sm:gap-3">
                                      <div className="shrink-0 rounded-lg bg-green-500/10 p-1.5 sm:p-2">
                                        <Crown className="h-3.5 w-3.5 text-green-400 sm:h-4 sm:w-4" />
                                      </div>
                                      <div>
                                        <p className="text-[11px] font-bold text-white sm:text-sm">{getPlanNameFa(s.plan)}</p>
                                        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[9px] text-gray-400 sm:mt-1 sm:gap-2 sm:text-[10px]">
                                          <span>{s.start_date ? new Date(s.start_date).toLocaleDateString("fa-IR") : "—"}</span>
                                          <span>تا</span>
                                          <span>{s.end_date ? new Date(s.end_date).toLocaleDateString("fa-IR") : "نامحدود"}</span>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="text-left shrink-0">
                                      {daysLeft != null && daysLeft > 0 && (
                                        <p className="text-[9px] text-[#d6ad60] font-bold sm:text-[10px]">{daysLeft} روز</p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* رزرو */}
                      {reservedSubs.length > 0 && (
                        <div>
                          <h3 className="mb-1.5 text-[10px] font-bold text-yellow-400 flex items-center gap-1.5 sm:mb-2 sm:text-xs">
                            <Hourglass className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> در انتظار شروع ({reservedSubs.length})
                          </h3>
                          <div className="space-y-1.5 sm:space-y-2">
                            {reservedSubs.map((s: any) => (
                              <div key={s.id} className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-2.5 sm:p-3">
                                <div className="flex items-center justify-between gap-2 sm:gap-3">
                                  <div className="flex items-center gap-2 sm:gap-3">
                                    <div className="shrink-0 rounded-lg bg-yellow-500/10 p-1.5 sm:p-2">
                                      <Hourglass className="h-3.5 w-3.5 text-yellow-400 sm:h-4 sm:w-4" />
                                    </div>
                                    <div>
                                      <p className="text-[11px] font-bold text-white sm:text-sm">{getPlanNameFa(s.plan)}</p>
                                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[9px] text-gray-400 sm:mt-1 sm:gap-2 sm:text-[10px]">
                                        <span>{s.start_date ? new Date(s.start_date).toLocaleDateString("fa-IR") : "—"}</span>
                                        <span>تا</span>
                                        <span>{s.end_date ? new Date(s.end_date).toLocaleDateString("fa-IR") : "نامحدود"}</span>
                                      </div>
                                    </div>
                                  </div>
                                  <span className="inline-block rounded-full bg-yellow-500/10 px-1.5 py-0.5 text-[8px] font-bold text-yellow-400 border border-yellow-500/20 sm:px-2 sm:text-[10px]">رزرو</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* منقضی */}
                      {expiredSubs.length > 0 && (
                        <div>
                          <h3 className="mb-1.5 text-[10px] font-bold text-gray-400 flex items-center gap-1.5 sm:mb-2 sm:text-xs">
                            <XCircle className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> منقضی شده ({expiredSubs.length})
                          </h3>
                          <div className="space-y-1.5 sm:space-y-2">
                            {expiredSubs.map((s: any) => (
                              <div key={s.id} className="rounded-2xl border border-white/[0.08] bg-[#09131d] p-2.5 sm:p-3">
                                <div className="flex items-center justify-between gap-2 sm:gap-3">
                                  <div className="flex items-center gap-2 sm:gap-3">
                                    <div className="shrink-0 rounded-lg bg-white/5 p-1.5 sm:p-2">
                                      <XCircle className="h-3.5 w-3.5 text-gray-500 sm:h-4 sm:w-4" />
                                    </div>
                                    <div>
                                      <p className="text-[11px] font-bold text-gray-300 sm:text-sm">{getPlanNameFa(s.plan)}</p>
                                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[9px] text-gray-500 sm:mt-1 sm:gap-2 sm:text-[10px]">
                                        <span>{s.start_date ? new Date(s.start_date).toLocaleDateString("fa-IR") : "—"}</span>
                                        <span>تا</span>
                                        <span>{s.end_date ? new Date(s.end_date).toLocaleDateString("fa-IR") : "نامحدود"}</span>
                                      </div>
                                    </div>
                                  </div>
                                  <span className="inline-block rounded-full bg-red-500/10 px-1.5 py-0.5 text-[8px] font-bold text-red-400 border border-red-500/20 sm:px-2 sm:text-[10px]">منقضی</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            )}


            {/* ═══ تب حساب کاربری ═══ */}
            {activeTab === "account" && (
              <motion.div 
                key="account" 
                custom={swipeDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slideTransition}
                className="space-y-4 sm:space-y-5"
              >
                <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-4 shadow-[0_6px_20px_rgba(0,0,0,0.16)] sm:p-5">
                  <div className="mb-3 flex items-center justify-between sm:mb-4">
                    <h2 className="font-display flex items-center gap-2 text-sm font-semibold text-white sm:text-base">
                      <UserIcon className="h-4 w-4 text-[#d6ad60] sm:h-5 sm:w-5" /> اطلاعات حساب
                    </h2>
                    <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
                      <button onClick={() => setIsEditOpen(true)} className="inline-flex h-7 items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-transparent px-2 text-[9px] font-medium text-gray-300 transition-colors hover:bg-white/5 hover:text-white sm:h-8 sm:px-3 sm:text-xs">
                        <Pencil className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> ویرایش
                      </button>
                      <DialogContent className="border-white/10 bg-[#081923] text-white sm:max-w-[425px]">
                        <DialogHeader><DialogTitle className="text-base text-[#d6ad60] sm:text-lg">ویرایش پروفایل</DialogTitle></DialogHeader>
                        <div className="space-y-3 pt-3 sm:space-y-4 sm:pt-4">
                          <div>
                            <label className="mb-1 block text-xs text-gray-400 sm:text-sm">نام نمایشی</label>
                            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="نام جدید" className="border-white/10 bg-black/30 text-sm" />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400 sm:text-sm">ایمیل</label>
                            <Input value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="example@email.com" dir="ltr" className="border-white/10 bg-black/30 text-center text-sm" />
                          </div>
                          <div className="space-y-2 border-t border-white/10 pt-3 sm:space-y-3 sm:pt-4">
                            <h3 className="text-xs font-bold text-[#d6ad60] sm:text-sm">تغییر رمز عبور</h3>
                            <div>
                              <label className="mb-1 block text-xs text-gray-400 sm:text-sm">رمز جدید</label>
                              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="حداقل ۶ حرف" dir="ltr" className="border-white/10 bg-black/30 text-center text-sm" />
                            </div>
                            <div>
                              <label className="mb-1 block text-xs text-gray-400 sm:text-sm">تکرار رمز</label>
                              <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="تکرار رمز" dir="ltr" className="border-white/10 bg-black/30 text-center text-sm" />
                            </div>
                          </div>
                          <Button onClick={handleUpdateProfile} disabled={editLoading} className="h-10 w-full bg-[#c6a15b] hover:bg-[#d0ad6c] text-sm font-bold text-[#030712] sm:h-11">
                            {editLoading ? "در حال ذخیره..." : "ذخیره تغییرات"}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3">
                    {[
                      { icon: UserIcon, label: "نام", value: user.full_name || "ثبت نشده", isLtr: false },
                      { icon: Mail, label: "ایمیل", value: user.email || "ثبت نشده", isLtr: true },
                      { icon: Lock, label: "رمز عبور", value: hasPassword ? "تعیین شده" : "تعیین نشده", color: hasPassword ? "text-green-400" : "text-yellow-400" },
                      { icon: UserIcon, label: "موبایل", value: user.phone, isLtr: true, isMono: true },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-2 rounded-2xl border border-white/[0.08] bg-white/[0.045] p-2 sm:gap-3 sm:p-3">
                        <div className="shrink-0 rounded-lg bg-[#d6ad60]/[0.07] p-1.5 text-[#d6ad60] sm:p-2"><item.icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" /></div>
                        <div className="flex min-w-0 flex-col">
                          <p className="text-xs text-gray-400 sm:text-sm">{item.label}</p>
                          <p className={`truncate text-xs sm:text-sm ${item.color || "text-white"} ${item.isLtr ? "dir-ltr" : ""} ${item.isMono ? "font-mono" : ""}`}>{item.value}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ═══ کارت تیکت پشتیبانی ═══ */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="pt-2">
          <Link href="/dashboard/tickets">
            <div className="group relative flex items-center justify-between overflow-hidden rounded-2xl border border-[#d6ad60]/14 bg-[#081923] p-3 shadow-xl transition-all hover:border-[#d6ad60]/50 sm:p-4">
              <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-[#d6ad60]/[0.04] blur-xl" />
              <div className="relative z-10 flex items-center gap-2.5 sm:gap-3">
                <div className="relative shrink-0 rounded-xl bg-[#d6ad60] p-2 text-[#030712] shadow-lg sm:p-2.5">
                  <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5" />
                  {ticketStats?.unread_count > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-3.5 w-3.5 animate-pulse items-center justify-center rounded-full bg-red-500 text-[8px] font-bold text-white sm:h-4 sm:w-4 sm:text-[9px]">{ticketStats.unread_count}</span>
                  )}
                </div>
                <div>
                  <p className="text-xs font-bold text-white sm:text-sm">تیکت پشتیبانی</p>
                  <p className="mt-0.5 text-xs text-gray-400 sm:text-sm">{ticketStats?.open_count > 0 ? `${ticketStats.open_count} تیکت باز داری` : "پاسخگویی سریع به سوالات"}</p>
                </div>
              </div>
              <ArrowRight className="relative z-10 h-3.5 w-3.5 text-[#d6ad60] transition-transform group-hover:-translate-x-1 sm:h-4 sm:w-4" />
            </div>
          </Link>
        </motion.div>
      </main>

      <Footer />

      {/* ═══ دانلود خطا ═══ */}
      <AnimatePresence>
        {downloadError && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" 
            onClick={() => setDownloadError(null)}
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#081923] p-6 text-center shadow-2xl" 
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10"><AlertTriangle className="h-8 w-8 text-red-500" /></div>
              <h3 className="mb-2 text-lg font-bold text-white">خطا در دانلود</h3>
              <p className="mb-6 text-sm leading-relaxed text-gray-400">{downloadError}</p>
              <div className="flex gap-2">
                <Link href="/subscription" className="flex-1"><Button className="w-full bg-[#c6a15b] hover:bg-[#d0ad6c] text-sm font-bold text-[#030712]">ارتقا اشتراک</Button></Link>
                <Button variant="outline" onClick={() => setDownloadError(null)} className="flex-1 border-white/20 text-sm text-white hover:bg-white/10">بستن</Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ مدال تراکنش ═══ */}
      <Dialog open={isUserTxDetailOpen} onOpenChange={setIsUserTxDetailOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#081923] text-white">
          <DialogHeader><DialogTitle className="text-[#d6ad60]">جزئیات تراکنش</DialogTitle></DialogHeader>
          {selectedUserTx && (
            <div className="space-y-3 py-2">
              <div className="flex justify-between text-xs"><span className="text-gray-400">پلن:</span><span className="font-bold text-white">{getPlanNameFa(selectedUserTx.plan)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-gray-400">مبلغ اصلی پلن:</span><span className="font-bold text-[#d6ad60]" dir="ltr">{selectedUserTx.plan_price ? selectedUserTx.plan_price.toLocaleString("fa-IR") : "—"} تومان</span></div>
              <div className="flex justify-between text-xs"><span className="text-gray-400">مبلغ پرداختی شما:</span><span className="font-bold text-white" dir="ltr">{(selectedUserTx.amount || 0).toLocaleString("fa-IR")} تومان</span></div>
              {selectedUserTx.zibal_ref_id && (
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">شماره پیگیری:</span>
                  <span className="font-mono text-[#d6ad60]" dir="ltr">
                    {selectedUserTx.zibal_ref_id}
                  </span>
                </div>
              )}
              {(selectedUserTx.source === "refund_request" || selectedUserTx.payment_method === "refund") && (
                <div className="rounded-xl border border-purple-500/20 bg-purple-500/10 p-3 text-xs text-purple-200">
                  <div className="mb-2 font-bold text-purple-300">{selectedUserTx.stage_label || (selectedUserTx.source === "refund_request" ? "درخواست عودت وجه توسط کاربر" : "عودت وجه توسط مدیر")}</div>
                  {selectedUserTx.reference_code && <div className="flex justify-between"><span>کد پیگیری مشترک:</span><b className="font-mono text-purple-300" dir="ltr">{selectedUserTx.reference_code}</b></div>}
                  {selectedUserTx.subscription_id && <div className="flex justify-between"><span>شناسه اشتراک:</span><b className="font-mono text-blue-300" dir="ltr">SUB-{String(selectedUserTx.subscription_id).padStart(6, "0")}</b></div>}
                  {selectedUserTx.subscription_code && <div className="flex justify-between"><span>شناسه اشتراک:</span><b className="font-mono text-blue-300" dir="ltr">{selectedUserTx.subscription_code}</b></div>}
                  <div className="flex justify-between"><span>وضعیت عودت:</span><b className="text-white">{selectedUserTx.status === "pending" ? "در حال بررسی" : selectedUserTx.status === "refunded" || selectedUserTx.status === "approved" ? "عودت شده" : "رد شده"}</b></div>
                  {selectedUserTx.old_plan && <div className="mt-1">پلن قبلی: <b>{getPlanNameFa(selectedUserTx.old_plan)}</b></div>}
                  {selectedUserTx.new_plan && <div className="mt-1">پلن جدید: <b>{getPlanNameFa(selectedUserTx.new_plan)}</b></div>}
                  {selectedUserTx.processed_at && <div className="mt-1">تاریخ رسیدگی: <b>{new Date(selectedUserTx.processed_at).toLocaleString("fa-IR")}</b></div>}
                  {selectedUserTx.admin_note && <div className="mt-2 border-t border-purple-500/20 pt-2"><b>{selectedUserTx.source === "refund_request" ? "توضیح ثبت اولیه درخواست:" : "توضیح رسیدگی مدیر:"}</b> {selectedUserTx.admin_note}</div>}
                </div>
              )}
              <div className="flex justify-between text-xs"><span className="text-gray-400">وضعیت:</span><span className={`font-bold ${getPaymentStatus(selectedUserTx.status).color}`}>{getPaymentStatus(selectedUserTx.status).text}</span></div>
              <div className="flex justify-between text-xs"><span className="text-gray-400">روش پرداخت:</span><span className="text-white">{getPaymentMethodFa(selectedUserTx.payment_method)}</span></div>
              <div className="flex justify-between text-xs"><span className="text-gray-400">تاریخ درخواست:</span><span className="text-white">{new Date(selectedUserTx.created_at).toLocaleString("fa-IR")}</span></div>
              {selectedUserTx.payment_time && (<div className="flex justify-between text-xs"><span className="text-gray-400">زمان واریز:</span><span className="text-white">{selectedUserTx.payment_time}</span></div>)}
              {selectedUserTx.receipt_note && (<div className="rounded border border-blue-500/20 bg-blue-500/10 p-2 text-xs text-blue-400"><span className="font-bold">توضیحات شما:</span> {selectedUserTx.receipt_note}</div>)}
              {selectedUserTx.admin_note && !selectedUserTx.type && (<div className="rounded border border-yellow-500/20 bg-yellow-500/10 p-2 text-xs text-yellow-500"><span className="font-bold">دلیل ادمین:</span> {selectedUserTx.admin_note}</div>)}
              <div className="flex gap-2 pt-2"><Button variant="outline" onClick={() => setIsUserTxDetailOpen(false)} className="flex-1 border-white/10 text-gray-300">بستن</Button></div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}