"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion, AnimatePresence } from "framer-motion";
import { 
  LogOut, CheckCircle2, XCircle, CreditCard, Users, 
  Clock, Globe, Monitor, UserCheck, Download, Upload, History, 
  ShieldAlert, ArrowUpDown, Home, Crown, TrendingUp, Bell, X,
  UserPlus, Trash2, Wrench, AlertTriangle
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAdminNotifications } from "@/hooks/useAdminNotifications";
import Link from "next/link";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "1_month": "یک ماهه", "3_months": "سه ماهه", "6_months": "شش ماهه", "12_months": "یک ساله",
    "free": "رایگان", "monthly": "ماهانه", "بدون اشتراک": "بدون اشتراک", "نامحدود (مدیر)": "نامحدود (مدیر)"
  };
  return map[plan] || plan || "نامشخص";
};

const formatFaDate = (iso: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("fa-IR"); } catch { return "—"; }
};

const formatFaDateTime = (iso: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("fa-IR", { dateStyle: "short", timeStyle: "short" }); } catch { return "—"; }
};

const statusDot = (status: string) => {
  switch (status) {
    case "active": return "bg-green-500 shadow-[0_0_8px_#22c55e]";
    case "free_active": return "bg-yellow-500 shadow-[0_0_8px_#eab308]";
    case "expired": return "bg-red-500 shadow-[0_0_8px_#ef4444]";
    case "free": return "bg-red-500/60";
    case "admin": return "bg-blue-500 shadow-[0_0_8px_#3b82f6]";
    default: return "bg-gray-500";
  }
};

export default function AdminPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"payments" | "users" | "transactions" | "tools">("users");
  const [payments, setPayments] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "expired">("all");

  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userDetails, setUserDetails] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [adjustDays, setAdjustDays] = useState<number>(0);
  const [sendSmsPlan, setSendSmsPlan] = useState(true);
  const [sendSmsDays, setSendSmsDays] = useState(true);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newUserPhone, setNewUserPhone] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserPlan, setNewUserPlan] = useState("1_month");
  const [newUserDays, setNewUserDays] = useState(30);
  const [newUserSendSms, setNewUserSendSms] = useState(true);

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ type: 'delete' | 'admin' | 'action', id?: number, endpoint?: string, message: string } | null>(null);
  const [deleteHard, setDeleteHard] = useState(false);

  const [notifications, setNotifications] = useState<any[]>([]);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  useEffect(() => {
    fetch(`${apiUrl}/admin/payments`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json()).then(data => setPendingCount((data.items || []).length)).catch(() => {});
  }, [apiUrl, token]);

  useEffect(() => {
    const u = getUser();
    if (!u || !u.is_admin) { router.replace("/login"); return; }
    setUserData(u);
    fetchData();
  }, [router, activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "payments") {
        const res = await fetch(`${apiUrl}/admin/payments`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) { setPayments(data.items || []); setPendingCount((data.items || []).length); }
      } else if (activeTab === "transactions") {
        const res = await fetch(`${apiUrl}/admin/transactions`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setTransactions(data.items || []);
      } else {
        const res = await fetch(`${apiUrl}/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setUsersList(data.items || []);
      }
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const { connected } = useAdminNotifications((n) => {
    setNotifications((prev) => [n, ...prev].slice(0, 5));
    fetchData();
  });

  const dismissNotification = (idx: number) => setNotifications((prev) => prev.filter((_, i) => i !== idx));

  useEffect(() => {
    if (notifications.length === 0) return;
    const timers = notifications.map((_, idx) => setTimeout(() => dismissNotification(idx), 15000));
    return () => timers.forEach((t) => clearTimeout(t));
  }, [notifications.length]);

  const filteredUsers = usersList.filter(u => {
    const matchSearch = u.phone.includes(searchQuery) || (u.full_name && u.full_name.includes(searchQuery));
    if (!matchSearch) return false;
    if (statusFilter === "active") return u.is_active_sub || u.is_admin;
    if (statusFilter === "expired") return !u.is_active_sub && !u.is_admin;
    return true;
  });

  const sortedUsers = [...filteredUsers].sort((a, b) => {
    if (!sortConfig) return 0;
    const { key, direction } = sortConfig;
    const aVal = a[key] ?? ""; const bVal = b[key] ?? "";
    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });

  const requestSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const openUserDetails = async (u: any) => {
    setSelectedUser(u); setIsModalOpen(true); setUserDetails(null); setAdjustDays(0);
    try {
      const res = await fetch(`${apiUrl}/admin/users/${u.id}/details`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (res.ok) setUserDetails(data);
    } catch (err) { console.error(err); }
  };

  const requestConfirm = (type: 'delete' | 'admin' | 'action', message: string, id?: number, endpoint?: string) => {
    setConfirmAction({ type, id, endpoint, message });
    setIsConfirmOpen(true);
  };

  const executeAction = async () => {
    if (!confirmAction) return;
    setIsConfirmOpen(false);
    try {
      if (confirmAction.type === 'delete' && confirmAction.id) {
        const res = await fetch(`${apiUrl}/admin/users/${confirmAction.id}?hard_delete=${deleteHard}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
        setIsModalOpen(false);
        fetchData();
      } else if (confirmAction.endpoint) {
        const res = await fetch(`${apiUrl}${confirmAction.endpoint}`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
        setIsModalOpen(false);
        fetchData();
      }
    } catch (err: any) { alert(err.message); }
  };

  const handleAction = async (id: number, endpoint: string, confirmMsg: string) => {
    requestConfirm('action', confirmMsg, id, endpoint);
  };

  const handleChangePlan = (plan: string) => {
    requestConfirm('action', `پلن کاربر به ${getPlanNameFa(plan)} تغییر کند؟`, selectedUser.id, `/admin/users/${selectedUser.id}/change-plan?plan=${plan}&send_sms=${sendSmsPlan}`);
  };

  const handleAdjustDays = () => {
    requestConfirm('action', `تعداد ${adjustDays} روز به اشتراک کاربر اضافه/کم شود؟`, selectedUser.id, `/admin/users/${selectedUser.id}/adjust-days?days=${adjustDays}&send_sms=${sendSmsDays}`);
  };

  const handleDeleteUser = () => {
    requestConfirm('delete', deleteHard ? "کاربر و تمام داده‌های مرتبط برای همیشه حذف شوند؟" : "کاربر غیرفعال شود؟ (قابل بازگشت)", selectedUser.id);
  };

  const handleAddUser = async () => {
    if (!newUserPhone || newUserPhone.length < 11) return alert("شماره موبایل نامعتبر است");
    try {
      const res = await fetch(`${apiUrl}/admin/users/add?phone=${newUserPhone}&full_name=${newUserName}&plan=${newUserPlan}&days=${newUserDays}&send_sms=${newUserSendSms}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      alert(data.message);
      setIsAddModalOpen(false); setNewUserPhone(""); setNewUserName("");
      fetchData();
    } catch (err: any) { alert(err.message); }
  };

  const handleBackup = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/backup`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error("خطا در بک‌آپ");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `trademun_backup_${Date.now()}.sql`; a.click();
    } catch (err) { alert("خطا در بک‌آپ"); }
  };

  const handleExcel = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/users/excel`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error("خطا");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `trademun-users-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.xlsx`; a.click();
    } catch (err) { alert("خطا"); }
  };

  const handleRestore = () => {
    const input = document.createElement("input"); input.type = "file"; input.accept = ".sql";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const formData = new FormData(); formData.append("file", file);
      try {
        const res = await fetch(`${apiUrl}/admin/backup/restore`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
        if (res.ok) alert("بازگردانی شد"); else alert("خطا");
      } catch (err) { alert("خطا"); }
    };
    input.click();
  };

  if (!user) return <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">در حال بارگذاری...</div>;
  const activeUsersCount = usersList.filter(u => u.is_active_sub || u.is_admin).length;
    return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <div className="fixed top-20 left-4 right-4 z-[100] flex flex-col gap-2 sm:left-auto sm:right-4 sm:w-96 pointer-events-none">
        <AnimatePresence>
          {notifications.map((n, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 50 }} className="pointer-events-auto flex items-start gap-3 rounded-xl border border-[#d6ad60]/40 bg-[#0d1b2d] p-4 shadow-2xl backdrop-blur-xl">
              <div className={`p-2 rounded-lg ${n.type === "new_user" ? "bg-blue-500/20" : "bg-[#d6ad60]/20"}`}>
                <Bell className={`h-5 w-5 ${n.type === "new_user" ? "text-blue-400" : "text-[#d6ad60]"}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-white">{n.message || "نوتیف جدید"}</p>
                {n.user_phone && <p className="text-xs text-gray-400 mt-1 font-mono dir-ltr">{n.user_phone}</p>}
              </div>
              <button onClick={() => dismissNotification(idx)} className="text-gray-400 hover:text-white transition-colors"><X className="h-4 w-4" /></button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-6xl space-y-6">
        
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-[#d6ad60]/10 p-2 rounded-xl border border-[#d6ad60]/20 shadow-[0_0_15px_#d6ad6040]"><Crown className="h-6 w-6 text-[#d6ad60]" /></div>
            <div>
              <h1 className="text-2xl font-bold text-white">اتاق فرمان</h1>
              <p className="text-sm text-gray-400 flex items-center gap-2">
                خوش آمدید، {user.full_name || "مدیر"}
                <span className="flex items-center gap-1 text-[10px] ml-2">
                  <span className={`h-2 w-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
                  {connected ? "متصل" : "قطع"}
                </span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/"><Button variant="outline" size="sm" className="gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white"><Home className="h-4 w-4" /> صفحه اصلی</Button></Link>
            <Button variant="destructive" size="sm" onClick={() => { removeToken(); router.replace("/login"); }} className="gap-2"><LogOut className="h-4 w-4" /> خروج</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-4">
            <div className="bg-[#d6ad60]/10 p-3 rounded-xl text-[#d6ad60]"><Users className="h-6 w-6" /></div>
            <div><p className="text-xs text-gray-400">کل کاربران</p><p className="text-2xl font-bold text-white">{usersList.length}</p></div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-4">
            <div className="bg-green-500/10 p-3 rounded-xl text-green-500"><TrendingUp className="h-6 w-6" /></div>
            <div><p className="text-xs text-gray-400">کاربران فعال</p><p className="text-2xl font-bold text-white">{activeUsersCount}</p></div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-4">
            <div className="bg-yellow-500/10 p-3 rounded-xl text-yellow-500"><CreditCard className="h-6 w-6" /></div>
            <div><p className="text-xs text-gray-400">درخواست‌های در انتظار</p><p className="text-2xl font-bold text-white">{pendingCount}</p></div>
          </motion.div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4 border-b border-white/10 pb-2">
          <div className="flex gap-2 overflow-x-auto w-full md:w-auto">
            <Button variant={activeTab === "users" ? "default" : "ghost"} onClick={() => setActiveTab("users")} className={`gap-2 shrink-0 ${activeTab === "users" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><Users className="h-4 w-4" /> کاربران</Button>
            <Button variant={activeTab === "payments" ? "default" : "ghost"} onClick={() => setActiveTab("payments")} className={`gap-2 shrink-0 ${activeTab === "payments" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><CreditCard className="h-4 w-4" /> در انتظار</Button>
            <Button variant={activeTab === "transactions" ? "default" : "ghost"} onClick={() => setActiveTab("transactions")} className={`gap-2 shrink-0 ${activeTab === "transactions" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><History className="h-4 w-4" /> تراکنش‌ها</Button>
            <Button variant={activeTab === "tools" ? "default" : "ghost"} onClick={() => setActiveTab("tools")} className={`gap-2 shrink-0 ${activeTab === "tools" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><Wrench className="h-4 w-4" /> ابزارها</Button>
          </div>
          
          <div className="flex gap-2 w-full md:w-auto">
            <Button variant="outline" size="sm" onClick={() => setIsAddModalOpen(true)} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10 flex-1 md:flex-none"><UserPlus className="h-4 w-4" /> افزودن</Button>
            <Button variant="outline" size="sm" onClick={handleBackup} className="gap-2 border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10 flex-1 md:flex-none"><Download className="h-4 w-4" /> بک‌آپ</Button>
            <Button variant="outline" size="sm" onClick={handleExcel} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10 flex-1 md:flex-none"><Download className="h-4 w-4" /> اکسل</Button>
            <Button variant="outline" size="sm" onClick={handleRestore} className="gap-2 border-orange-500/30 text-orange-500 hover:bg-orange-500/10 flex-1 md:flex-none"><Upload className="h-4 w-4" /> بازگردانی</Button>
          </div>
        </div>

        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1"><Input placeholder="جستجوی شماره یا نام..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pr-4 pl-4 bg-[#0d1b2d] border-white/10 text-white h-11 rounded-xl" /></div>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="h-11 rounded-xl border border-white/10 bg-[#0d1b2d] px-4 text-sm text-white">
                <option value="all">همه ({usersList.length})</option>
                <option value="active">فعال ({activeUsersCount})</option>
                <option value="expired">منقضی ({usersList.length - activeUsersCount})</option>
              </select>
            </div>
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0d1b2dd0] shadow-xl backdrop-blur-xl">
                <table className="w-full text-sm text-right">
                  <thead className="bg-white/5 text-gray-400">
                    <tr>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('phone')}>شماره {sortConfig?.key === 'phone' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('full_name')}>نام {sortConfig?.key === 'full_name' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium">نقش</th>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('plan')}>پلن {sortConfig?.key === 'plan' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('end_date')}>اعتبار {sortConfig?.key === 'end_date' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('last_login')}>آخرین ورود {sortConfig?.key === 'last_login' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('created_at')}>عضویت {sortConfig?.key === 'created_at' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-3 py-3 font-medium">عملیات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {sortedUsers.length === 0 ? <tr><td colSpan={8} className="text-center py-8 text-gray-400">کاربری یافت نشد.</td></tr> : sortedUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-3 py-3 font-mono dir-ltr font-bold text-white text-xs">{u.phone}</td>
                        <td className="px-3 py-3 text-gray-300 text-xs">{u.full_name}</td>
                        <td className="px-3 py-3">{u.is_admin ? <span className="text-green-500 text-[10px] font-bold bg-green-500/10 px-2 py-1 rounded flex items-center gap-1 w-fit"><ShieldAlert className="h-3 w-3" /> مدیر</span> : <span className="text-gray-400 text-[10px]">کاربر</span>}</td>
                        <td className="px-3 py-3"><span className="bg-[#d6ad60]/10 text-[#d6ad60] px-2 py-1 rounded text-[10px] font-bold">{getPlanNameFa(u.plan)}</span></td>
                        <td className="px-3 py-3"><div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${statusDot(u.sub_status)}`} /><span className="text-[10px] text-gray-400">{u.is_admin ? "نامحدود" : formatFaDate(u.end_date)}</span></div></td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDateTime(u.last_login)}</td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDate(u.created_at)}</td>
                        <td className="px-3 py-3"><Button size="sm" variant="outline" className="text-[10px] h-7 gap-1 border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => openUserDetails(u)}><History className="h-3 w-3" /> جزئیات</Button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
                {activeTab === "payments" && (
          <div className="space-y-4">
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : payments.length === 0 ? <div className="text-center text-gray-400 py-10 bg-[#0d1b2dd0] rounded-2xl border border-white/10">هیچ درخواستی نیست.</div> : (
              payments.map((p) => (
                <motion.div key={p.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl border border-white/10 bg-[#0d1b2dd0] shadow-lg backdrop-blur-xl hover:border-[#d6ad60]/30 transition-colors">
                  <div className="w-full space-y-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="font-mono dir-ltr text-base font-bold bg-white/10 px-2 py-1 rounded text-white">{p.user_phone}</span>
                      <span className="text-xs bg-[#d6ad60]/10 text-[#d6ad60] px-3 py-1 rounded-full font-bold">{getPlanNameFa(p.plan)}</span>
                      <span className="text-xs text-gray-400 flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(p.created_at).toLocaleString('fa-IR')}</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-400 bg-black/20 p-3 rounded-lg border border-white/5">
                      <div className="flex items-center gap-2"><UserCheck className="h-4 w-4 text-blue-400" /><span>نام: {p.full_name}</span></div>
                      <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-yellow-400" /><span>زمان واریز: {p.payment_time}</span></div>
                      <div className="flex items-center gap-2"><Globe className="h-4 w-4 text-orange-400" /><span className="dir-ltr font-mono">{p.ip_address}</span></div>
                      <div className="flex items-center gap-2 truncate"><Monitor className="h-4 w-4 text-purple-400" /><span className="truncate" title={p.user_agent}>{p.user_agent}</span></div>
                    </div>
                    {p.receipt_note && <div className="text-xs bg-yellow-500/10 text-yellow-500 p-2 rounded-lg border border-yellow-500/20"><strong>توضیحات کاربر:</strong> {p.receipt_note}</div>}
                  </div>
                  <div className="flex gap-2 w-full md:w-auto shrink-0 pt-2 md:pt-0 border-t md:border-t-0 md:border-r border-white/10 md:pr-4">
                    <Button size="sm" className="flex-1 md:flex-none bg-green-600 hover:bg-green-700 text-white gap-1" onClick={() => handleAction(p.id, `/admin/payments/${p.id}/approve`, "پرداخت تایید شود؟")}><CheckCircle2 className="h-4 w-4" /> تایید</Button>
                    <Button size="sm" variant="destructive" className="flex-1 md:flex-none gap-1" onClick={() => handleAction(p.id, `/admin/payments/${p.id}/reject`, "پرداخت رد شود؟")}><XCircle className="h-4 w-4" /> رد</Button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {activeTab === "transactions" && (
          <div className="space-y-4">
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : transactions.length === 0 ? <div className="text-center text-gray-400 py-10 bg-[#0d1b2dd0] rounded-2xl border border-white/10">هیچ تراکنشی نیست.</div> : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0d1b2dd0] shadow-xl backdrop-blur-xl">
                <table className="w-full text-sm text-right">
                  <thead className="bg-white/5 text-gray-400">
                    <tr>
                      <th className="px-3 py-3">کاربر</th>
                      <th className="px-3 py-3">پلن</th>
                      <th className="px-3 py-3">مبلغ</th>
                      <th className="px-3 py-3">وضعیت</th>
                      <th className="px-3 py-3">تاریخ</th>
                      <th className="px-3 py-3">بررسی توسط</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {transactions.map((t) => (
                      <tr key={t.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-3 py-3 font-mono dir-ltr text-white text-xs">{t.user_phone}</td>
                        <td className="px-3 py-3 text-gray-300 text-xs">{getPlanNameFa(t.plan)}</td>
                        <td className="px-3 py-3 text-gray-300 text-xs">{t.amount?.toLocaleString('fa-IR')} تومان</td>
                        <td className="px-3 py-3">
                          <span className={t.status === "approved" ? "text-green-500" : t.status === "pending" ? "text-yellow-500" : "text-red-500"}>
                            {t.status === "approved" ? "تایید شده" : t.status === "pending" ? "در انتظار" : "رد شده"}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDateTime(t.created_at)}</td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{t.reviewed_by || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "tools" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-[#0d1b2dd0] p-6 shadow-xl backdrop-blur-xl">
              <h3 className="text-lg font-bold text-[#d6ad60] mb-4 flex items-center gap-2"><Wrench className="h-5 w-5" /> ابزارهای مدیریت (به‌زودی)</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { title: "پاکسازی کش تحلیل", desc: "پاک کردن حافظه موقت تحلیل‌ها" },
                  { title: "بازسازی آمار بک‌تست", desc: "اجرای مجدد محاسبات بک‌تست" },
                  { title: "ارسال پیام همگانی", desc: "ارسال پیامک به تمام کاربران" },
                  { title: "مدیریت واچ‌لیست", desc: "مشاهده و ویرایش واچ‌لیست کاربران" },
                  { title: "گزارش درآمد ماهانه", desc: "دریافت گزارش مالی ماهانه" },
                  { title: "لاگ فعالیت ادمین", desc: "مشاهده تاریخچه تغییرات" },
                ].map((tool, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-3 opacity-50 cursor-not-allowed">
                    <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><Wrench className="h-4 w-4" /></div>
                    <div>
                      <p className="text-xs font-bold text-white">{tool.title}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{tool.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* مدال افزودن کاربر */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white">
          <DialogHeader><DialogTitle className="text-[#d6ad60]">افزودن کاربر جدید</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><label className="text-xs text-gray-400">شماره موبایل</label><Input value={newUserPhone} onChange={e => setNewUserPhone(e.target.value)} className="bg-black/30 border-white/10 mt-1" dir="ltr" /></div>
            <div><label className="text-xs text-gray-400">نام</label><Input value={newUserName} onChange={e => setNewUserName(e.target.value)} className="bg-black/30 border-white/10 mt-1" /></div>
            <div><label className="text-xs text-gray-400">پلن</label>
              <select value={newUserPlan} onChange={e => setNewUserPlan(e.target.value)} className="w-full h-10 mt-1 rounded-md bg-black/30 border-white/10 text-sm px-2">
                <option value="free">رایگان</option>
                <option value="1_month">یک ماهه</option>
                <option value="3_months">سه ماهه</option>
                <option value="6_months">شش ماهه</option>
                <option value="12_months">یک ساله</option>
              </select>
            </div>
            <div><label className="text-xs text-gray-400">مدت (روز)</label><Input type="number" value={newUserDays} onChange={e => setNewUserDays(Number(e.target.value))} className="bg-black/30 border-white/10 mt-1" /></div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="sendSmsAdd" checked={newUserSendSms} onChange={e => setNewUserSendSms(e.target.checked)} className="accent-[#d6ad60]" />
              <label htmlFor="sendSmsAdd" className="text-xs text-gray-400">ارسال پیامک اطلاع‌رسانی</label>
            </div>
            <Button onClick={handleAddUser} className="w-full bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90">ثبت کاربر</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* مدال جزئیات */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-[#0d1b2d] border-white/10 text-white">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-[#d6ad60]"><UserCheck className="h-5 w-5" /> مدیریت کاربر: {selectedUser?.phone}</DialogTitle></DialogHeader>
          {userDetails ? (
            <div className="space-y-6 py-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-black/20 p-4 rounded-xl border border-white/5">
                <div><span className="text-gray-400">نام:</span> {userDetails.user.full_name || "نامشخص"}</div>
                <div><span className="text-gray-400">تاریخ عضویت:</span> {formatFaDate(userDetails.user.created_at)}</div>
                <div><span className="text-gray-400">آخرین ورود:</span> {formatFaDateTime(userDetails.user.last_login)}</div>
                <div><span className="text-gray-400">آخرین IP:</span> <span className="font-mono dir-ltr text-gray-300">{userDetails.user.last_ip}</span></div>
                <div className="sm:col-span-2"><span className="text-gray-400">مرورگر:</span> <span className="text-xs text-gray-300" title={userDetails.user.last_user_agent}>{userDetails.user.last_user_agent}</span></div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی پلن اشتراک:</h4>
                <div className="flex flex-wrap gap-2">
                  {["1_month", "3_months", "6_months", "12_months"].map((plan) => (
                    <Button key={plan} size="sm" variant="outline" className="border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => handleChangePlan(plan)}>{getPlanNameFa(plan)}</Button>
                  ))}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <input type="checkbox" id="sendSmsPlan" checked={sendSmsPlan} onChange={e => setSendSmsPlan(e.target.checked)} className="accent-[#d6ad60]" />
                  <label htmlFor="sendSmsPlan" className="text-[10px] text-gray-400">ارسال پیامک اطلاع‌رسانی</label>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی تاریخ انقضا:</h4>
                <div className="flex flex-wrap items-center gap-2">
                  <Input type="number" placeholder="مثلاً 30" value={adjustDays || ""} onChange={(e) => setAdjustDays(Number(e.target.value))} className="w-24 h-9 bg-black/30 border-white/10 text-white" />
                  <Button size="sm" variant="outline" onClick={handleAdjustDays} className="gap-1 text-green-500 border-green-500/20 hover:bg-green-500/10">اعمال روز</Button>
                  <span className="text-xs text-gray-500">(عدد منفی برای کاهش)</span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <input type="checkbox" id="sendSmsDays" checked={sendSmsDays} onChange={e => setSendSmsDays(e.target.checked)} className="accent-[#d6ad60]" />
                  <label htmlFor="sendSmsDays" className="text-[10px] text-gray-400">ارسال پیامک اطلاع‌رسانی</label>
                </div>
              </div>

              {user.phone === "09129630901" && (
                <div>
                  <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">مدیریت سطح دسترسی:</h4>
                  {selectedUser.is_admin ? (
                    selectedUser.phone !== "09129630901" && (
                      <Button size="sm" variant="destructive" onClick={() => handleAction(selectedUser.id, `/admin/users/${selectedUser.id}/remove-admin`, "دسترسی ادمین لغو شود؟")} className="gap-1"><ShieldAlert className="h-4 w-4" /> لغو دسترسی ادمین</Button>
                    )
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => handleAction(selectedUser.id, `/admin/users/${selectedUser.id}/make-admin`, "کاربر به مدیر ارتقا یابد؟")} className="gap-1 text-orange-500 border-orange-500/20 hover:bg-orange-500/10"><ShieldAlert className="h-4 w-4" /> ارتقا به مدیر</Button>
                  )}
                </div>
              )}

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">حذف کاربر:</h4>
                <div className="flex items-center gap-2 mb-2">
                  <input type="checkbox" id="deleteHard" checked={deleteHard} onChange={e => setDeleteHard(e.target.checked)} className="accent-red-500" />
                  <label htmlFor="deleteHard" className="text-[10px] text-red-400">حذف کامل (غیرقابل بازگشت)</label>
                </div>
                <Button size="sm" variant="destructive" onClick={handleDeleteUser} className="gap-1"><Trash2 className="h-4 w-4" /> حذف کاربر</Button>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه اشتراک‌ها:</h4>
                <div className="space-y-2">
                  {userDetails.subscriptions.length === 0 ? <p className="text-xs text-gray-500">ندارد</p> : userDetails.subscriptions.map((s: any) => (
                    <div key={s.id} className="text-xs flex justify-between items-center bg-white/5 p-2 rounded border border-white/5">
                      <span className="font-bold text-gray-200">{getPlanNameFa(s.plan)}</span>
                      <span className="text-gray-400">تا {s.end ? formatFaDate(s.end) : "نامحدود"}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه پرداخت‌ها:</h4>
                <div className="space-y-2">
                  {userDetails.payments.length === 0 ? <p className="text-xs text-gray-500">ندارد</p> : userDetails.payments.map((p: any) => (
                    <div key={p.id} className="text-xs flex justify-between items-center bg-white/5 p-2 rounded border border-white/5">
                      <span className="text-gray-200">{getPlanNameFa(p.plan)}</span>
                      <span className={p.status === "approved" ? "text-green-500" : p.status === "pending" ? "text-yellow-500" : "text-red-500"}>{p.status === "approved" ? "تایید شده" : p.status === "pending" ? "در انتظار" : "رد شده"}</span>
                      <span className="text-gray-400">{formatFaDate(p.created_at)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-10">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#d6ad60]"></div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* مدال تایید سفارشی */}
      <Dialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white max-w-md">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-[#d6ad60]"><AlertTriangle className="h-5 w-5" /> تایید عملیات</DialogTitle></DialogHeader>
          <p className="text-sm text-gray-300 py-4">{confirmAction?.message}</p>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setIsConfirmOpen(false)} className="border-white/10 text-gray-300">لغو</Button>
            <Button onClick={executeAction} className="bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90">تایید</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Footer />
    </div>
  );
}