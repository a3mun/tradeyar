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
  LogOut,
  CheckCircle2,
  ShieldCheck,
  Pencil,
  MessageSquare,
  Home,
  Mail,
  Lock,
  User as UserIcon,
  Crown,
  Clock,
  Zap,
  Download,
  BookOpen,
  Gift,
  AlertTriangle,
  ArrowRight,
  Puzzle,
  Hourglass,
  Wallet,
  CreditCard,
  History,
  XCircle,
  Receipt,
  LayoutDashboard,
  UserCircle,
  RefreshCw,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Link from "next/link";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    free: "پلن آشنایی رایگان",
    "1_month": "اشتراک یک ماهه",
    "3_months": "اشتراک سه ماهه",
    "6_months": "اشتراک شش ماهه",
    "12_months": "اشتراک یک ساله",
    "نامحدود (مدیر)": "نامحدود (مدیر)",
    refund: "عودت وجه",
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

const PENDING_KEY = "trademun_pending_request";

const getPaymentMethodFa = (method: string | null | undefined) => {
  if (!method) return "—";
  if (method === "zibal") return "درگاه زیبال";
  if (method === "card") return "کارت به کارت";
  if (method === "refund") return "عودت وجه";
  return method;
};

const getPaymentStatus = (status: string) => {
  switch (status) {
    case "approved":
      return {
        text: "تایید شده",
        color: "text-green-400",
        bg: "bg-green-500/10",
        border: "border-green-500/30",
        icon: CheckCircle2,
      };
    case "pending":
      return {
        text: "در حال بررسی",
        color: "text-yellow-400",
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/30",
        icon: Hourglass,
      };
    case "rejected":
      return {
        text: "رد شده",
        color: "text-red-400",
        bg: "bg-red-500/10",
        border: "border-red-500/30",
        icon: XCircle,
      };
    case "refunded":
      return {
        text: "عودت شده",
        color: "text-purple-400",
        bg: "bg-purple-500/10",
        border: "border-purple-500/30",
        icon: RefreshCw,
      };
    default:
      return {
        text: status,
        color: "text-gray-400",
        bg: "bg-white/5",
        border: "border-white/10",
        icon: History,
      };
  }
};

type TabKey = "home" | "history" | "account";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [sub, setSub] = useState<any>(null);
  const [ticketStats, setTicketStats] = useState<any>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [txLoading, setTxLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("home");

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

  useEffect(() => {
    const u = getUser();
    if (!u) {
      router.replace("/login");
      return;
    }
    setUserData(u);
    setNewName(u.full_name || "");
    setNewEmail(u.email || "");

    if (typeof window !== "undefined") {
      setIsPending(localStorage.getItem(PENDING_KEY) === "true");
    }

    fetch(`${apiUrl}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.user) {
          setUser(data.user);
          setUserData(data.user);
          setHasPassword(!!data.user.has_password);
        }
      })
      .catch(console.error);

    fetch(`${apiUrl}/subscription/my`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setSub(data.subscription);
        if (data.subscription?.status === "active" && typeof window !== "undefined") {
          localStorage.removeItem(PENDING_KEY);
          setIsPending(false);
        }
      })
      .catch((err) => console.error(err));

    fetch(`${apiUrl}/tickets/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) =>
        res.ok
          ? res.json()
          : { open_count: 0, closed_count: 0, unread_count: 0, total_count: 0 }
      )
      .then((data) => setTicketStats(data))
      .catch(() =>
        setTicketStats({ open_count: 0, closed_count: 0, unread_count: 0, total_count: 0 })
      );

    fetch(`${apiUrl}/subscription/my-transactions`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : { items: [] }))
      .then((data) => setTransactions(data.items || []))
      .catch(() => setTransactions([]))
      .finally(() => setTxLoading(false));
  }, [router, apiUrl, token]);

  const handleLogout = () => {
    removeToken();
    router.replace("/login");
  };

  const handleDownload = async () => {
    if (!token) {
      setDownloadError("لطفاً ابتدا وارد حساب کاربری خود شوید.");
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/extension/download`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });

      if (!res.ok) {
        const data = await res.json();
        setDownloadError(
          data.detail ||
            "برای دانلود افزونه، نیاز به اشتراک حرفه‌ای (Pro) دارید. لطفاً از صفحه اشتراک، پلن خود را ارتقا دهید."
        );
        return;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "trademun-extension.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError("خطا در ارتباط با سرور");
    }
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
        body: JSON.stringify({
          full_name: newName,
          email: newEmail || undefined,
          new_password: newPassword || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا در ذخیره");

      setUser(data.user);
      setUserData(data.user);
      setHasPassword(!!data.user.has_password);
      setIsEditOpen(false);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setEditLoading(false);
    }
  };

  const openUserTxDetail = (tx: any) => {
    setSelectedUserTx(tx);
    setIsUserTxDetailOpen(true);
  };

  if (!user)
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">
        در حال بارگذاری...
      </div>
    );

  const subStatus = getSubStatus(sub);
  const displayName = user.full_name || user.phone;

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="container mx-auto max-w-5xl flex-1 space-y-5 p-4 py-6">
        {/* ═══ خوش‌آمد ═══ */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h1 className="font-display truncate text-xl font-bold text-white sm:text-2xl">
                خوش آمدی، <span className="text-[#d6ad60]">{displayName}</span> 👋
              </h1>
              <p className="mt-1 text-xs text-gray-400 sm:text-sm">
                امروز چه خبر؟ بازار منتظرته.
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Link href="/">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-9 w-9 border-white/10 text-gray-300 hover:bg-white/5"
                >
                  <Home className="h-4 w-4" />
                </Button>
              </Link>
              <Button
                variant="destructive"
                size="icon"
                onClick={handleLogout}
                className="h-9 w-9"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>

        {/* ═══ در انتظار ═══ */}
        {isPending && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3 rounded-2xl border border-yellow-500/30 bg-yellow-500/5 p-4"
          >
            <div className="shrink-0 rounded-lg bg-yellow-500/15 p-2">
              <Hourglass className="h-5 w-5 animate-pulse text-yellow-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-yellow-400">
                درخواست اشتراک شما در حال بررسی است
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-gray-400">
                تیم پشتیبانی ظرف ۲۴ ساعت آینده درخواست شما را بررسی می‌کند. پس از
                تایید، اشتراک به‌طور خودکار فعال خواهد شد.
              </p>
            </div>
          </motion.div>
        )}

        {/* ═══ تب‌ها (هم‌اندازه، مدرن) ═══ */}
        <div className="grid grid-cols-3 gap-1.5 rounded-xl border border-white/10 bg-white/5 p-1">
          <button
            onClick={() => setActiveTab("home")}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition-all sm:text-sm ${
              activeTab === "home"
                ? "bg-[#d6ad60] text-[#101827] shadow-md"
                : "text-gray-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <LayoutDashboard className="h-4 w-4" />
            <span className="hidden sm:inline">وضعیت اشتراک</span>
            <span className="sm:hidden">اشتراک</span>
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition-all sm:text-sm ${
              activeTab === "history"
                ? "bg-[#d6ad60] text-[#101827] shadow-md"
                : "text-gray-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <Receipt className="h-4 w-4" />
            <span className="hidden sm:inline">تاریخچه مالی</span>
            <span className="sm:hidden">تاریخچه</span>
          </button>
          <button
            onClick={() => setActiveTab("account")}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition-all sm:text-sm ${
              activeTab === "account"
                ? "bg-[#d6ad60] text-[#101827] shadow-md"
                : "text-gray-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <UserCircle className="h-4 w-4" />
            <span className="hidden sm:inline">حساب کاربری</span>
            <span className="sm:hidden">حساب</span>
          </button>
        </div>

        {/* ═══ تب home ═══ */}
        {activeTab === "home" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            {/* کارت اشتراک */}
            <div className="relative overflow-hidden rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-r from-[#14263e] via-[#0d1b2d] to-[#07111f] p-5 sm:p-6">
              <div className="absolute -right-10 -top-10 p-4 opacity-5">
                <Crown className="h-48 w-48 text-[#d6ad60]" />
              </div>
              <div className="relative z-10 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
                <div className="w-full space-y-2 sm:w-auto">
                  <div className="inline-flex items-center gap-1.5 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10 px-2.5 py-1 text-[#d6ad60]">
                    <Crown className="h-3.5 w-3.5" />
                    <span className="text-[10px] font-bold sm:text-xs">
                      وضعیت اشتراک شما
                    </span>
                  </div>
                  {sub ? (
                    <div className="space-y-1 pr-1">
                      <h2 className="flex flex-wrap items-center gap-2.5 text-lg font-bold text-white sm:text-xl">
                        {sub.plan === "free" ? (
                          <Gift className="h-5 w-5 text-[#d6ad60]" />
                        ) : (
                          <ShieldCheck className="h-5 w-5 text-green-400" />
                        )}
                        {getPlanNameFa(sub.plan)}
                        <span
                          className={`inline-block h-2.5 w-2.5 rounded-full ${
                            subStatus.active
                              ? "bg-green-500 shadow-[0_0_8px_#22c55e]"
                              : "bg-red-500 shadow-[0_0_8px_#ef4444]"
                          }`}
                        />
                      </h2>
                      <div className="mt-2 flex items-center gap-2 text-xs text-gray-400 sm:text-sm">
                        <Clock className="h-3.5 w-3.5" />
                        <span>
                          تاریخ انقضا:{" "}
                          {sub.end_date
                            ? new Date(sub.end_date).toLocaleDateString("fa-IR")
                            : "نامحدود"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <h2 className="text-xl font-bold text-white sm:text-2xl">
                      در حال دریافت...
                    </h2>
                  )}
                </div>
                <Link href="/subscription" className="mt-2 w-full shrink-0 sm:mt-0 sm:w-auto">
                  <Button className="h-11 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-5 text-sm font-bold text-[#07111f] shadow-lg shadow-[#d6ad60]/20 transition-transform hover:scale-[1.02] hover:opacity-90 sm:h-12 sm:px-6 sm:text-base">
                    <Zap className="h-4 w-4 sm:h-5 sm:w-5" />
                    ارتقا / تمدید
                  </Button>
                </Link>
              </div>
            </div>

            {/* کارت افزونه */}
            <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#14263e] to-[#0a1526] p-4 transition-all hover:border-[#d6ad60]/40 sm:p-5">
              <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-bl-full bg-[#d6ad60]/8 blur-2xl transition-all group-hover:bg-[#d6ad60]/15" />
              <div className="relative flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
                <div className="flex w-full items-start gap-3 md:min-w-0 md:flex-1">
                  <div className="shrink-0 rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/12 p-2.5 text-[#d6ad60] sm:p-3">
                    <Puzzle className="h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-bold text-white sm:text-base">
                        افزونه کروم تریدمون
                      </p>
                      <span className="rounded-full border border-[#d6ad60]/25 bg-[#d6ad60]/15 px-2 py-0.5 text-[9px] font-bold text-[#d6ad60]">
                        ویژه انس طلا
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-relaxed text-gray-400 sm:text-xs">
                      نوسان‌گیر لحظه‌ای <b className="text-gray-200">XAU/USD</b> در
                      صرافی‌های دریا گلد و آلفا گلد. نیازمند{" "}
                      <b className="text-[#d6ad60]">اشتراک حرفه‌ای</b>.
                    </p>
                    <Link
                      href="/extension/guide"
                      className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-bold text-[#d6ad60] hover:text-[#e2c17e] sm:text-xs"
                    >
                      <BookOpen className="h-3 w-3" />
                      راهنمای جامع افزونه
                      <ArrowRight className="h-3 w-3 rotate-180" />
                    </Link>
                  </div>
                </div>
                <div className="flex w-full flex-col gap-2 md:w-auto md:shrink-0 md:flex-row">
                  <Link href="/extension/guide" className="w-full sm:w-auto">
                    <Button
                      variant="outline"
                      className="h-10 w-full gap-2 border-white/15 px-4 text-xs text-gray-300 hover:border-[#d6ad60]/40 hover:bg-white/5 sm:text-sm"
                    >
                      <BookOpen className="h-4 w-4" />
                      راهنما
                    </Button>
                  </Link>
                  <Button
                    onClick={handleDownload}
                    className="h-10 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] px-4 text-xs font-bold text-[#07111f] shadow-md shadow-[#d6ad60]/20 hover:opacity-90 sm:w-auto sm:text-sm"
                  >
                    <Download className="h-4 w-4" />
                    دانلود افزونه
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* ═══ تب history ═══ */}
        {activeTab === "history" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <div className="rounded-2xl border border-white/10 bg-[#0d1b2d] p-4 sm:p-5">
              <div className="mb-3 flex items-center justify-between sm:mb-4">
                <h2 className="font-display flex items-center gap-2 text-base font-semibold text-white sm:text-lg">
                  <Receipt className="h-4 w-4 text-[#d6ad60] sm:h-5 sm:w-5" />
                  تراکنش‌های من
                </h2>
                <span className="rounded-full border border-white/5 bg-white/5 px-2 py-0.5 text-[10px] text-gray-500">
                  {transactions.length} تراکنش
                </span>
              </div>
              {txLoading ? (
                <div className="flex justify-center py-6">
                  <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-t-2 border-[#d6ad60]"></div>
                </div>
              ) : transactions.length === 0 ? (
                <div className="rounded-xl border border-white/5 bg-black/20 py-6 text-center">
                  <History className="mx-auto mb-2 h-8 w-8 text-gray-600" />
                  <p className="text-xs text-gray-400">هنوز تراکنشی ثبت نکرده‌اید.</p>
                  <Link href="/subscription">
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3 h-8 gap-1 border-[#d6ad60]/30 text-xs text-[#d6ad60] hover:bg-[#d6ad60]/10"
                    >
                      <Zap className="h-3 w-3" />
                      خرید اشتراک
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                  {transactions.map((tx: any, idx: number) => {
                    const st = getPaymentStatus(tx.status);
                    const StatusIcon = st.icon;
                    const MethodIcon =
                      tx.payment_method === "zibal"
                        ? Wallet
                        : tx.payment_method === "refund"
                          ? RefreshCw
                          : CreditCard;
                    const isRefund = tx.payment_method === "refund" || tx.plan === "refund";
                    const cardBg = isRefund
                      ? "bg-purple-500/5 border-purple-500/20 hover:border-purple-500/40"
                      : "bg-black/20 border-white/5 hover:border-[#d6ad60]/20";

                    return (
                      <div
                        key={tx.id || idx}
                        className={`flex cursor-pointer items-center justify-between gap-2 rounded-xl border p-3 transition-colors ${cardBg}`}
                        onClick={() => openUserTxDetail(tx)}
                      >
                        <div className="flex min-w-0 flex-1 items-center gap-3">
                          <div
                            className={`shrink-0 rounded-lg p-2 ${
                              isRefund
                                ? "border-purple-500/20 bg-purple-500/10"
                                : st.bg + " " + st.border
                            }`}
                          >
                            <StatusIcon
                              className={`h-4 w-4 ${
                                isRefund ? "text-purple-400" : st.color
                              }`}
                            />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p
                                className={`text-xs font-bold ${
                                  isRefund ? "text-purple-400" : "text-white"
                                }`}
                              >
                                {getPlanNameFa(tx.plan)}
                              </p>
                              <span
                                className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold ${
                                  isRefund
                                    ? "border-purple-500/20 bg-purple-500/10 text-purple-400"
                                    : st.bg + " " + st.color + " " + st.border
                                }`}
                              >
                                {st.text}
                              </span>
                            </div>
                            <div className="mt-1 flex items-center gap-3 text-[10px] text-gray-400">
                              <span className="flex items-center gap-1">
                                <MethodIcon className="h-3 w-3" />
                                {getPaymentMethodFa(tx.payment_method)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {new Date(tx.created_at).toLocaleString("fa-IR")}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="shrink-0 text-left sm:text-right">
                          <p
                            className={`text-sm font-bold ${
                              isRefund ? "text-purple-400" : "text-white"
                            }`}
                            dir="ltr"
                          >
                            {(tx.amount || 0).toLocaleString("fa-IR")}
                            <span className="mr-1 text-[10px] text-gray-400">
                              تومان
                            </span>
                          </p>
                          <p className="mt-1 text-[10px] text-[#d6ad60]">
                            جزئیات{" "}
                            <ArrowRight className="inline h-3 w-3 rotate-180" />
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* ═══ تب account ═══ */}
        {activeTab === "account" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <div className="rounded-2xl border border-white/10 bg-[#0d1b2d] p-4 sm:p-6">
              <div className="mb-3 flex items-center justify-between sm:mb-4">
                <h2 className="font-display flex items-center gap-2 text-base font-semibold text-white sm:text-lg">
                  <UserIcon className="h-4 w-4 text-[#d6ad60] sm:h-5 sm:w-5" />
                  اطلاعات حساب
                </h2>
                <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
                  <button
                    onClick={() => setIsEditOpen(true)}
                    className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-transparent px-2.5 text-[10px] font-medium text-gray-300 transition-colors hover:bg-white/5 hover:text-white sm:px-3 sm:text-xs"
                  >
                    <Pencil className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                    ویرایش
                  </button>
                  <DialogContent className="border-white/10 bg-[#0d1b2d] text-white sm:max-w-[425px]">
                    <DialogHeader>
                      <DialogTitle className="text-base text-[#d6ad60] sm:text-lg">
                        ویرایش پروفایل
                      </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 pt-3 sm:space-y-4 sm:pt-4">
                      <div>
                        <label className="mb-1 block text-[10px] text-gray-400 sm:text-xs">
                          نام نمایشی
                        </label>
                        <Input
                          value={newName}
                          onChange={(e) => setNewName(e.target.value)}
                          placeholder="نام جدید"
                          className="border-white/10 bg-black/30 text-sm"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-[10px] text-gray-400 sm:text-xs">
                          ایمیل
                        </label>
                        <Input
                          value={newEmail}
                          onChange={(e) => setNewEmail(e.target.value)}
                          placeholder="example@email.com"
                          dir="ltr"
                          className="border-white/10 bg-black/30 text-center text-sm"
                        />
                      </div>
                      <div className="space-y-2 border-t border-white/10 pt-3 sm:space-y-3 sm:pt-4">
                        <h3 className="text-xs font-bold text-[#d6ad60] sm:text-sm">
                          تغییر رمز عبور
                        </h3>
                        <div>
                          <label className="mb-1 block text-[10px] text-gray-400 sm:text-xs">
                            رمز جدید
                          </label>
                          <Input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            placeholder="حداقل ۶ حرف"
                            dir="ltr"
                            className="border-white/10 bg-black/30 text-center text-sm"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-[10px] text-gray-400 sm:text-xs">
                            تکرار رمز
                          </label>
                          <Input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="تکرار رمز"
                            dir="ltr"
                            className="border-white/10 bg-black/30 text-center text-sm"
                          />
                        </div>
                      </div>
                      <Button
                        onClick={handleUpdateProfile}
                        disabled={editLoading}
                        className="h-10 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f] sm:h-11"
                      >
                        {editLoading ? "در حال ذخیره..." : "ذخیره تغییرات"}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3">
                {[
                  {
                    icon: UserIcon,
                    label: "نام",
                    value: user.full_name || "ثبت نشده",
                    isLtr: false,
                  },
                  {
                    icon: Mail,
                    label: "ایمیل",
                    value: user.email || "ثبت نشده",
                    isLtr: true,
                  },
                  {
                    icon: Lock,
                    label: "رمز عبور",
                    value: hasPassword ? "تعیین شده" : "تعیین نشده",
                    color: hasPassword ? "text-green-400" : "text-yellow-400",
                  },
                  {
                    icon: UserIcon,
                    label: "موبایل",
                    value: user.phone,
                    isLtr: true,
                    isMono: true,
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/5 p-2 sm:gap-3 sm:p-3"
                  >
                    <div className="shrink-0 rounded-lg bg-[#d6ad60]/10 p-1.5 text-[#d6ad60] sm:p-2">
                      <item.icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    </div>
                    <div className="flex min-w-0 flex-col">
                      <p className="text-[9px] text-gray-400 sm:text-[10px]">
                        {item.label}
                      </p>
                      <p
                        className={`truncate text-xs sm:text-sm ${
                          item.color || "text-white"
                        } ${item.isLtr ? "dir-ltr" : ""} ${
                          item.isMono ? "font-mono" : ""
                        }`}
                      >
                        {item.value}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* ═══ تیکت ═══ */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="pt-4"
        >
          <Link href="/dashboard/tickets">
            <div className="group relative flex items-center justify-between overflow-hidden rounded-2xl border-2 border-[#d6ad60]/40 bg-gradient-to-br from-[#1a2c45] to-[#0a1526] p-4 transition-all hover:border-[#d6ad60]">
              <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-[#d6ad60]/15 blur-xl transition-all group-hover:bg-[#d6ad60]/25" />
              <div className="relative z-10 flex items-center gap-3">
                <div className="relative shrink-0 rounded-xl bg-[#d6ad60] p-2.5 text-[#07111f] shadow-lg shadow-[#d6ad60]/25">
                  <MessageSquare className="h-5 w-5" />
                  {ticketStats?.unread_count > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-4 w-4 animate-pulse items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
                      {ticketStats.unread_count}
                    </span>
                  )}
                </div>
                <div>
                  <p className="text-sm font-bold text-white">تیکت پشتیبانی</p>
                  <p className="mt-0.5 text-[10px] text-gray-400">
                    {ticketStats?.open_count > 0
                      ? `${ticketStats.open_count} تیکت باز داری`
                      : "پاسخگویی سریع به سوالات"}
                  </p>
                </div>
              </div>
              <ArrowRight className="relative z-10 h-4 w-4 text-[#d6ad60] transition-transform group-hover:-translate-x-1" />
            </div>
          </Link>
        </motion.div>
      </main>
      <Footer />

      {/* ═══ دانلود خطا ═══ */}
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 transition-opacity ${
          !downloadError ? "pointer-events-none opacity-0" : "opacity-100"
        }`}
        onClick={() => setDownloadError(null)}
      >
        <div
          className="w-full max-w-sm scale-100 rounded-2xl border border-red-500/20 bg-[#0d1b2d] p-6 text-center shadow-2xl transition-transform"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10">
            <AlertTriangle className="h-8 w-8 text-red-500" />
          </div>
          <h3 className="mb-2 text-lg font-bold text-white">خطا در دانلود</h3>
          <p className="mb-6 text-sm leading-relaxed text-gray-400">{downloadError}</p>
          <div className="flex gap-2">
            <Link href="/subscription" className="flex-1">
              <Button className="w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#07111f]">
                ارتقا اشتراک
              </Button>
            </Link>
            <Button
              variant="outline"
              onClick={() => setDownloadError(null)}
              className="flex-1 border-white/20 text-sm text-white hover:bg-white/10"
            >
              بستن
            </Button>
          </div>
        </div>
      </div>

      {/* ═══ مدال تراکنش ═══ */}
      <Dialog open={isUserTxDetailOpen} onOpenChange={setIsUserTxDetailOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">جزئیات تراکنش</DialogTitle>
          </DialogHeader>
          {selectedUserTx && (
            <div className="space-y-3 py-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">پلن:</span>
                <span className="font-bold text-white">
                  {getPlanNameFa(selectedUserTx.plan)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">مبلغ اصلی پلن:</span>
                <span className="font-bold text-[#d6ad60]" dir="ltr">
                  {selectedUserTx.plan_price
                    ? selectedUserTx.plan_price.toLocaleString("fa-IR")
                    : "—"}{" "}
                  تومان
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">مبلغ پرداختی شما:</span>
                <span className="font-bold text-white" dir="ltr">
                  {(selectedUserTx.amount || 0).toLocaleString("fa-IR")} تومان
                </span>
              </div>

              {selectedUserTx.type === "refund" && (
                <div className="rounded border border-purple-500/20 bg-purple-500/10 p-2 text-xs text-purple-400">
                  <div>
                    وضعیت عودت:{" "}
                    <b className="text-white">
                      {selectedUserTx.status === "pending"
                        ? "در حال بررسی"
                        : selectedUserTx.status === "refunded"
                          ? "عودت شده"
                          : "رد شده"}
                    </b>
                  </div>
                  {selectedUserTx.admin_note && (
                    <div className="mt-1">
                      توضیحات ادمین: {selectedUserTx.admin_note}
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-between text-xs">
                <span className="text-gray-400">وضعیت:</span>
                <span
                  className={`font-bold ${
                    getPaymentStatus(selectedUserTx.status).color
                  }`}
                >
                  {getPaymentStatus(selectedUserTx.status).text}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">روش پرداخت:</span>
                <span className="text-white">
                  {getPaymentMethodFa(selectedUserTx.payment_method)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">تاریخ درخواست:</span>
                <span className="text-white">
                  {new Date(selectedUserTx.created_at).toLocaleString("fa-IR")}
                </span>
              </div>
              {selectedUserTx.payment_time && (
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">زمان واریز:</span>
                  <span className="text-white">{selectedUserTx.payment_time}</span>
                </div>
              )}
              {selectedUserTx.receipt_note && (
                <div className="rounded border border-blue-500/20 bg-blue-500/10 p-2 text-xs text-blue-400">
                  <span className="font-bold">توضیحات شما:</span>{" "}
                  {selectedUserTx.receipt_note}
                </div>
              )}
              {selectedUserTx.admin_note && !selectedUserTx.type && (
                <div className="rounded border border-yellow-500/20 bg-yellow-500/10 p-2 text-xs text-yellow-500">
                  <span className="font-bold">دلیل ادمین:</span>{" "}
                  {selectedUserTx.admin_note}
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setIsUserTxDetailOpen(false)}
                  className="flex-1 border-white/10 text-gray-300"
                >
                  بستن
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}