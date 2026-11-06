"use client";

import { useEffect, useState, useMemo } from "react";
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
  UserPlus, Trash2, Wrench, AlertTriangle, MessageSquare, Database,
  Search, Pencil, DollarSign, Wallet, Receipt, Lock, RefreshCw, UserX, UserCheck2, Hourglass
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAdminNotifications } from "@/hooks/useAdminNotifications";
import Link from "next/link";
import { RestoreGuide } from "@/components/admin/RestoreGuide";


const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "1_month": "یک ماهه", "3_months": "سه ماهه", "6_months": "شش ماهه", "12_months": "یک ساله",
    "free": "رایگان", "monthly": "ماهانه", "بدون اشتراک": "بدون اشتراک", "نامحدود (مدیر)": "نامحدود (مدیر)",
    "refund": "عودت وجه"
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

const paymentMethodLabel = (m: string | null | undefined) => {
  if (!m) return "—";
  if (m === "zibal") return "درگاه زیبال";
  if (m === "card") return "کارت به کارت";
  if (m === "refund") return "عودت وجه";
  return m;
};

const paymentStatusBadge = (s: string) => {
  switch (s) {
    case "approved": return { text: "تایید شده", color: "text-green-500 bg-green-500/10 border-green-500/20" };
    case "pending": return { text: "در حال بررسی", color: "text-yellow-500 bg-yellow-500/10 border-yellow-500/20" };
    case "rejected": return { text: "رد شده", color: "text-red-500 bg-red-500/10 border-red-500/20" };
    case "refunded": return { text: "عودت شده", color: "text-purple-500 bg-purple-500/10 border-purple-500/20" };
    default: return { text: s, color: "text-gray-400 bg-white/5 border-white/10" };
  }
};

type TabKey = "users" | "payments" | "transactions" | "tools" | "zibal" | "refunds";

export default function AdminPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("users");
  const [payments, setPayments] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [refunds, setRefunds] = useState<any[]>([]);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [ticketStats, setTicketStats] = useState<any>(null);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [txSearchQuery, setTxSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "expired" | "inactive">("all");
  const [stats, setStats] = useState<any>(null);

  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userDetails, setUserDetails] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [adjustDays, setAdjustDays] = useState<number>(0);
  const [sendSmsPlan, setSendSmsPlan] = useState(true);
  const [sendSmsDays, setSendSmsDays] = useState(true);

  // 🔴 استیت‌های ریست رمز
  const [newPasswordForUser, setNewPasswordForUser] = useState("");
  const [extStats, setExtStats] = useState<any>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newUserPhone, setNewUserPhone] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserPlan, setNewUserPlan] = useState("1_month");
  const [newUserDays, setNewUserDays] = useState(30);
  const [newUserSendSms, setNewUserSendSms] = useState(true);
  const [isMaintenance, setIsMaintenance] = useState(false);
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ type: 'delete' | 'admin' | 'action' | 'delete_backups', id?: number, endpoint?: string, message: string, backupNames?: string[] } | null>(null);
  const [deleteHard, setDeleteHard] = useState(false);
  
  // 🔴 استیت‌های مودال یادداشت (تایید/رد)
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [noteAction, setNoteAction] = useState<{ type: "approve" | "reject", id: number } | null>(null);
  const [noteText, setNoteText] = useState("");
  const [noteLoading, setNoteLoading] = useState(false);

  // 🔴 استیت‌های مدال جزئیات تراکنش
  const [isTxDetailOpen, setIsTxDetailOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<any>(null);
  const [txNewAmount, setTxNewAmount] = useState<number>(0);
  const [txNewStatus, setTxNewStatus] = useState<string>("pending");
  const [txNewNote, setTxNewNote] = useState<string>("");
  const [txSendSms, setTxSendSms] = useState(true);
  const [txDetailLoading, setTxDetailLoading] = useState(false);

  // 🔴 استیت‌های ثبت عودت
  const [isRefundModalOpen, setIsRefundModalOpen] = useState(false);
  const [refundNewPlan, setRefundNewPlan] = useState("no_change");
  const [refundAmount, setRefundAmount] = useState(0);
  const [refundNote, setRefundNote] = useState("");
  const [refundLoading, setRefundLoading] = useState(false);

  const [notifications, setNotifications] = useState<any[]>([]);
  const [backups, setBackups] = useState<any[]>([]);
  const [selectedBackups, setSelectedBackups] = useState<string[]>([]);
  const [backupLoading, setBackupLoading] = useState(false);
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

  const fetchTicketStats = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/stats`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setTicketStats(await res.json());
    } catch {}
  };

  const fetchMaintenanceStatus = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/maintenance`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setIsMaintenance(data.is_maintenance);
      }
    } catch {}
  };

  const fetchBackups = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/backups`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setBackups(data.items || []);
      }
    } catch {}
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/dashboard-stats`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setStats(await res.json());
    } catch {}
  };

  useEffect(() => {
    fetch(`${apiUrl}/admin/payments`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json()).then(data => setPendingCount((data.items || []).length)).catch(() => {});
    fetchTicketStats();
    fetchBackups();
    fetchMaintenanceStatus();
    fetchStats();
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
        const res = await fetch(`${apiUrl}/admin/all-transactions`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setTransactions(data.items || []);
      } else if (activeTab === "users") {
        const res = await fetch(`${apiUrl}/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setUsersList(data.items || []);
      } else if (activeTab === "refunds") {
        const res = await fetch(`${apiUrl}/admin/refunds`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setRefunds(data.items || []);
      }
      fetchStats();
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const { connected } = useAdminNotifications((n) => {
    setNotifications((prev) => [n, ...prev].slice(0, 5));
    fetchData();
    if (n.type === "new_ticket" || n.type === "ticket_reply") fetchTicketStats();
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
      if (statusFilter === "inactive") return u.is_active === false;
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

  const filteredTransactions = useMemo(() => {
    if (!txSearchQuery.trim()) return transactions;
    const q = txSearchQuery.toLowerCase();
    return transactions.filter(t =>
      (t.user_phone || "").includes(q) ||
      (t.plan || "").toLowerCase().includes(q) ||
      (t.status || "").toLowerCase().includes(q) ||
      (t.id || "").toLowerCase().includes(q) ||
      (t.payment_method || "").toLowerCase().includes(q) ||
      (t.admin_note || "").toLowerCase().includes(q) ||
      (t.receipt_note || "").toLowerCase().includes(q)
    );
  }, [transactions, txSearchQuery]);

  const requestSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const openUserDetails = async (u: any) => {
    setSelectedUser(u); setIsModalOpen(true); setUserDetails(null); setAdjustDays(0); setNewPasswordForUser("");
    try {
      const res = await fetch(`${apiUrl}/admin/users/${u.id}/details`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (res.ok) setUserDetails(data);
      
      fetch(`${apiUrl}/admin/users/${u.id}/extension-stats`, { headers: { Authorization: `Bearer ${token}` } })
        .then(res => res.ok ? res.json() : null)
        .then(stats => setExtStats(stats))
        .catch(console.error);
    } catch (err) { console.error(err); }
  };

  const requestConfirm = (type: 'delete' | 'admin' | 'action' | 'delete_backups', message: string, id?: number, endpoint?: string, backupNames?: string[]) => {
    setConfirmAction({ type, id, endpoint, message, backupNames });
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
      } else if (confirmAction.type === 'delete_backups' && confirmAction.backupNames) {
        const res = await fetch(`${apiUrl}/admin/backups/delete`, { 
          method: "POST", 
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ names: confirmAction.backupNames })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
        setSelectedBackups([]);
        fetchBackups();
      } else if (confirmAction.endpoint) {
        const res = await fetch(`${apiUrl}${confirmAction.endpoint}`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);

        // 🔴 بعد از هر عملیات، دیتای مدال رو دوباره بخون (مطمئن‌ترین راه)
        if (selectedUser) {
          try {
            const detailsRes = await fetch(`${apiUrl}/admin/users/${selectedUser.id}/details`, { headers: { Authorization: `Bearer ${token}` } });
            const detailsData = await detailsRes.json();
            if (detailsRes.ok) setUserDetails(detailsData);
          } catch (e) { console.error(e); }
        }

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

  const handleResetPassword = () => {
    if (!newPasswordForUser || newPasswordForUser.length < 6) return alert("رمز جدید باید حداقل ۶ حرف باشد");
    requestConfirm('action', "رمز عبور کاربر ریست شود؟", selectedUser.id, `/admin/users/${selectedUser.id}/reset-password?new_password=${newPasswordForUser}`);
  };

  const handleActivateUser = () => {
    requestConfirm('action', "کاربر فعال شود؟", selectedUser.id, `/admin/users/${selectedUser.id}/activate`);
  };

  const handleDeleteUser = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/users/${selectedUser.id}/ticket-count`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      
      if (data.count > 0) {
        if (!confirm(`⚠️ این کاربر ${data.count} تیکت دارد. با حذف کاربر، تمام تیکت‌ها و پیام‌های آن‌ها هم پاک می‌شوند. مطمئنی؟`)) return;
      }
      
      requestConfirm('delete', deleteHard ? "کاربر و تمام داده‌های مرتبط برای همیشه حذف شوند؟" : "کاربر غیرفعال شود؟ (قابل بازگشت)", selectedUser.id);
    } catch {
      requestConfirm('delete', deleteHard ? "کاربر و تمام داده‌های مرتبط برای همیشه حذف شوند؟" : "کاربر غیرفعال شود؟ (قابل بازگشت)", selectedUser.id);
    }
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

  const toggleMaintenance = async (enable: boolean) => {
    if (enable && !confirm("آیا مطمئنید؟ سایت برای همه کاربران غیرفعال می‌شود.")) return;
    setMaintenanceLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/maintenance/${enable ? "enable" : "disable"}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setIsMaintenance(enable);
      alert(data.message);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setMaintenanceLoading(false);
    }
  };

  const handleBackup = async () => {
    setBackupLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/backup`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "خطا در بک‌آپ");
      }
      
      alert(`✅ بک‌آپ "${data.name}" با موفقیت ساخته شد.\n\nحجم: ${(data.size / 1024).toFixed(1)} KB`);
      fetchBackups();
    } catch (err: any) {
      console.error("Backup error:", err);
      alert(err.message || "خطا در بک‌آپ");
    } finally {
      setBackupLoading(false);
    }
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

  const handleTxExcel = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/transactions/excel`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error("خطا");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `trademun-transactions-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.xlsx`; a.click();
    } catch (err) { alert("خطا در خروجی اکسل"); }
  };

  const openTxDetail = (tx: any) => {
    setSelectedTx(tx);
    setTxNewAmount(tx.amount || 0);
    setTxNewStatus(tx.status);
    setTxNewNote(tx.admin_note || "");
    setTxSendSms(true);
    setIsTxDetailOpen(true);
  };

  const saveTxDetail = async () => {
    if (!selectedTx) return;
    setTxDetailLoading(true);
    try {
      // ۱. تغییر مبلغ
      if (txNewAmount !== selectedTx.amount) {
        await fetch(`${apiUrl}/admin/transactions/${selectedTx.id}/amount?amount=${txNewAmount}`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
      
      // ۲. تغییر وضعیت
      if (txNewStatus !== selectedTx.status) {
        await fetch(`${apiUrl}/admin/transactions/${selectedTx.id}/status?new_status=${txNewStatus}&send_sms=${txSendSms}`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        });
      }

      // ۳. 🔴 ذخیره یادداشت (اگه تغییر کرده بود)
      if (txNewNote !== selectedTx.admin_note) {
        await fetch(`${apiUrl}/admin/transactions/${selectedTx.id}/note`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ admin_note: txNewNote }),
        });
      }
      
      alert("تغییرات با موفقیت ذخیره شد");
      setIsTxDetailOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setTxDetailLoading(false);
    }
  };

  const handleApproveWithNote = async () => {
    if (!noteAction) return;
    setNoteLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/payments/${noteAction.id}/${noteAction.type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ admin_note: noteText }), 
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا");
      alert(data.message);
      setIsNoteModalOpen(false);
      setNoteText("");
      fetchData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setNoteLoading(false);
    }
  };

  const handleCreateRefund = async () => {
    setRefundLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/users/${selectedUser.id}/refund`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          new_plan: refundNewPlan,
          refund_amount: refundAmount,
          admin_note: refundNote || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا");
      alert(data.message);
      setIsRefundModalOpen(false);
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setRefundLoading(false);
    }
  };

  const toggleBackupSelection = (name: string) => {
    setSelectedBackups(prev => 
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const toggleAllBackups = () => {
    if (selectedBackups.length === backups.length) {
      setSelectedBackups([]);
    } else {
      setSelectedBackups(backups.map(b => b.name));
    }
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

        {/* ۴ کارت اول */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <button
            onClick={() => setActiveTab("users")}
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] hover:from-[#14263e] hover:to-[#0d1b2d] transition-all p-3 sm:p-5 rounded-2xl border border-white/10 hover:border-[#d6ad60]/40 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-[#d6ad60]/10 p-2 sm:p-3 rounded-xl text-[#d6ad60]"><Users className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div><p className="text-[10px] sm:text-xs text-gray-400">کل کاربران</p><p className="text-lg sm:text-2xl font-bold text-white">{usersList.length}</p></div>
          </button>
          
          <button
            onClick={() => setActiveTab("users")}
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] hover:from-[#14263e] hover:to-[#0d1b2d] transition-all p-3 sm:p-5 rounded-2xl border border-white/10 hover:border-[#d6ad60]/40 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-green-500/10 p-2 sm:p-3 rounded-xl text-green-500"><TrendingUp className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div><p className="text-[10px] sm:text-xs text-gray-400">کاربران فعال</p><p className="text-lg sm:text-2xl font-bold text-white">{activeUsersCount}</p></div>
          </button>
          
          <button
            onClick={() => setActiveTab("payments")}
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] hover:from-[#14263e] hover:to-[#0d1b2d] transition-all p-3 sm:p-5 rounded-2xl border border-white/10 hover:border-[#d6ad60]/40 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-yellow-500/10 p-2 sm:p-3 rounded-xl text-yellow-500"><CreditCard className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div><p className="text-[10px] sm:text-xs text-gray-400">درخواست‌های در انتظار</p><p className="text-lg sm:text-2xl font-bold text-white">{pendingCount}</p></div>
          </button>

          <Link href="/admin/tickets">
            <div className="group bg-gradient-to-br from-[#0d1b2d] to-[#07111f] hover:from-[#1a2c45] hover:to-[#0d1b2d] transition-all p-3 sm:p-5 rounded-2xl border border-white/10 hover:border-[#d6ad60]/40 shadow-xl flex items-center gap-2 sm:gap-4 cursor-pointer relative overflow-hidden w-full text-right">
              {ticketStats?.unread_count > 0 && (
                 <div className="absolute top-0 right-0 w-12 h-12 sm:w-16 sm:h-16 bg-[#d6ad60]/10 rounded-bl-full flex items-start justify-end p-1.5 sm:p-2">
                   <span className="animate-pulse w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[#d6ad60]"></span>
                 </div>
              )}
              <div className="bg-blue-500/10 p-2 sm:p-3 rounded-xl text-blue-400 group-hover:scale-110 transition-transform"><MessageSquare className="h-4 w-4 sm:h-6 sm:w-6" /></div>
              <div className="flex-1">
                <p className="text-[10px] sm:text-xs text-gray-400">تیکت‌ها</p>
                <div className="flex items-center gap-1.5 sm:gap-2 mt-0.5">
                  <p className="text-lg sm:text-2xl font-bold text-white">{ticketStats?.open_count || 0} <span className="text-[10px] sm:text-sm font-normal text-gray-500">باز</span></p>
                  {ticketStats?.unread_count > 0 && (
                    <span className="bg-[#d6ad60] text-[#101827] text-[8px] sm:text-[10px] font-bold px-1.5 py-0.5 rounded-full">{ticketStats.unread_count} جدید</span>
                  )}
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* ۴ کارت مالی */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.5 }} 
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 sm:p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-green-500/10 p-2 sm:p-3 rounded-xl text-green-500"><TrendingUp className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div>
              <p className="text-[10px] sm:text-xs text-gray-400">درآمد کل</p>
              <p className="text-sm sm:text-xl font-bold text-white" dir="ltr">
                {(stats?.total_revenue || 0).toLocaleString("fa-IR")}
                <span className="text-[8px] sm:text-[10px] text-gray-500 mr-1">ت</span>
              </p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.6 }} 
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 sm:p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-purple-500/10 p-2 sm:p-3 rounded-xl text-purple-500"><RefreshCw className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div>
              <p className="text-[10px] sm:text-xs text-gray-400">جمع عودت‌ها</p>
              <p className="text-sm sm:text-xl font-bold text-white" dir="ltr">
                {(stats?.total_refunded || 0).toLocaleString("fa-IR")}
                <span className="text-[8px] sm:text-[10px] text-gray-500 mr-1">ت</span>
              </p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.7 }} 
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 sm:p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-blue-500/10 p-2 sm:p-3 rounded-xl text-blue-500"><DollarSign className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div>
              <p className="text-[10px] sm:text-xs text-gray-400">درآمد خالص</p>
              <p className="text-sm sm:text-xl font-bold text-white" dir="ltr">
                {(stats?.net_revenue || 0).toLocaleString("fa-IR")}
                <span className="text-[8px] sm:text-[10px] text-gray-500 mr-1">ت</span>
              </p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: 0.8 }} 
            className="text-right bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 sm:p-5 rounded-2xl border border-white/10 shadow-xl flex items-center gap-2 sm:gap-4"
          >
            <div className="bg-yellow-500/10 p-2 sm:p-3 rounded-xl text-yellow-500"><Hourglass className="h-4 w-4 sm:h-6 sm:w-6" /></div>
            <div>
              <p className="text-[10px] sm:text-xs text-gray-400">درخواست‌های عودت</p>
              <p className="text-lg sm:text-xl font-bold text-white">
                {stats?.pending_refunds || 0}
                <span className="text-[8px] sm:text-[10px] text-gray-500 mr-1">مورد</span>
              </p>
            </div>
          </motion.div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4 border-b border-white/10 pb-2">
          <div className="flex gap-2 overflow-x-auto w-full md:w-auto">
            <Button variant={activeTab === "users" ? "default" : "ghost"} onClick={() => setActiveTab("users")} className={`gap-2 shrink-0 ${activeTab === "users" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><Users className="h-4 w-4" /> کاربران</Button>
            <Button variant={activeTab === "payments" ? "default" : "ghost"} onClick={() => setActiveTab("payments")} className={`gap-2 shrink-0 ${activeTab === "payments" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><CreditCard className="h-4 w-4" /> در انتظار</Button>
            <Button variant={activeTab === "transactions" ? "default" : "ghost"} onClick={() => setActiveTab("transactions")} className={`gap-2 shrink-0 ${activeTab === "transactions" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><History className="h-4 w-4" /> تراکنش‌ها</Button>
            <Button variant={activeTab === "refunds" ? "default" : "ghost"} onClick={() => setActiveTab("refunds")} className={`gap-2 shrink-0 ${activeTab === "refunds" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              <RefreshCw className="h-4 w-4" /> عودت‌ها
            </Button>
            <Button variant="ghost" onClick={() => setActiveTab("zibal")} className={`gap-2 shrink-0 ${activeTab === "zibal" ? "bg-[#d6ad60] text-[#101827]" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              <Wallet className="h-4 w-4" /> زیبال <span className="text-[8px] bg-yellow-500/20 text-yellow-400 px-1 rounded">به زودی</span>
            </Button>
            
            <Link href="/admin/tickets">
              <Button variant="ghost" className="gap-2 shrink-0 text-gray-400 hover:text-white hover:bg-white/5"><MessageSquare className="h-4 w-4" /> تیکت‌ها</Button>
            </Link>

            <Button variant={activeTab === "tools" ? "default" : "ghost"} onClick={() => setActiveTab("tools")} className={`gap-2 shrink-0 ${activeTab === "tools" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><Wrench className="h-4 w-4" /> ابزارها</Button>
          </div>
        </div>

        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2 justify-between">
              <div className="flex flex-col sm:flex-row gap-2 flex-1">
                <div className="relative flex-1">
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <Input placeholder="جستجوی شماره یا نام..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pr-10 pl-4 bg-[#0d1b2d] border-white/10 text-white h-11 rounded-xl" />
                </div>
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="h-11 rounded-xl border border-white/10 bg-[#0d1b2d] px-4 text-sm text-white">
                  <option value="all">همه ({usersList.length})</option>
                  <option value="active">فعال ({activeUsersCount})</option>
                  <option value="expired">منقضی ({usersList.length - activeUsersCount})</option>
                  <option value="inactive">غیرفعال ({usersList.filter(u => u.is_active === false).length})</option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setIsAddModalOpen(true)} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10 h-11 px-4"><UserPlus className="h-4 w-4" /> افزودن</Button>
                <Button variant="outline" size="sm" onClick={handleExcel} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10 h-11 px-4"><Download className="h-4 w-4" /> اکسل</Button>
              </div>
            </div>
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                <table className="w-full text-sm text-right">
                  <thead className="bg-white/5 text-gray-400">
                    <tr><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('phone')}>شماره {sortConfig?.key === 'phone' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('full_name')}>نام {sortConfig?.key === 'full_name' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium">نقش</th><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('plan')}>پلن {sortConfig?.key === 'plan' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('end_date')}>اعتبار {sortConfig?.key === 'end_date' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('last_login')}>آخرین ورود {sortConfig?.key === 'last_login' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('created_at')}>عضویت {sortConfig?.key === 'created_at' && <ArrowUpDown className="inline h-3 w-3" />}</th><th className="px-3 py-3 font-medium">عملیات</th></tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {sortedUsers.length === 0 ? <tr><td colSpan={8} className="text-center py-8 text-gray-400">کاربری یافت نشد.</td></tr> : sortedUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-3 py-3 font-mono dir-ltr font-bold text-white text-xs">{u.phone}</td>
                        <td className="px-3 py-3 text-gray-300 text-xs">{u.full_name}</td>
                        <td className="px-3 py-3">
                          {u.is_admin ? (
                            <span className="text-green-500 text-[10px] font-bold bg-green-500/10 px-2 py-1 rounded flex items-center gap-1 w-fit">
                              <ShieldAlert className="h-3 w-3" /> مدیر
                            </span>
                          ) : u.is_active === false ? (
                            <span className="text-gray-500 text-[10px] font-bold bg-gray-500/10 px-2 py-1 rounded flex items-center gap-1 w-fit">
                              <span className="h-2 w-2 rounded-full bg-gray-500" /> غیرفعال
                            </span>
                          ) : (
                            <span className="text-gray-400 text-[10px]">کاربر</span>
                          )}
                        </td>
                        <td className="px-3 py-3"><span className="bg-[#d6ad60]/10 text-[#d6ad60] px-2 py-1 rounded text-[10px] font-bold">{getPlanNameFa(u.plan)}</span></td>
                        <td className="px-3 py-3"><div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${statusDot(u.sub_status)}`} /><span className="text-[10px] text-gray-400">{u.is_admin ? "نامحدود" : formatFaDate(u.end_date)}</span></div></td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDateTime(u.last_login)}</td>
                        <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDate(u.created_at)}</td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-2">
                            {u.extension_downloaded && (
                              <span title="افزونه را دانلود کرده" className="flex items-center justify-center h-5 w-5 rounded-full bg-green-500/20 text-green-500">
                                <CheckCircle2 className="h-3 w-3" />
                              </span>
                            )}
                            <Button size="sm" variant="outline" className="text-[10px] h-7 gap-1 border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => openUserDetails(u)}>
                              <History className="h-3 w-3" /> جزئیات
                            </Button>
                          </div>
                        </td>
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
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : payments.length === 0 ? <div className="text-center text-gray-400 py-10 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10">هیچ درخواستی نیست.</div> : (
              payments.map((p) => (
                <motion.div key={p.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-lg hover:border-[#d6ad60]/30 transition-colors">
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
                    <Button size="sm" className="flex-1 md:flex-none bg-green-600 hover:bg-green-700 text-white gap-1" onClick={() => { setNoteAction({ type: "approve", id: p.id }); setIsNoteModalOpen(true); }}><CheckCircle2 className="h-4 w-4" /> تایید</Button>
                    <Button size="sm" variant="destructive" className="flex-1 md:flex-none gap-1" onClick={() => { setNoteAction({ type: "reject", id: p.id }); setIsNoteModalOpen(true); }}><XCircle className="h-4 w-4" /> رد</Button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {activeTab === "transactions" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2 justify-between">
              <div className="relative flex-1">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <Input 
                  placeholder="جستجو در شماره، پلن، وضعیت، روش پرداخت..." 
                  value={txSearchQuery} 
                  onChange={(e) => setTxSearchQuery(e.target.value)} 
                  className="pr-10 pl-4 bg-[#0d1b2d] border-white/10 text-white h-11 rounded-xl" 
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleTxExcel} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10 h-11 px-4">
                  <Download className="h-4 w-4" /> اکسل
                </Button>
              </div>
            </div>

            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : filteredTransactions.length === 0 ? (
              <div className="text-center text-gray-400 py-10 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10">هیچ تراکنشی نیست.</div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                <table className="w-full text-sm text-right">
                  <thead className="bg-white/5 text-gray-400">
                    <tr><th className="px-3 py-3 font-medium">شناسه</th><th className="px-3 py-3 font-medium">کاربر</th><th className="px-3 py-3 font-medium">پلن</th><th className="px-3 py-3 font-medium">روش پرداخت</th><th className="px-3 py-3 font-medium">مبلغ</th><th className="px-3 py-3 font-medium">وضعیت</th><th className="px-3 py-3 font-medium">تاریخ درخواست</th><th className="px-3 py-3 font-medium">تاریخ تایید</th><th className="px-3 py-3 font-medium">یادداشت</th><th className="px-3 py-3 font-medium">عملیات</th></tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredTransactions.map((t) => {
                      const st = paymentStatusBadge(t.status);
                      const MethodIcon = t.payment_method === "zibal" ? Wallet : (t.payment_method === "refund" ? RefreshCw : CreditCard);
                      const isRefund = t.payment_method === "refund" || t.plan === "refund";
                      return (
                        <tr key={t.id} className="hover:bg-white/5 transition-colors">
                          <td className="px-3 py-3 font-mono text-[10px] text-gray-500">{t.id}</td>
                          <td className="px-3 py-3 font-mono dir-ltr text-white text-xs">{t.user_phone}</td>
                          <td className={`px-3 py-3 text-xs ${isRefund ? "text-purple-400 font-bold" : "text-gray-300"}`}>{getPlanNameFa(t.plan)}</td>
                          <td className="px-3 py-3"><span className="inline-flex items-center gap-1 text-[10px] text-gray-300"><MethodIcon className="h-3 w-3" /> {paymentMethodLabel(t.payment_method)}</span></td>
                          <td className="px-3 py-3 text-white text-xs font-bold" dir="ltr">{(t.amount || 0).toLocaleString("fa-IR")}<span className="text-[9px] text-gray-500 mr-1">ت</span></td>
                          <td className="px-3 py-3"><span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${st.color}`}>{st.text}</span></td>
                          <td className="px-3 py-3 text-gray-400 text-[10px]">{formatFaDateTime(t.created_at)}</td>
                          <td className="px-3 py-3 text-gray-400 text-[10px]">{t.reviewed_at ? formatFaDateTime(t.reviewed_at) : "—"}</td>
                          <td className="px-3 py-3 text-gray-400 text-[10px] max-w-[150px] truncate" title={t.admin_note}>{t.admin_note || "—"}</td>   
                          <td className="px-3 py-3">
                            <Button size="sm" variant="outline" onClick={() => openTxDetail(t)} className="h-7 text-[10px] gap-1 border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10">
                              <Pencil className="h-3 w-3" /> ویرایش / جزئیات
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}


        {activeTab === "refunds" && (
          <div className="space-y-3">
            {loading ? (
              <p className="text-center text-gray-400 py-4">در حال دریافت...</p>
            ) : refunds.length === 0 ? (
              <div className="text-center text-gray-400 py-10 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10">
                هیچ درخواست عودتی نیست.
              </div>
            ) : (
              refunds.map((r) => (
                <motion.div 
                  key={r.id} 
                  initial={{ opacity: 0, y: 10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 p-4 rounded-2xl border border-purple-500/30 bg-gradient-to-br from-[#1a1635] to-[#0d0b1f] shadow-lg"
                >
                  {/* سمت راست: اطلاعات */}
                  <div className="flex-1 w-full min-w-0 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="bg-purple-500/15 p-1.5 rounded-lg border border-purple-500/25">
                        <RefreshCw className="h-3.5 w-3.5 text-purple-400" />
                      </div>
                      <span className="font-mono dir-ltr text-sm font-bold text-white">{r.user_phone}</span>
                      <span className="text-[10px] bg-[#d6ad60]/10 text-[#d6ad60] px-2 py-0.5 rounded-full font-bold">
                        {getPlanNameFa(r.old_plan)} → {getPlanNameFa(r.new_plan)}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                        r.status === "refunded" ? "text-purple-400 bg-purple-500/10 border-purple-500/20" :
                        r.status === "rejected" ? "text-red-400 bg-red-500/10 border-red-500/20" :
                        "text-yellow-400 bg-yellow-500/10 border-yellow-500/20"
                      }`}>
                        {r.status === "refunded" ? "✓ عودت شده" : r.status === "rejected" ? "✗ رد شده" : "⏳ در حال بررسی"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-gray-400 flex-wrap">
                      <span>مبلغ عودت: <b className="text-purple-400" dir="ltr">{r.refund_amount.toLocaleString("fa-IR")} تومان</b></span>
                      <span>تاریخ: <b className="text-white">{formatFaDateTime(r.created_at)}</b></span>
                    </div>
                    {r.admin_note && (
                      <div className="text-[10px] text-yellow-500 bg-yellow-500/10 p-1.5 rounded border border-yellow-500/20">
                        <b>توضیحات:</b> {r.admin_note}
                      </div>
                    )}
                  </div>

                  {/* سمت چپ: دکمه‌ها */}
                  {r.status === "pending" && (
                    <div className="flex gap-2 w-full md:w-auto shrink-0 pt-2 md:pt-0 border-t md:border-t-0 md:border-r border-white/10 md:pr-3">
                      <Button 
                        size="sm" 
                        onClick={() => { 
                          setConfirmAction({ type: 'action', message: "تایید عودت وجه؟", endpoint: `/admin/refunds/${r.id}/approve` }); 
                          setIsConfirmOpen(true); 
                        }} 
                        className="flex-1 md:flex-none bg-purple-600 hover:bg-purple-700 text-white gap-1 h-8 text-xs"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> تایید
                      </Button>
                      <Button 
                        size="sm" 
                        variant="destructive" 
                        onClick={() => { 
                          setConfirmAction({ type: 'action', message: "رد درخواست عودت؟", endpoint: `/admin/refunds/${r.id}/reject` }); 
                          setIsConfirmOpen(true); 
                        }} 
                        className="flex-1 md:flex-none gap-1 h-8 text-xs"
                      >
                        <XCircle className="h-3.5 w-3.5" /> رد
                      </Button>
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </div>
        )}

        {activeTab === "zibal" && (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-10 text-center">
            <Wallet className="h-12 w-12 text-gray-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-white mb-2">اتصال به درگاه زیبال</h3>
            <p className="text-xs text-gray-400 leading-relaxed max-w-md mx-auto mb-4">این تب برای بررسی و تطبیق تراکنش‌های درگاه زیبال با سیستم است. پس از راه‌اندازی درگاه، تراکنش‌ها به‌طور خودکار اینجا نمایش داده می‌شوند.</p>
            <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-1.5"><Clock className="h-3.5 w-3.5 text-yellow-400" /><span className="text-[10px] text-yellow-400 font-bold">در حال توسعه</span></div>
          </div>
        )}

        {activeTab === "tools" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 shadow-xl">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
                <h3 className="text-base font-bold text-[#d6ad60] flex items-center gap-2"><Database className="h-5 w-5" /> بک‌آپ</h3>
                <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                  <Button onClick={handleBackup} disabled={backupLoading} size="sm" className="gap-1 bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90 font-bold">{backupLoading ? "..." : <><Download className="h-3 w-3" /> بک‌آپ جدید</>}</Button>
                  <RestoreGuide backups={backups} />
                </div>
              </div>
              {backups.length === 0 ? <p className="text-gray-500 text-xs text-center py-2">هنوز بک‌آپی ساخته نشده.</p> : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  <label className="flex items-center gap-2 text-[10px] text-gray-500 cursor-pointer mb-1"><input type="checkbox" checked={selectedBackups.length === backups.length && backups.length > 0} onChange={toggleAllBackups} className="accent-[#d6ad60]" />انتخاب همه</label>
                  {backups.map((b) => (
                    <div key={b.name} className={`flex items-center justify-between gap-2 rounded-lg border ${selectedBackups.includes(b.name) ? "border-[#d6ad60]/50 bg-[#d6ad60]/10" : "border-white/5 bg-white/5"} px-3 py-2`}>
                      <div className="flex items-center gap-2 min-w-0 flex-1"><input type="checkbox" checked={selectedBackups.includes(b.name)} onChange={() => toggleBackupSelection(b.name)} className="accent-[#d6ad60] h-3 w-3" /><p className="text-[11px] text-gray-300 truncate dir-ltr">{b.name}</p></div>
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-gray-400 hover:text-[#d6ad60]" onClick={async () => { try { const res = await fetch(`${apiUrl}/admin/backups/${b.name}/download`, { headers: { Authorization: `Bearer ${token}` } }); if (!res.ok) throw new Error("دانلود ناموفق"); const blob = await res.blob(); const url = window.URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = b.name; a.click(); window.URL.revokeObjectURL(url); } catch (err: any) { alert(err.message || "خطا در دانلود"); } }}><Download className="h-3 w-3" /></Button>
                    </div>
                  ))}
                  {selectedBackups.length > 0 && <Button size="sm" variant="destructive" onClick={() => requestConfirm('delete_backups', `${selectedBackups.length} بک‌آپ انتخاب شده حذف شوند؟`, undefined, undefined, selectedBackups)} className="w-full h-7 text-[10px] gap-1 mt-2"><Trash2 className="h-3 w-3" /> حذف انتخاب شده‌ها</Button>}
                </div>
              )}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3"><ShieldAlert className={`h-5 w-5 ${isMaintenance ? "text-red-400" : "text-green-400"}`} /><div><h3 className="text-sm font-bold text-white">حالت تعمیرات</h3><p className={`text-[10px] ${isMaintenance ? "text-red-400" : "text-green-400"}`}>{isMaintenance ? "سایت در حال تعمیرات است" : "سایت فعال است"}</p></div></div>
                <Button onClick={() => toggleMaintenance(!isMaintenance)} disabled={maintenanceLoading} size="sm" className={`gap-1 font-bold ${isMaintenance ? "bg-green-500 text-white hover:bg-green-600" : "bg-red-500 text-white hover:bg-red-600"}`}>{maintenanceLoading ? "..." : (isMaintenance ? "خروج از تعمیرات" : "فعال‌سازی")}</Button>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 shadow-xl">
              <h3 className="text-sm font-bold text-[#d6ad60] mb-3 flex items-center gap-2"><Wrench className="h-4 w-4" /> ابزارهای مدیریت (به‌زودی)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{[ "پاکسازی کش", "بازسازی آمار", "ارسال پیام", "واچ‌لیست", "گزارش مالی", "لاگ ادمین" ].map((t, idx) => (<div key={idx} className="rounded-lg border border-white/5 bg-white/5 p-2 opacity-40 text-center"><p className="text-[10px] text-gray-400">{t}</p></div>))}</div>
            </div>
          </div>
        )}
      </main>

      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white">
          <DialogHeader><DialogTitle className="text-[#d6ad60]">افزودن کاربر جدید</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div><label className="text-xs text-gray-400">شماره موبایل</label><Input value={newUserPhone} onChange={e => setNewUserPhone(e.target.value)} className="bg-black/30 border-white/10 mt-1" dir="ltr" /></div>
            <div><label className="text-xs text-gray-400">نام</label><Input value={newUserName} onChange={e => setNewUserName(e.target.value)} className="bg-black/30 border-white/10 mt-1" /></div>
            <div><label className="text-xs text-gray-400">پلن</label><select value={newUserPlan} onChange={e => setNewUserPlan(e.target.value)} className="w-full h-10 mt-1 rounded-md bg-black/30 border-white/10 text-sm px-2"><option value="free">رایگان</option><option value="1_month">یک ماهه</option><option value="3_months">سه ماهه</option><option value="6_months">شش ماهه</option><option value="12_months">یک ساله</option></select></div>
            <div><label className="text-xs text-gray-400">مدت (روز)</label><Input type="number" value={newUserDays} onChange={e => setNewUserDays(Number(e.target.value))} className="bg-black/30 border-white/10 mt-1" /></div>
            <div className="flex items-center gap-2"><input type="checkbox" id="sendSmsAdd" checked={newUserSendSms} onChange={e => setNewUserSendSms(e.target.checked)} className="accent-[#d6ad60]" /><label htmlFor="sendSmsAdd" className="text-xs text-gray-400">ارسال پیامک اطلاع‌رسانی</label></div>
            <Button onClick={handleAddUser} className="w-full bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90">ثبت کاربر</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-[#0d1b2d] border-white/10 text-white">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-[#d6ad60]"><UserCheck className="h-5 w-5" /> مدیریت کاربر: {selectedUser?.phone}</DialogTitle></DialogHeader>
          {userDetails ? (
            <div className="space-y-6 py-4">
              {/* اطلاعات کاربر */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-black/20 p-4 rounded-xl border border-white/5">
                <div><span className="text-gray-400">نام:</span> {userDetails.user.full_name || "نامشخص"}</div>
                <div><span className="text-gray-400">تاریخ عضویت:</span> {formatFaDate(userDetails.user.created_at)}</div>
                <div><span className="text-gray-400">آخرین ورود:</span> {formatFaDateTime(userDetails.user.last_login)}</div>
                <div><span className="text-gray-400">آخرین IP:</span> <span className="font-mono dir-ltr text-gray-300">{userDetails.user.last_ip}</span></div>
                <div className="sm:col-span-2"><span className="text-gray-400">مرورگر:</span> <span className="text-xs text-gray-300" title={userDetails.user.last_user_agent}>{userDetails.user.last_user_agent}</span></div>
              </div>
              
              {/* 🔴 جمع‌بندی مالی */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-3">
                  <p className="text-[10px] text-green-400 mb-1">جمع پرداختی‌های تایید شده:</p>
                  <p className="text-lg font-bold text-green-400" dir="ltr">
                    {((userDetails as any).total_paid || 0).toLocaleString("fa-IR")}
                    <span className="text-xs text-gray-400 mr-1">تومان</span>
                  </p>
                </div>
                <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-3">
                  <p className="text-[10px] text-purple-400 mb-1">جمع عودت‌های وجه:</p>
                  <p className="text-lg font-bold text-purple-400" dir="ltr">
                    {((userDetails as any).total_refunded || 0).toLocaleString("fa-IR")}
                    <span className="text-xs text-gray-400 mr-1">تومان</span>
                  </p>
                </div>
                <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3">
                  <p className="text-[10px] text-blue-400 mb-1">مانده خالص:</p>
                  <p className="text-lg font-bold text-blue-400" dir="ltr">
                    {((userDetails as any).net_balance || 0).toLocaleString("fa-IR")}
                    <span className="text-xs text-gray-400 mr-1">تومان</span>
                  </p>
                </div>
              </div>

              {/* 🔴 دکمه فعال‌سازی کاربر (اگه غیرفعال باشه) */}
              {!userDetails.user.is_active && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserX className="h-5 w-5 text-yellow-500" />
                    <span className="text-xs text-yellow-500">این کاربر غیرفعال است</span>
                  </div>
                  <Button size="sm" onClick={handleActivateUser} className="bg-green-600 hover:bg-green-700 text-white gap-1">
                    <UserCheck2 className="h-4 w-4" /> فعال‌سازی کاربر
                  </Button>
                </div>
              )}              
              
              <div><h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی پلن اشتراک:</h4><div className="flex flex-wrap gap-2">{[ "1_month", "3_months", "6_months", "12_months" ].map((plan) => (<Button key={plan} size="sm" variant="outline" className="border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => handleChangePlan(plan)}>{getPlanNameFa(plan)}</Button>))}</div><div className="flex items-center gap-2 mt-2"><input type="checkbox" id="sendSmsPlan" checked={sendSmsPlan} onChange={e => setSendSmsPlan(e.target.checked)} className="accent-[#d6ad60]" /><label htmlFor="sendSmsPlan" className="text-[10px] text-gray-400">ارسال پیامک اطلاع‌رسانی</label></div></div>
              <div><h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی تاریخ انقضا:</h4><div className="flex flex-wrap items-center gap-2"><Input type="number" placeholder="مثلاً 30" value={adjustDays || ""} onChange={(e) => setAdjustDays(Number(e.target.value))} className="w-24 h-9 bg-black/30 border-white/10 text-white" /><Button size="sm" variant="outline" onClick={handleAdjustDays} className="gap-1 text-green-500 border-green-500/20 hover:bg-green-500/10">اعمال روز</Button><span className="text-xs text-gray-500">(عدد منفی برای کاهش)</span></div><div className="flex items-center gap-2 mt-2"><input type="checkbox" id="sendSmsDays" checked={sendSmsDays} onChange={e => setSendSmsDays(e.target.checked)} className="accent-[#d6ad60]" /><label htmlFor="sendSmsDays" className="text-[10px] text-gray-400">ارسال پیامک اطلاع‌رسانی</label></div></div>
              {user.phone === "09129630901" && (<div><h4 className="font-bold text-sm mb-2 text-[#d6ad60]">مدیریت سطح دسترسی:</h4>{selectedUser.is_admin ? (selectedUser.phone !== "09129630901" && (<Button size="sm" variant="destructive" onClick={() => handleAction(selectedUser.id, `/admin/users/${selectedUser.id}/remove-admin`, "دسترسی ادمین لغو شود؟")} className="gap-1"><ShieldAlert className="h-4 w-4" /> لغو دسترسی ادمین</Button>)) : (<Button size="sm" variant="outline" onClick={() => handleAction(selectedUser.id, `/admin/users/${selectedUser.id}/make-admin`, "کاربر به مدیر ارتقا یابد؟")} className="gap-1 text-orange-500 border-orange-500/20 hover:bg-orange-500/10"><ShieldAlert className="h-4 w-4" /> ارتقا به مدیر</Button>)}</div>)}
              
              {/* 🔴 بخش ریست رمز توسط ادمین */}
              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">ریست رمز عبور (توسط مدیر):</h4>
                <div className="flex gap-2">
                  <Input type="text" placeholder="رمز جدید (حداقل ۶ حرف)" value={newPasswordForUser} onChange={(e) => setNewPasswordForUser(e.target.value)} className="bg-black/30 border-white/10 text-white h-9 flex-1 text-sm" dir="ltr" />
                  <Button size="sm" variant="outline" onClick={handleResetPassword} className="gap-1 text-blue-400 border-blue-500/20 hover:bg-blue-500/10"><Lock className="h-3.5 w-3.5" /> ثبت</Button>
                </div>
              </div>

              {/* 🔴 بخش ثبت درخواست عودت */}
              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">لغو اشتراک و عودت وجه:</h4>
                <p className="text-[10px] text-gray-400 mb-2 leading-relaxed">
                  با ثبت این درخواست، پلن کاربر به پلن جدید تغییر می‌کند و مبلغ عودت به حساب او بازگردانده می‌شود.
                </p>
                <Button size="sm" variant="outline" onClick={() => setIsRefundModalOpen(true)} className="gap-1 text-red-400 border-red-500/20 hover:bg-red-500/10">
                  <DollarSign className="h-3.5 w-3.5" /> ثبت درخواست عودت
                </Button>
              </div>

              {/* 🔴 بخش آمار دانلود افزونه */}
              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">آمار دانلود افزونه:</h4>
                {extStats ? (
                  <div className="bg-black/30 p-3 rounded-lg border border-white/5 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-400">تعداد کل دانلودها:</span>
                      <span className="text-white font-bold">{extStats.total_downloads} بار</span>
                    </div>
                    
                    {extStats.logs && extStats.logs.length > 0 && (
                      <div className="border-t border-white/10 mt-2 pt-2 max-h-40 overflow-y-auto space-y-1.5 pr-1">
                        {extStats.logs.map((log: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between text-[10px] bg-black/40 p-1.5 rounded">
                            <span className="text-gray-300">{formatFaDateTime(log.downloaded_at)}</span>
                            <span className="font-mono dir-ltr text-gray-400">{log.ip_address}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {extStats.total_downloads > 0 && (
                      <div className="text-[10px] text-gray-500 mt-1">
                        آخرین دانلود: {formatFaDateTime(extStats.logs[0]?.downloaded_at)}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-xs text-gray-500 py-2">در حال بارگذاری...</div>
                )}
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">حذف / غیرفعال‌سازی کاربر:</h4>
                <div className="flex items-center gap-2 mb-2">
                  <input type="checkbox" id="deleteHard" checked={deleteHard} onChange={e => setDeleteHard(e.target.checked)} className="accent-red-500" />
                  <label htmlFor="deleteHard" className="text-[10px] text-red-400">حذف کامل (غیرقابل بازگشت)</label>
                </div>
                <Button size="sm" variant="destructive" onClick={handleDeleteUser} className="gap-1">
                  <Trash2 className="h-4 w-4" /> حذف / غیرفعال‌سازی کاربر
                </Button>
              </div>
              <div><h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه اشتراک‌ها:</h4><div className="space-y-2">{userDetails.subscriptions.length === 0 ? <p className="text-xs text-gray-500">ندارد</p> : userDetails.subscriptions.map((s: any) => (<div key={s.id} className="text-xs flex justify-between items-center bg-white/5 p-2 rounded border border-white/5"><span className="font-bold text-gray-200">{getPlanNameFa(s.plan)}</span><span className="text-gray-400">تا {s.end ? formatFaDate(s.end) : "نامحدود"}</span></div>))}</div></div>
              
              {/* 🔴 تاریخچه پرداخت‌ها */}
              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه پرداخت‌ها:</h4>
                <div className="space-y-2">
                  {userDetails.payments.length === 0 ? (
                    <p className="text-xs text-gray-500">ندارد</p>
                  ) : (
                    userDetails.payments.map((p: any) => {
                      const isRefund = p.payment_method === "refund" || p.plan === "refund";
                      const bgColor = isRefund ? "bg-purple-500/10 border-purple-500/20" : "bg-white/5 border-white/5";
                      const textColor = isRefund ? "text-purple-400" : "text-gray-200";
                      const statusBg = p.status === "approved" ? "bg-green-500/10 text-green-500 border-green-500/20" :
                                       p.status === "pending" ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/20" :
                                       p.status === "refunded" ? "bg-purple-500/10 text-purple-500 border-purple-500/20" :
                                       "bg-red-500/10 text-red-500 border-red-500/20";
                      const statusText = p.status === "approved" ? "تایید شده" :
                                        p.status === "pending" ? "در انتظار" :
                                        p.status === "refunded" ? "عودت شده" : "رد شده";
                      
                      return (
                        <div key={p.id} className={`text-xs flex justify-between items-center p-2 rounded border ${bgColor}`}>
                          <span className={`font-bold ${textColor}`}>{getPlanNameFa(p.plan)}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusBg}`}>{statusText}</span>
                          <span className="text-gray-400">{formatFaDate(p.created_at)}</span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#d6ad60]"></div></div>
          )}
        </DialogContent>
      </Dialog>

      {/* 🔴 مودال یادداشت برای تایید/رد */}
      <Dialog open={isNoteModalOpen} onOpenChange={setIsNoteModalOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">
              {noteAction?.type === "approve" ? "تایید پرداخت" : "رد پرداخت"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-400">
              لطفاً دلیل {noteAction?.type === "approve" ? "تایید" : "رد"} را وارد کنید (اختیاری):
            </p>
            <textarea 
              value={noteText} 
              onChange={e => setNoteText(e.target.value)} 
              placeholder="مثلاً: مبلغ کمتر واریز شده بود..." 
              className="w-full h-24 bg-black/30 border border-white/10 rounded-md p-2 text-sm text-white" 
            />
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsNoteModalOpen(false)} className="flex-1 border-white/10 text-gray-300">لغو</Button>
              <Button onClick={handleApproveWithNote} disabled={noteLoading} className={`flex-1 ${noteAction?.type === "approve" ? "bg-green-600" : "bg-red-600"} text-white`}>
                {noteLoading ? "..." : "تایید نهایی"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 🔴 مدال جزئیات و ویرایش تراکنش */}
      <Dialog open={isTxDetailOpen} onOpenChange={setIsTxDetailOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">جزئیات و ویرایش تراکنش</DialogTitle>
          </DialogHeader>
          {selectedTx && (
            <div className="space-y-4 py-2">
              {/* اطلاعات اولیه */}
              <div className="bg-black/30 p-3 rounded-lg border border-white/5 text-xs space-y-1.5">
                <div className="flex justify-between"><span className="text-gray-400">کاربر:</span><span className="font-mono dir-ltr text-white">{selectedTx.user_phone}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">پلن:</span><span className="text-white">{getPlanNameFa(selectedTx.plan)}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">روش پرداخت:</span><span className="text-white">{paymentMethodLabel(selectedTx.payment_method)}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">تاریخ درخواست:</span><span className="text-white">{formatFaDateTime(selectedTx.created_at)}</span></div>
                {selectedTx.payment_time && <div className="flex justify-between"><span className="text-gray-400">زمان واریز:</span><span className="text-white">{selectedTx.payment_time}</span></div>}
                {selectedTx.receipt_note && <div className="flex justify-between"><span className="text-gray-400">توضیحات کاربر:</span><span className="text-white">{selectedTx.receipt_note}</span></div>}
              </div>
              
              {/* فرم ویرایش */}
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">مبلغ (تومان)</label>
                  <Input type="number" value={txNewAmount} onChange={e => setTxNewAmount(Number(e.target.value))} className="bg-black/30 border-white/10 text-white" dir="ltr" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">وضعیت</label>
                  <select value={txNewStatus} onChange={e => setTxNewStatus(e.target.value)} className="w-full h-10 rounded-md bg-black/30 border-white/10 text-sm px-2">
                    <option value="pending">در حال بررسی</option>
                    <option value="approved">تایید شده</option>
                    <option value="rejected">رد شده</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">یادداشت ادمین</label>
                  <textarea 
                    value={txNewNote} 
                    onChange={e => setTxNewNote(e.target.value)} 
                    placeholder="دلیل تغییر..." 
                    className="w-full h-24 bg-black/30 border border-white/10 rounded-md p-2 text-sm text-white" 
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" id="txSendSms" checked={txSendSms} onChange={e => setTxSendSms(e.target.checked)} className="accent-[#d6ad60]" />
                  <label htmlFor="txSendSms" className="text-xs text-gray-400">ارسال پیامک اطلاع‌رسانی به کاربر</label>
                </div>
              </div>
              
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setIsTxDetailOpen(false)} className="flex-1 border-white/10 text-gray-300">لغو</Button>
                <Button onClick={saveTxDetail} disabled={txDetailLoading} className="flex-1 bg-[#d6ad60] text-[#101827] font-bold">
                  {txDetailLoading ? "..." : "ذخیره تغییرات"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 🔴 مدال ثبت درخواست عودت */}
      <Dialog open={isRefundModalOpen} onOpenChange={setIsRefundModalOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">ثبت درخواست عودت</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">نوع اقدام (فقط جهت اطلاع)</label>
              <select value={refundNewPlan} onChange={e => setRefundNewPlan(e.target.value)} className="w-full h-10 rounded-md bg-black/30 border-white/10 text-sm px-2">
                <option value="no_change">بدون تغییر (فقط عودت وجه)</option>
                <option value="deactivate">غیرفعال‌سازی اشتراک</option>
                <option value="1_month">تغییر به یک ماهه</option>
                <option value="3_months">تغییر به سه ماهه</option>
                <option value="6_months">تغییر به شش ماهه</option>
                <option value="12_months">تغییر به یک ساله</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">مبلغ عودت (تومان)</label>
              <Input type="number" value={refundAmount || ""} onChange={e => setRefundAmount(Number(e.target.value))} className="bg-black/30 border-white/10 text-white" dir="ltr" />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">توضیحات (مثلاً شماره کارت)</label>
              <textarea value={refundNote} onChange={e => setRefundNote(e.target.value)} placeholder="شماره کارت: ..." className="w-full h-24 bg-black/30 border border-white/10 rounded-md p-2 text-sm text-white" />
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={() => setIsRefundModalOpen(false)} className="flex-1 border-white/10 text-gray-300">لغو</Button>
              <Button onClick={handleCreateRefund} disabled={refundLoading} className="flex-1 bg-[#d6ad60] text-[#101827] font-bold">
                {refundLoading ? "..." : "ثبت درخواست"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <DialogContent className="bg-[#0d1b2d] border-white/10 text-white max-w-md">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-[#d6ad60]"><AlertTriangle className="h-5 w-5" /> تایید عملیات</DialogTitle></DialogHeader>
          <p className="text-sm text-gray-300 py-4">{confirmAction?.message}</p>
          <div className="flex gap-2 justify-end"><Button variant="outline" onClick={() => setIsConfirmOpen(false)} className="border-white/10 text-gray-300">لغو</Button><Button onClick={executeAction} className={confirmAction?.type === 'delete_backups' ? "bg-red-500 text-white hover:bg-red-600" : "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"}>تایید</Button></div>
        </DialogContent>
      </Dialog>

      <Footer />
    </div>
  );
}