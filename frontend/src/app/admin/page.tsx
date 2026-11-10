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
  LogOut,
  CheckCircle2,
  XCircle,
  CreditCard,
  Users,
  Clock,
  Globe,
  Monitor,
  UserCheck,
  Download,
  History,
  ShieldAlert,
  ArrowUpDown,
  Home,
  Crown,
  TrendingUp,
  Bell,
  X,
  UserPlus,
  Trash2,
  Wrench,
  AlertTriangle,
  MessageSquare,
  Database,
  Search,
  Pencil,
  DollarSign,
  Wallet,
  Lock,
  RefreshCw,
  UserX,
  UserCheck2,
  Hourglass,
  Target,
  ChevronDown,
  Save,
  RotateCcw,
  CheckCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAdminNotifications } from "@/hooks/useAdminNotifications";
import Link from "next/link";
import { RestoreGuide } from "@/components/admin/RestoreGuide";
// 🔴 فاز ۱۴.۹.۱۲ — راستی‌آزمایی
import { BacktestStats } from "@/components/backtest/BacktestStats";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "1_month": "یک ماهه",
    "3_months": "سه ماهه",
    "6_months": "شش ماهه",
    "12_months": "یک ساله",
    free: "رایگان",
    monthly: "ماهانه",
    "بدون اشتراک": "بدون اشتراک",
    "نامحدود (مدیر)": "نامحدود (مدیر)",
    refund: "عودت وجه",
  };
  return map[plan] || plan || "نامشخص";
};

const formatFaDate = (iso: string | null) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fa-IR");
  } catch {
    return "—";
  }
};

const formatFaDateTime = (iso: string | null) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fa-IR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return "—";
  }
};

const statusDot = (status: string) => {
  switch (status) {
    case "active":
      return "bg-green-500 shadow-[0_0_8px_#22c55e]";
    case "free_active":
      return "bg-yellow-500 shadow-[0_0_8px_#eab308]";
    case "expired":
      return "bg-red-500 shadow-[0_0_8px_#ef4444]";
    case "free":
      return "bg-red-500/60";
    case "admin":
      return "bg-blue-500 shadow-[0_0_8px_#3b82f6]";
    default:
      return "bg-gray-500";
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
    case "approved":
      return {
        text: "تایید شده",
        color: "text-green-400 bg-green-500/10 border-green-500/30",
      };
    case "pending":
      return {
        text: "در حال بررسی",
        color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
      };
    case "rejected":
      return {
        text: "رد شده",
        color: "text-red-400 bg-red-500/10 border-red-500/30",
      };
    case "refunded":
      return {
        text: "عودت شده",
        color: "text-purple-400 bg-purple-500/10 border-purple-500/30",
      };
    default:
      return { text: s, color: "text-gray-400 bg-white/5 border-white/10" };
  }
};

type TabKey =
  | "users"
  | "payments"
  | "transactions"
  | "tools"
  | "zibal"
  | "refunds"
  | "verification";

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
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: "asc" | "desc";
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [txSearchQuery, setTxSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<
    "all" | "active" | "expired" | "inactive"
  >("all");
  const [stats, setStats] = useState<any>(null);

  // 🔴 فاز ۱۴.۹.۱۲ — کنترل آمار نمایشی
  const [siteStats, setSiteStats] = useState<any>(null);
  const [inputWinRate, setInputWinRate] = useState<string>("");
  const [inputDirAcc, setInputDirAcc] = useState<string>("");
  const [inputTotalSignals, setInputTotalSignals] = useState<string>("");
  const [overrideSaving, setOverrideSaving] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userDetails, setUserDetails] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [adjustDays, setAdjustDays] = useState<number>(0);
  const [sendSmsPlan, setSendSmsPlan] = useState(true);
  const [sendSmsDays, setSendSmsDays] = useState(true);
  const [inputWinRateDict, setInputWinRateDict] = useState<Record<string, string>>({});
  const [inputDirAccDict, setInputDirAccDict] = useState<Record<string, string>>({});
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
  const [confirmAction, setConfirmAction] = useState<{
    type: "delete" | "admin" | "action" | "delete_backups";
    id?: number;
    endpoint?: string;
    message: string;
    backupNames?: string[];
  } | null>(null);
  const [deleteHard, setDeleteHard] = useState(false);

  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [noteAction, setNoteAction] = useState<{
    type: "approve" | "reject";
    id: number;
  } | null>(null);
  const [noteText, setNoteText] = useState("");
  const [noteLoading, setNoteLoading] = useState(false);

  const [isTxDetailOpen, setIsTxDetailOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<any>(null);
  const [txNewAmount, setTxNewAmount] = useState<number>(0);
  const [txNewStatus, setTxNewStatus] = useState<string>("pending");
  const [txNewNote, setTxNewNote] = useState<string>("");
  const [txSendSms, setTxSendSms] = useState(true);
  const [txDetailLoading, setTxDetailLoading] = useState(false);

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
      const res = await fetch(`${apiUrl}/admin/tickets/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setTicketStats(await res.json());
    } catch {}
  };

  const fetchMaintenanceStatus = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/maintenance`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setIsMaintenance(data.is_maintenance);
      }
    } catch {}
  };

  const fetchBackups = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/backups`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setBackups(data.items || []);
      }
    } catch {}
  };


  
    const fetchStats = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/dashboard-stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setStats(await res.json());
    } catch {}
  };

  // 🔴 فاز ۱۴.۹.۱۲ — fetch آمار نمایشی
  const fetchSiteStats = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/site-stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSiteStats(data);
                const newWinRateDict: Record<string, string> = {};
        const newDirAccDict: Record<string, string> = {};
        ["scalp", "swing", "position"].forEach((strat) => {
          if (data.by_strategy?.[strat]?.has_override?.win_rate) {
            newWinRateDict[strat] = String(data.by_strategy[strat].win_rate);
          }
          if (data.by_strategy?.[strat]?.has_override?.direction_accuracy) {
            newDirAccDict[strat] = String(data.by_strategy[strat].direction_accuracy);
          }
        });
        setInputWinRateDict(newWinRateDict);
        setInputDirAccDict(newDirAccDict);
        setInputWinRate(
          data.has_override?.win_rate ? String(data.win_rate) : ""
        );
        setInputDirAcc(
          data.has_override?.direction_accuracy
            ? String(data.direction_accuracy)
            : ""
        );
        setInputTotalSignals(data.has_override?.total_signals ? String(data.total_signals) : "");

      }
    } catch {}
  };

const saveOverride = async (key: string, value: number) => {
  if (value < 0 || value > 100) {
      alert("مقدار باید بین ۰ تا ۱۰۰ باشد");
      return;
    }
    setOverrideSaving(true);
    try {
      const res = await fetch(`${apiUrl}/admin/site-stats/override`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ key, value }),
      });
      if (!res.ok) throw new Error("خطا در ذخیره");
      await fetchSiteStats();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setOverrideSaving(false);
    }
  };

const deleteOverride = async (key: string) => {
  if (!confirm("برگشت به مقدار واقعی؟")) return;
    setOverrideSaving(true);
    try {
      const res = await fetch(`${apiUrl}/admin/site-stats/override/${key}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("خطا در حذف");
      await fetchSiteStats();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setOverrideSaving(false);
    }
  };


  useEffect(() => {
    fetch(`${apiUrl}/admin/payments`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setPendingCount((data.items || []).length))
      .catch(() => {});
    fetchTicketStats();
    fetchBackups();
    fetchMaintenanceStatus();
    fetchStats();
    fetchSiteStats();
  }, [apiUrl, token]);
      
  useEffect(() => {
    const u = getUser();
    if (!u || !u.is_admin) {
      router.replace("/login");
      return;
    }
    setUserData(u);
    fetchData();
    if (activeTab === "verification") fetchSiteStats();
  }, [router, activeTab]);
  
  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "payments") {
        const res = await fetch(`${apiUrl}/admin/payments`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (res.ok) {
          setPayments(data.items || []);
          setPendingCount((data.items || []).length);
        }
      } else if (activeTab === "transactions") {
        const res = await fetch(`${apiUrl}/admin/all-transactions`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (res.ok) setTransactions(data.items || []);
      } else if (activeTab === "users") {
        const res = await fetch(`${apiUrl}/admin/users`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (res.ok) setUsersList(data.items || []);
      } else if (activeTab === "refunds") {
        const res = await fetch(`${apiUrl}/admin/refunds`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (res.ok) setRefunds(data.items || []);
      }
      fetchStats();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const { connected } = useAdminNotifications((n) => {
    setNotifications((prev) => [n, ...prev].slice(0, 5));
    fetchData();
    if (n.type === "new_ticket" || n.type === "ticket_reply") fetchTicketStats();
  });

  const dismissNotification = (idx: number) =>
    setNotifications((prev) => prev.filter((_, i) => i !== idx));

  useEffect(() => {
    if (notifications.length === 0) return;
    const timers = notifications.map((_, idx) =>
      setTimeout(() => dismissNotification(idx), 15000)
    );
    return () => timers.forEach((t) => clearTimeout(t));
  }, [notifications.length]);

  const filteredUsers = usersList.filter((u) => {
    const matchSearch =
      u.phone.includes(searchQuery) ||
      (u.full_name && u.full_name.includes(searchQuery));
    if (!matchSearch) return false;

    if (statusFilter === "active") return u.is_active_sub || u.is_admin;
    if (statusFilter === "expired") return !u.is_active_sub && !u.is_admin;
    if (statusFilter === "inactive") return u.is_active === false;
    return true;
  });

  const sortedUsers = [...filteredUsers].sort((a, b) => {
    if (!sortConfig) return 0;
    const { key, direction } = sortConfig;
    const aVal = a[key] ?? "";
    const bVal = b[key] ?? "";
    if (aVal < bVal) return direction === "asc" ? -1 : 1;
    if (aVal > bVal) return direction === "asc" ? 1 : -1;
    return 0;
  });

  const filteredTransactions = useMemo(() => {
    if (!txSearchQuery.trim()) return transactions;
    const q = txSearchQuery.toLowerCase();
    return transactions.filter(
      (t) =>
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
    let direction: "asc" | "desc" = "asc";
    if (
      sortConfig &&
      sortConfig.key === key &&
      sortConfig.direction === "asc"
    )
      direction = "desc";
    setSortConfig({ key, direction });
  };

  const openUserDetails = async (u: any) => {
    setSelectedUser(u);
    setIsModalOpen(true);
    setUserDetails(null);
    setAdjustDays(0);
    setNewPasswordForUser("");
    try {
      const res = await fetch(`${apiUrl}/admin/users/${u.id}/details`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) setUserDetails(data);

      fetch(`${apiUrl}/admin/users/${u.id}/extension-stats`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((stats) => setExtStats(stats))
        .catch(console.error);
    } catch (err) {
      console.error(err);
    }
  };

  const requestConfirm = (
    type: "delete" | "admin" | "action" | "delete_backups",
    message: string,
    id?: number,
    endpoint?: string,
    backupNames?: string[]
  ) => {
    setConfirmAction({ type, id, endpoint, message, backupNames });
    setIsConfirmOpen(true);
  };

  const executeAction = async () => {
    if (!confirmAction) return;
    setIsConfirmOpen(false);
    try {
      if (confirmAction.type === "delete" && confirmAction.id) {
        const res = await fetch(
          `${apiUrl}/admin/users/${confirmAction.id}?hard_delete=${deleteHard}`,
          {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
        setIsModalOpen(false);
        fetchData();
      } else if (
        confirmAction.type === "delete_backups" &&
        confirmAction.backupNames
      ) {
        const res = await fetch(`${apiUrl}/admin/backups/delete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ names: confirmAction.backupNames }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
        setSelectedBackups([]);
        fetchBackups();
      } else if (confirmAction.endpoint) {
        const res = await fetch(`${apiUrl}${confirmAction.endpoint}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);

        if (selectedUser) {
          try {
            const detailsRes = await fetch(
              `${apiUrl}/admin/users/${selectedUser.id}/details`,
              { headers: { Authorization: `Bearer ${token}` } }
            );
            const detailsData = await detailsRes.json();
            if (detailsRes.ok) setUserDetails(detailsData);
          } catch (e) {
            console.error(e);
          }
        }

        fetchData();
      }
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleAction = async (
    id: number,
    endpoint: string,
    confirmMsg: string
  ) => {
    requestConfirm("action", confirmMsg, id, endpoint);
  };

  const handleChangePlan = (plan: string) => {
    requestConfirm(
      "action",
      `پلن کاربر به ${getPlanNameFa(plan)} تغییر کند؟`,
      selectedUser.id,
      `/admin/users/${selectedUser.id}/change-plan?plan=${plan}&send_sms=${sendSmsPlan}`
    );
  };

  const handleAdjustDays = () => {
    requestConfirm(
      "action",
      `تعداد ${adjustDays} روز به اشتراک کاربر اضافه/کم شود؟`,
      selectedUser.id,
      `/admin/users/${selectedUser.id}/adjust-days?days=${adjustDays}&send_sms=${sendSmsDays}`
    );
  };

  const handleResetPassword = () => {
    if (!newPasswordForUser || newPasswordForUser.length < 6)
      return alert("رمز جدید باید حداقل ۶ حرف باشد");
    requestConfirm(
      "action",
      "رمز عبور کاربر ریست شود؟",
      selectedUser.id,
      `/admin/users/${selectedUser.id}/reset-password?new_password=${newPasswordForUser}`
    );
  };

  const handleActivateUser = () => {
    requestConfirm(
      "action",
      "کاربر فعال شود؟",
      selectedUser.id,
      `/admin/users/${selectedUser.id}/activate`
    );
  };

  const handleDeleteUser = async () => {
    try {
      const res = await fetch(
        `${apiUrl}/admin/users/${selectedUser.id}/ticket-count`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();

      if (data.count > 0) {
        if (
          !confirm(
            `⚠️ این کاربر ${data.count} تیکت دارد. با حذف کاربر، تمام تیکت‌ها و پیام‌های آن‌ها هم پاک می‌شوند. مطمئنی؟`
          )
        )
          return;
      }

      requestConfirm(
        "delete",
        deleteHard
          ? "کاربر و تمام داده‌های مرتبط برای همیشه حذف شوند؟"
          : "کاربر غیرفعال شود؟ (قابل بازگشت)",
        selectedUser.id
      );
    } catch {
      requestConfirm(
        "delete",
        deleteHard
          ? "کاربر و تمام داده‌های مرتبط برای همیشه حذف شوند؟"
          : "کاربر غیرفعال شود؟ (قابل بازگشت)",
        selectedUser.id
      );
    }
  };

  const handleAddUser = async () => {
    if (!newUserPhone || newUserPhone.length < 11)
      return alert("شماره موبایل نامعتبر است");
    try {
      const res = await fetch(
        `${apiUrl}/admin/users/add?phone=${newUserPhone}&full_name=${newUserName}&plan=${newUserPlan}&days=${newUserDays}&send_sms=${newUserSendSms}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      alert(data.message);
      setIsAddModalOpen(false);
      setNewUserPhone("");
      setNewUserName("");
      fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const toggleMaintenance = async (enable: boolean) => {
    if (enable && !confirm("آیا مطمئنید؟ سایت برای همه کاربران غیرفعال می‌شود."))
      return;
    setMaintenanceLoading(true);
    try {
      const res = await fetch(
        `${apiUrl}/admin/maintenance/${enable ? "enable" : "disable"}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
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
      const res = await fetch(`${apiUrl}/admin/backup`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "خطا در بک‌آپ");
      }

      alert(
        `✅ بک‌آپ "${data.name}" با موفقیت ساخته شد.\n\nحجم: ${(data.size / 1024).toFixed(1)} KB`
      );
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
      const res = await fetch(`${apiUrl}/admin/users/excel`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("خطا");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `trademun-users-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.xlsx`;
      a.click();
    } catch (err) {
      alert("خطا");
    }
  };

  const handleTxExcel = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/transactions/excel`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("خطا");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `trademun-transactions-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.xlsx`;
      a.click();
    } catch (err) {
      alert("خطا در خروجی اکسل");
    }
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
      if (txNewAmount !== selectedTx.amount) {
        await fetch(
          `${apiUrl}/admin/transactions/${selectedTx.id}/amount?amount=${txNewAmount}`,
          {
            method: "PATCH",
            headers: { Authorization: `Bearer ${token}` },
          }
        );
      }

      if (txNewStatus !== selectedTx.status) {
        await fetch(
          `${apiUrl}/admin/transactions/${selectedTx.id}/status?new_status=${txNewStatus}&send_sms=${txSendSms}`,
          {
            method: "PATCH",
            headers: { Authorization: `Bearer ${token}` },
          }
        );
      }

      if (txNewNote !== selectedTx.admin_note) {
        await fetch(
          `${apiUrl}/admin/transactions/${selectedTx.id}/note`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ admin_note: txNewNote }),
          }
        );
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
      const res = await fetch(
        `${apiUrl}/admin/payments/${noteAction.id}/${noteAction.type}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ admin_note: noteText }),
        }
      );
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
      const res = await fetch(
        `${apiUrl}/admin/users/${selectedUser.id}/refund`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            new_plan: refundNewPlan,
            refund_amount: refundAmount,
            admin_note: refundNote || undefined,
          }),
        }
      );
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
    setSelectedBackups((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const toggleAllBackups = () => {
    if (selectedBackups.length === backups.length) {
      setSelectedBackups([]);
    } else {
      setSelectedBackups(backups.map((b) => b.name));
    }
  };

  if (!user)
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white">
        در حال بارگذاری...
      </div>
    );

  const activeUsersCount = usersList.filter(
    (u) => u.is_active_sub || u.is_admin
  ).length;

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <div className="pointer-events-none fixed left-4 right-4 top-20 z-[100] flex flex-col gap-2 sm:left-auto sm:right-4 sm:w-96">
        <AnimatePresence>
          {notifications.map((n, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 50 }}
              className="pointer-events-auto flex items-start gap-3 rounded-xl border border-[#d6ad60]/40 bg-[#0d1b2d] p-4 shadow-2xl backdrop-blur-xl"
            >
              <div
                className={`rounded-lg p-2 ${
                  n.type === "new_user" ? "bg-blue-500/20" : "bg-[#d6ad60]/20"
                }`}
              >
                <Bell
                  className={`h-5 w-5 ${
                    n.type === "new_user" ? "text-blue-400" : "text-[#d6ad60]"
                  }`}
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-white">
                  {n.message || "نوتیف جدید"}
                </p>
                {n.user_phone && (
                  <p className="dir-ltr mt-1 font-mono text-xs text-gray-400">
                    {n.user_phone}
                  </p>
                )}
              </div>
              <button
                onClick={() => dismissNotification(idx)}
                className="text-gray-400 transition-colors hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <Header />
      <main className="container mx-auto max-w-6xl flex-1 space-y-6 p-4 py-8">
        {/* ═══ هدر ═══ */}
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/10 p-2 shadow-[0_0_15px_#d6ad6040]">
              <Crown className="h-6 w-6 text-[#d6ad60]" />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold text-white">
                اتاق فرمان
              </h1>
              <p className="flex items-center gap-2 text-sm text-gray-400">
                خوش آمدید، {user.full_name || "مدیر"}
                <span className="ml-2 flex items-center gap-1 text-[10px]">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      connected ? "animate-pulse bg-green-500" : "bg-red-500"
                    }`}
                  />
                  {connected ? "متصل" : "قطع"}
                </span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/">
              <Button
                variant="outline"
                size="sm"
                className="gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white"
              >
                <Home className="h-4 w-4" />
                صفحه اصلی
              </Button>
            </Link>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                removeToken();
                router.replace("/login");
              }}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              خروج
            </Button>
          </div>
        </div>

        {/* ═══ ردیف ۱: ۴ کارت اصلی ═══ */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 sm:gap-4">
          <button
            onClick={() => setActiveTab("users")}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl transition-all hover:border-[#d6ad60]/40 hover:from-[#14263e] hover:to-[#0d1b2d] sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-[#d6ad60]/10 p-2 text-[#d6ad60] sm:p-3">
              <Users className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">کل کاربران</p>
              <p className="text-lg font-bold text-white sm:text-2xl">
                {usersList.length}
              </p>
            </div>
          </button>

          <button
            onClick={() => setActiveTab("users")}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl transition-all hover:border-[#d6ad60]/40 hover:from-[#14263e] hover:to-[#0d1b2d] sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-green-500/10 p-2 text-green-400 sm:p-3">
              <TrendingUp className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">
                کاربران فعال
              </p>
              <p className="text-lg font-bold text-white sm:text-2xl">
                {activeUsersCount}
              </p>
            </div>
          </button>

          <button
            onClick={() => setActiveTab("payments")}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl transition-all hover:border-[#d6ad60]/40 hover:from-[#14263e] hover:to-[#0d1b2d] sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-yellow-500/10 p-2 text-yellow-400 sm:p-3">
              <CreditCard className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">
                درخواست‌های در حال بررسی
              </p>
              <p className="text-lg font-bold text-white sm:text-2xl">
                {pendingCount}
              </p>
            </div>
          </button>

          <Link href="/admin/tickets">
            <div className="group relative flex w-full cursor-pointer items-center gap-2 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl transition-all hover:border-[#d6ad60]/40 hover:from-[#1a2c45] hover:to-[#0d1b2d] sm:gap-4 sm:p-5">
              {ticketStats?.unread_count > 0 && (
                <div className="absolute right-0 top-0 flex h-12 w-12 items-start justify-end rounded-bl-full bg-[#d6ad60]/10 p-1.5 sm:h-16 sm:w-16 sm:p-2">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#d6ad60] sm:h-2 sm:w-2"></span>
                </div>
              )}
              <div className="rounded-xl bg-blue-500/10 p-2 text-blue-400 transition-transform group-hover:scale-110 sm:p-3">
                <MessageSquare className="h-4 w-4 sm:h-6 sm:w-6" />
              </div>
              <div className="flex-1">
                <p className="text-[10px] text-gray-400 sm:text-xs">تیکت‌ها</p>
                <div className="mt-0.5 flex items-center gap-1.5 sm:gap-2">
                  <p className="text-lg font-bold text-white sm:text-2xl">
                    {ticketStats?.open_count || 0}{" "}
                    <span className="text-[10px] font-normal text-gray-500 sm:text-sm">
                      باز
                    </span>
                  </p>
                  {ticketStats?.unread_count > 0 && (
                    <span className="rounded-full bg-[#d6ad60] px-1.5 py-0.5 text-[8px] font-bold text-[#101827] sm:text-[10px]">
                      {ticketStats.unread_count} جدید
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* ═══ ردیف ۲: ۴ کارت مالی ═══ */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 sm:gap-4">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-green-500/10 p-2 text-green-400 sm:p-3">
              <TrendingUp className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">درآمد کل</p>
              <p
                className="text-sm font-bold text-white sm:text-xl"
                dir="ltr"
              >
                {(stats?.total_revenue || 0).toLocaleString("fa-IR")}
                <span className="mr-1 text-[8px] text-gray-500 sm:text-[10px]">
                  تومان
                </span>
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-purple-500/10 p-2 text-purple-400 sm:p-3">
              <RefreshCw className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">جمع عودت‌ها</p>
              <p
                className="text-sm font-bold text-white sm:text-xl"
                dir="ltr"
              >
                {(stats?.total_refunded || 0).toLocaleString("fa-IR")}
                <span className="mr-1 text-[8px] text-gray-500 sm:text-[10px]">
                  تومان
                </span>
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-blue-500/10 p-2 text-blue-400 sm:p-3">
              <DollarSign className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">
                درآمد خالص
              </p>
              <p
                className="text-sm font-bold text-white sm:text-xl"
                dir="ltr"
              >
                {(stats?.net_revenue || 0).toLocaleString("fa-IR")}
                <span className="mr-1 text-[8px] text-gray-500 sm:text-[10px]">
                  تومان
                </span>
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-3 text-right shadow-xl sm:gap-4 sm:p-5"
          >
            <div className="rounded-xl bg-yellow-500/10 p-2 text-yellow-400 sm:p-3">
              <Hourglass className="h-4 w-4 sm:h-6 sm:w-6" />
            </div>
            <div>
              <p className="text-[10px] text-gray-400 sm:text-xs">
                درخواست‌های عودت
              </p>
              <p className="text-lg font-bold text-white sm:text-xl">
                {stats?.pending_refunds || 0}
                <span className="mr-1 text-[8px] text-gray-500 sm:text-[10px]">
                  مورد
                </span>
              </p>
            </div>
          </motion.div>
        </div>

        {/* ═══ تب‌ها ═══ */}
        <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-2">
          <div className="flex w-full gap-1 overflow-x-auto md:w-auto">
            <Button
              variant={activeTab === "users" ? "default" : "ghost"}
              onClick={() => setActiveTab("users")}
              className={`shrink-0 gap-2 ${
                activeTab === "users"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">کاربران</span>
            </Button>
            <Button
              variant={activeTab === "payments" ? "default" : "ghost"}
              onClick={() => setActiveTab("payments")}
              className={`shrink-0 gap-2 ${
                activeTab === "payments"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <CreditCard className="h-4 w-4" />
              <span className="hidden sm:inline">در حال بررسی</span>
            </Button>
            <Button
              variant={activeTab === "transactions" ? "default" : "ghost"}
              onClick={() => setActiveTab("transactions")}
              className={`shrink-0 gap-2 ${
                activeTab === "transactions"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <History className="h-4 w-4" />
              <span className="hidden sm:inline">تراکنش‌ها</span>
            </Button>
            <Button
              variant={activeTab === "refunds" ? "default" : "ghost"}
              onClick={() => setActiveTab("refunds")}
              className={`shrink-0 gap-2 ${
                activeTab === "refunds"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">عودت‌ها</span>
            </Button>
            <Button
              variant="ghost"
              onClick={() => setActiveTab("zibal")}
              className={`shrink-0 gap-2 ${
                activeTab === "zibal"
                  ? "bg-[#d6ad60] text-[#101827]"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Wallet className="h-4 w-4" />
              <span className="hidden sm:inline">زیبال</span>
              <span className="rounded bg-yellow-500/20 px-1 text-[8px] text-yellow-400">
                به زودی
              </span>
            </Button>

            <Link href="/admin/tickets">
              <Button
                variant="ghost"
                className="shrink-0 gap-2 text-gray-400 hover:bg-white/5 hover:text-white"
              >
                <MessageSquare className="h-4 w-4" />
                <span className="hidden sm:inline">تیکت‌ها</span>
              </Button>
            </Link>

            <Button
              variant={activeTab === "tools" ? "default" : "ghost"}
              onClick={() => setActiveTab("tools")}
              className={`shrink-0 gap-2 ${
                activeTab === "tools"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Wrench className="h-4 w-4" />
              <span className="hidden sm:inline">ابزارها</span>
            </Button>
            {/* 🔴 فاز ۱۴.۹.۱۲ — راستی‌آزمایی */}
            <Button
              variant={activeTab === "verification" ? "default" : "ghost"}
              onClick={() => setActiveTab("verification")}
              className={`shrink-0 gap-2 ${
                activeTab === "verification"
                  ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Target className="h-4 w-4" />
              <span className="hidden sm:inline">راستی‌آزمایی</span>
            </Button>
          </div>
        </div>

        {/* ═══ تب users ═══ */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="flex flex-col justify-between gap-2 sm:flex-row">
              <div className="flex flex-1 flex-col gap-2 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                  <Input
                    placeholder="جستجوی شماره یا نام..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="h-11 rounded-xl border-white/10 bg-[#0d1b2d] pl-4 pr-10 text-white"
                  />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as any)}
                  className="h-11 rounded-xl border border-white/10 bg-[#0d1b2d] px-4 text-sm text-white"
                >
                  <option value="all">همه ({usersList.length})</option>
                  <option value="active">فعال ({activeUsersCount})</option>
                  <option value="expired">
                    منقضی ({usersList.length - activeUsersCount})
                  </option>
                  <option value="inactive">
                    غیرفعال (
                    {usersList.filter((u) => u.is_active === false).length})
                  </option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsAddModalOpen(true)}
                  className="h-11 gap-2 border-green-500/30 px-4 text-green-400 hover:bg-green-500/10"
                >
                  <UserPlus className="h-4 w-4" />
                  افزودن
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExcel}
                  className="h-11 gap-2 border-green-500/30 px-4 text-green-400 hover:bg-green-500/10"
                >
                  <Download className="h-4 w-4" />
                  اکسل
                </Button>
              </div>
            </div>
            {loading ? (
              <p className="py-4 text-center text-gray-400">در حال دریافت...</p>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/5 shadow-xl backdrop-blur-xl">
                <table className="w-full text-right text-sm">
                  <thead className="bg-white/5 text-gray-400">
                    <tr>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("phone")}
                      >
                        شماره{" "}
                        {sortConfig?.key === "phone" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("full_name")}
                      >
                        نام{" "}
                        {sortConfig?.key === "full_name" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th className="px-3 py-3 font-medium">نقش</th>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("plan")}
                      >
                        پلن{" "}
                        {sortConfig?.key === "plan" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("end_date")}
                      >
                        اعتبار{" "}
                        {sortConfig?.key === "end_date" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("last_login")}
                      >
                        آخرین ورود{" "}
                        {sortConfig?.key === "last_login" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th
                        className="cursor-pointer px-3 py-3 font-medium hover:text-[#d6ad60]"
                        onClick={() => requestSort("created_at")}
                      >
                        عضویت{" "}
                        {sortConfig?.key === "created_at" && (
                          <ArrowUpDown className="inline h-3 w-3" />
                        )}
                      </th>
                      <th className="px-3 py-3 font-medium">عملیات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {sortedUsers.length === 0 ? (
                      <tr>
                        <td
                          colSpan={8}
                          className="py-8 text-center text-gray-400"
                        >
                          کاربری یافت نشد.
                        </td>
                      </tr>
                    ) : (
                      sortedUsers.map((u) => (
                        <tr
                          key={u.id}
                          className="transition-colors hover:bg-white/5"
                        >
                          <td className="dir-ltr px-3 py-3 font-mono text-xs font-bold text-white">
                            {u.phone}
                          </td>
                          <td className="px-3 py-3 text-xs text-gray-300">
                            {u.full_name}
                          </td>
                          <td className="px-3 py-3">
                            {u.is_admin ? (
                              <span className="flex w-fit items-center gap-1 rounded bg-green-500/10 px-2 py-1 text-[10px] font-bold text-green-400">
                                <ShieldAlert className="h-3 w-3" /> مدیر
                              </span>
                            ) : u.is_active === false ? (
                              <span className="flex w-fit items-center gap-1 rounded bg-gray-500/10 px-2 py-1 text-[10px] font-bold text-gray-500">
                                <span className="h-2 w-2 rounded-full bg-gray-500" />{" "}
                                غیرفعال
                              </span>
                            ) : (
                              <span className="text-[10px] text-gray-400">
                                کاربر
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            <span className="rounded bg-[#d6ad60]/10 px-2 py-1 text-[10px] font-bold text-[#d6ad60]">
                              {getPlanNameFa(u.plan)}
                            </span>
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-2">
                              <span
                                className={`h-2 w-2 rounded-full ${statusDot(u.sub_status)}`}
                              />
                              <span className="text-[10px] text-gray-400">
                                {u.is_admin ? "نامحدود" : formatFaDate(u.end_date)}
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-3 text-[10px] text-gray-400">
                            {formatFaDateTime(u.last_login)}
                          </td>
                          <td className="px-3 py-3 text-[10px] text-gray-400">
                            {formatFaDate(u.created_at)}
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-2">
                              {u.extension_downloaded && (
                                <span
                                  title="افزونه را دانلود کرده"
                                  className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500/20 text-green-400"
                                >
                                  <CheckCircle2 className="h-3 w-3" />
                                </span>
                              )}
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 border-white/10 text-[10px] text-gray-300 hover:bg-white/10 hover:text-white"
                                onClick={() => openUserDetails(u)}
                              >
                                <History className="h-3 w-3" /> جزئیات
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ═══ تب payments ═══ */}
        {activeTab === "payments" && (
          <div className="space-y-4">
            {loading ? (
              <p className="py-4 text-center text-gray-400">در حال دریافت...</p>
            ) : payments.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 py-10 text-center text-gray-400 backdrop-blur-xl">
                هیچ درخواستی نیست.
              </div>
            ) : (
              payments.map((p) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 shadow-lg backdrop-blur-xl transition-colors hover:border-[#d6ad60]/30 md:flex-row md:items-center"
                >
                  <div className="w-full space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="dir-ltr rounded bg-white/10 px-2 py-1 font-mono text-base font-bold text-white">
                        {p.user_phone}
                      </span>
                      <span className="rounded-full bg-[#d6ad60]/10 px-3 py-1 text-xs font-bold text-[#d6ad60]">
                        {getPlanNameFa(p.plan)}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />{" "}
                        {new Date(p.created_at).toLocaleString("fa-IR")}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 gap-2 rounded-lg border border-white/5 bg-black/20 p-3 text-xs text-gray-400 sm:grid-cols-2">
                      <div className="flex items-center gap-2">
                        <UserCheck className="h-4 w-4 text-blue-400" />
                        <span>نام: {p.full_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-yellow-400" />
                        <span>زمان واریز: {p.payment_time}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4 text-orange-400" />
                        <span className="dir-ltr font-mono">{p.ip_address}</span>
                      </div>
                      <div className="flex items-center gap-2 truncate">
                        <Monitor className="h-4 w-4 text-purple-400" />
                        <span className="truncate" title={p.user_agent}>
                          {p.user_agent}
                        </span>
                      </div>
                    </div>
                    {p.receipt_note && (
                      <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-2 text-xs text-yellow-400">
                        <strong>توضیحات کاربر:</strong> {p.receipt_note}
                      </div>
                    )}
                  </div>
                  <div className="flex w-full shrink-0 gap-2 border-t border-white/10 pt-2 md:w-auto md:border-r md:border-t-0 md:pl-4 md:pt-0">
                    <Button
                      size="sm"
                      className="flex-1 gap-1 bg-green-600 text-white hover:bg-green-700 md:flex-none"
                      onClick={() => {
                        setNoteAction({ type: "approve", id: p.id });
                        setIsNoteModalOpen(true);
                      }}
                    >
                      <CheckCircle2 className="h-4 w-4" /> تایید
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      className="flex-1 gap-1 md:flex-none"
                      onClick={() => {
                        setNoteAction({ type: "reject", id: p.id });
                        setIsNoteModalOpen(true);
                      }}
                    >
                      <XCircle className="h-4 w-4" /> رد
                    </Button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* ═══ تب transactions ═══ */}
        {activeTab === "transactions" && (
          <div className="space-y-4">
            <div className="flex flex-col justify-between gap-2 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                <Input
                  placeholder="جستجو در شماره، پلن، وضعیت، روش پرداخت..."
                  value={txSearchQuery}
                  onChange={(e) => setTxSearchQuery(e.target.value)}
                  className="h-11 rounded-xl border-white/10 bg-[#0d1b2d] pl-4 pr-10 text-white"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTxExcel}
                  className="h-11 gap-2 border-green-500/30 px-4 text-green-400 hover:bg-green-500/10"
                >
                  <Download className="h-4 w-4" />
                  اکسل
                </Button>
              </div>
            </div>

            {loading ? (
              <p className="py-4 text-center text-gray-400">در حال دریافت...</p>
            ) : filteredTransactions.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 py-10 text-center text-gray-400 backdrop-blur-xl">
                هیچ تراکنشی نیست.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/5 shadow-xl backdrop-blur-xl">
                <table className="w-full text-right text-sm">
                  <thead className="bg-white/5 text-gray-400">
                    <tr>
                      <th className="px-3 py-3 font-medium">شناسه</th>
                      <th className="px-3 py-3 font-medium">کاربر</th>
                      <th className="px-3 py-3 font-medium">پلن</th>
                      <th className="px-3 py-3 font-medium">روش پرداخت</th>
                      <th className="px-3 py-3 font-medium">مبلغ</th>
                      <th className="px-3 py-3 font-medium">وضعیت</th>
                      <th className="px-3 py-3 font-medium">تاریخ درخواست</th>
                      <th className="px-3 py-3 font-medium">تاریخ تایید</th>
                      <th className="px-3 py-3 font-medium">یادداشت</th>
                      <th className="px-3 py-3 font-medium">عملیات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredTransactions.map((t) => {
                      const st = paymentStatusBadge(t.status);
                      const MethodIcon =
                        t.payment_method === "zibal"
                          ? Wallet
                          : t.payment_method === "refund"
                            ? RefreshCw
                            : CreditCard;
                      const isRefund =
                        t.payment_method === "refund" || t.plan === "refund";
                      return (
                        <tr
                          key={t.id}
                          className="transition-colors hover:bg-white/5"
                        >
                          <td className="px-3 py-3 font-mono text-[10px] text-gray-500">
                            {t.id}
                          </td>
                          <td className="dir-ltr px-3 py-3 font-mono text-xs text-white">
                            {t.user_phone}
                          </td>
                          <td
                            className={`px-3 py-3 text-xs ${isRefund ? "font-bold text-purple-400" : "text-gray-300"}`}
                          >
                            {getPlanNameFa(t.plan)}
                          </td>
                          <td className="px-3 py-3">
                            <span className="inline-flex items-center gap-1 text-[10px] text-gray-300">
                              <MethodIcon className="h-3 w-3" />{" "}
                              {paymentMethodLabel(t.payment_method)}
                            </span>
                          </td>
                          <td
                            className="px-3 py-3 text-xs font-bold text-white"
                            dir="ltr"
                          >
                            {(t.amount || 0).toLocaleString("fa-IR")}
                            <span className="mr-1 text-[9px] text-gray-500">
                              تومان
                            </span>
                          </td>
                          <td className="px-3 py-3">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${st.color}`}
                            >
                              {st.text}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-[10px] text-gray-400">
                            {formatFaDateTime(t.created_at)}
                          </td>
                          <td className="px-3 py-3 text-[10px] text-gray-400">
                            {t.reviewed_at ? formatFaDateTime(t.reviewed_at) : "—"}
                          </td>
                          <td
                            className="max-w-[150px] truncate px-3 py-3 text-[10px] text-gray-400"
                            title={t.admin_note}
                          >
                            {t.admin_note || "—"}
                          </td>
                          <td className="px-3 py-3">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openTxDetail(t)}
                              className="h-7 gap-1 border-[#d6ad60]/30 text-[10px] text-[#d6ad60] hover:bg-[#d6ad60]/10"
                            >
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

        {/* ═══ تب refunds ═══ */}
        {activeTab === "refunds" && (
          <div className="space-y-3">
            {loading ? (
              <p className="py-4 text-center text-gray-400">در حال دریافت...</p>
            ) : refunds.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 py-10 text-center text-gray-400 backdrop-blur-xl">
                هیچ درخواست عودتی نیست.
              </div>
            ) : (
              refunds.map((r) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-start justify-between gap-3 rounded-2xl border border-purple-500/30 bg-gradient-to-br from-[#1a1635] to-[#0d0b1f] p-4 shadow-lg md:flex-row md:items-center"
                >
                  <div className="w-full min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="rounded-lg border border-purple-500/25 bg-purple-500/15 p-1.5">
                        <RefreshCw className="h-3.5 w-3.5 text-purple-400" />
                      </div>
                      <span className="dir-ltr font-mono text-sm font-bold text-white">
                        {r.user_phone}
                      </span>
                      <span className="rounded-full bg-[#d6ad60]/10 px-2 py-0.5 text-[10px] font-bold text-[#d6ad60]">
                        {getPlanNameFa(r.old_plan)} → {getPlanNameFa(r.new_plan)}
                      </span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                          r.status === "refunded"
                            ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
                            : r.status === "rejected"
                              ? "border-red-500/30 bg-red-500/10 text-red-400"
                              : "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                        }`}
                      >
                        {r.status === "refunded"
                          ? "✓ عودت شده"
                          : r.status === "rejected"
                            ? "✗ رد شده"
                            : "⏳ در حال بررسی"}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-[10px] text-gray-400">
                      <span>
                        مبلغ عودت:{" "}
                        <b className="text-purple-400" dir="ltr">
                          {r.refund_amount.toLocaleString("fa-IR")} تومان
                        </b>
                      </span>
                      <span>
                        تاریخ:{" "}
                        <b className="text-white">
                          {formatFaDateTime(r.created_at)}
                        </b>
                      </span>
                    </div>
                    {r.admin_note && (
                      <div className="rounded border border-yellow-500/20 bg-yellow-500/10 p-1.5 text-[10px] text-yellow-400">
                        <b>توضیحات:</b> {r.admin_note}
                      </div>
                    )}
                  </div>

                  {r.status === "pending" && (
                    <div className="flex w-full shrink-0 gap-2 border-t border-white/10 pt-2 md:w-auto md:border-r md:border-t-0 md:pl-3 md:pt-0">
                      <Button
                        size="sm"
                        onClick={() => {
                          setConfirmAction({
                            type: "action",
                            message: "تایید عودت وجه؟",
                            endpoint: `/admin/refunds/${r.id}/approve`,
                          });
                          setIsConfirmOpen(true);
                        }}
                        className="h-8 flex-1 gap-1 bg-purple-600 text-xs text-white hover:bg-purple-700 md:flex-none"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> تایید
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          setConfirmAction({
                            type: "action",
                            message: "رد درخواست عودت؟",
                            endpoint: `/admin/refunds/${r.id}/reject`,
                          });
                          setIsConfirmOpen(true);
                        }}
                        className="h-8 flex-1 gap-1 text-xs md:flex-none"
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

        {/* ═══ تب zibal ═══ */}
        {activeTab === "zibal" && (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-10 text-center">
            <Wallet className="mx-auto mb-3 h-12 w-12 text-gray-500" />
            <h3 className="mb-2 text-lg font-bold text-white">
              اتصال به درگاه زیبال
            </h3>
            <p className="mx-auto mb-4 max-w-md text-xs leading-relaxed text-gray-400">
              این تب برای بررسی و تطبیق تراکنش‌های درگاه زیبال با سیستم است. پس از
              راه‌اندازی درگاه، تراکنش‌ها به‌طور خودکار اینجا نمایش داده می‌شوند.
            </p>
            <div className="inline-flex items-center gap-2 rounded-lg border border-yellow-500/20 bg-yellow-500/10 px-3 py-1.5">
              <Clock className="h-3.5 w-3.5 text-yellow-400" />
              <span className="text-[10px] font-bold text-yellow-400">
                در حال توسعه
              </span>
            </div>
          </div>
        )}

        {/* ═══ تب tools ═══ */}
        {activeTab === "tools" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur-xl">
              <div className="mb-4 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                <h3 className="flex items-center gap-2 text-base font-bold text-[#d6ad60]">
                  <Database className="h-5 w-5" /> بک‌آپ
                </h3>
                <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                  <Button
                    onClick={handleBackup}
                    disabled={backupLoading}
                    size="sm"
                    className="gap-1 bg-[#d6ad60] font-bold text-[#101827] hover:bg-[#d6ad60]/90"
                  >
                    {backupLoading ? (
                      "..."
                    ) : (
                      <>
                        <Download className="h-3 w-3" /> بک‌آپ جدید
                      </>
                    )}
                  </Button>
                  <RestoreGuide backups={backups} />
                </div>
              </div>
              {backups.length === 0 ? (
                <p className="py-2 text-center text-xs text-gray-500">
                  هنوز بک‌آپی ساخته نشده.
                </p>
              ) : (
                <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
                  <label className="mb-1 flex cursor-pointer items-center gap-2 text-[10px] text-gray-500">
                    <input
                      type="checkbox"
                      checked={
                        selectedBackups.length === backups.length &&
                        backups.length > 0
                      }
                      onChange={toggleAllBackups}
                      className="accent-[#d6ad60]"
                    />
                    انتخاب همه
                  </label>
                  {backups.map((b) => (
                    <div
                      key={b.name}
                      className={`flex items-center justify-between gap-2 rounded-lg border ${
                        selectedBackups.includes(b.name)
                          ? "border-[#d6ad60]/50 bg-[#d6ad60]/10"
                          : "border-white/5 bg-white/5"
                      } px-3 py-2`}
                    >
                      <div className="flex min-w-0 flex-1 items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedBackups.includes(b.name)}
                          onChange={() => toggleBackupSelection(b.name)}
                          className="h-3 w-3 accent-[#d6ad60]"
                        />
                        <p className="dir-ltr truncate text-[11px] text-gray-300">
                          {b.name}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-gray-400 hover:text-[#d6ad60]"
                        onClick={async () => {
                          try {
                            const res = await fetch(
                              `${apiUrl}/admin/backups/${b.name}/download`,
                              {
                                headers: {
                                  Authorization: `Bearer ${token}`,
                                },
                              }
                            );
                            if (!res.ok) throw new Error("دانلود ناموفق");
                            const blob = await res.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = b.name;
                            a.click();
                            window.URL.revokeObjectURL(url);
                          } catch (err: any) {
                            alert(err.message || "خطا در دانلود");
                          }
                        }}
                      >
                        <Download className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                  {selectedBackups.length > 0 && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() =>
                        requestConfirm(
                          "delete_backups",
                          `${selectedBackups.length} بک‌آپ انتخاب شده حذف شوند؟`,
                          undefined,
                          undefined,
                          selectedBackups
                        )
                      }
                      className="mt-2 h-7 w-full gap-1 text-[10px]"
                    >
                      <Trash2 className="h-3 w-3" /> حذف انتخاب شده‌ها
                    </Button>
                  )}
                </div>
              )}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldAlert
                    className={`h-5 w-5 ${isMaintenance ? "text-red-400" : "text-green-400"}`}
                  />
                  <div>
                    <h3 className="text-sm font-bold text-white">
                      حالت تعمیرات
                    </h3>
                    <p
                      className={`text-[10px] ${isMaintenance ? "text-red-400" : "text-green-400"}`}
                    >
                      {isMaintenance ? "سایت در حال تعمیرات است" : "سایت فعال است"}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => toggleMaintenance(!isMaintenance)}
                  disabled={maintenanceLoading}
                  size="sm"
                  className={`gap-1 font-bold ${
                    isMaintenance
                      ? "bg-green-500 text-white hover:bg-green-600"
                      : "bg-red-500 text-white hover:bg-red-600"
                  }`}
                >
                  {maintenanceLoading
                    ? "..."
                    : isMaintenance
                      ? "خروج از تعمیرات"
                      : "فعال‌سازی"}
                </Button>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur-xl">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-[#d6ad60]">
                <Wrench className="h-4 w-4" /> ابزارهای مدیریت (به‌زودی)
              </h3>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  "پاکسازی کش",
                  "بازسازی آمار",
                  "ارسال پیام",
                  "واچ‌لیست",
                  "گزارش مالی",
                  "لاگ ادمین",
                ].map((t, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-white/5 bg-white/5 p-2 text-center opacity-40"
                  >
                    <p className="text-[10px] text-gray-400">{t}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══ تب verification ═══ */}
        {activeTab === "verification" && (
          <div className="space-y-4">
            
            {/* ۱. آمار کامل و اصلی (موضوع اصلی) - کشویی */}
            <details className="group rounded-2xl border border-white/10 bg-white/5 shadow-xl backdrop-blur-xl [&_summary::-webkit-details-marker]:hidden" open>
              <summary className="flex cursor-pointer items-center justify-between p-4">
                <h3 className="flex items-center gap-2 text-sm font-bold text-[#d6ad60]">
                  <CheckCircle className="h-4 w-4" />
                  آمار کامل و تاریخچه راستی‌آزمایی
                </h3>
                <ChevronDown className="h-4 w-4 text-gray-400 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-white/10 p-4">
                <BacktestStats />
              </div>
            </details>

            {/* ۲. کنترل آمار نمایشی (بخش تنظیمات مدیر) - کشویی و پیش‌فرض بسته */}
            <details className="group rounded-2xl border border-[#d6ad60]/30 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] shadow-xl [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer items-center justify-between p-4">
                <h3 className="flex items-center gap-2 text-sm font-bold text-[#d6ad60]">
                  <Target className="h-4 w-4" />
                  کنترل آمار نمایشی سایت (تنظیمات مدیر)
                </h3>
                <ChevronDown className="h-4 w-4 text-gray-400 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-[#d6ad60]/20 p-4">
                <p className="mb-4 text-[10px] leading-relaxed text-gray-400">
                  این اعداد در صفحه اصلی به کاربران نمایش داده می‌شوند. می‌تونی برای هر استراتژی، نرخ برد و دقت پیش‌بینی رو به صورت جداگانه و خوش‌بینانه تنظیم کنی.
                </p>

                {!siteStats ? (
                  <p className="py-2 text-center text-xs text-gray-500">
                    در حال بارگذاری...
                  </p>
                ) : (
                  <div className="space-y-3">
                    
                    {/* بخش استراتژی‌ها */}
                    {["scalp", "swing", "position"].map((strat) => {
                      const sData = siteStats.by_strategy?.[strat];
                      if (!sData) return null;
                      const stratName = strat === "scalp" ? "اسکالپ" : strat === "swing" ? "سوئینگ" : "پوزیشن";
                      
                      return (
                        <div key={strat} className="rounded-lg border border-white/10 bg-black/20 p-4 space-y-3">
                          <h4 className="text-xs font-bold text-[#d6ad60]">استراتژی: {stratName} (کل: {sData.total} سیگنال)</h4>
                          
                          {/* نرخ برد */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex-1">
                              <p className="text-[10px] text-gray-400">نرخ برد (واقعی: {sData.real_win_rate.toFixed(1)}٪)</p>
                              <Input
                                type="number" step="0.1"
                                value={inputWinRateDict[strat] || ""}
                                onChange={(e) => setInputWinRateDict({...inputWinRateDict, [strat]: e.target.value})}
                                className="h-7 text-xs bg-black/40 mt-1" dir="ltr" placeholder="مثلا 75"
                              />
                            </div>
                            <div className="flex flex-col gap-1 mt-4">
                              <Button size="sm" onClick={() => saveOverride(`win_rate_${strat}`, parseFloat(inputWinRateDict[strat]))} className="h-6 text-[10px] bg-green-600">ذخیره</Button>
                              {sData.has_override?.win_rate && (
                                <Button size="sm" variant="outline" onClick={() => deleteOverride(`win_rate_${strat}`)} className="h-6 text-[10px] text-red-400 border-red-500/30">واقعی</Button>
                              )}
                            </div>
                          </div>

                          {/* دقت پیش‌بینی */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex-1">
                              <p className="text-[10px] text-gray-400">دقت پیش‌بینی (واقعی: {sData.real_direction_accuracy.toFixed(1)}٪)</p>
                              <Input
                                type="number" step="0.1"
                                value={inputDirAccDict[strat] || ""}
                                onChange={(e) => setInputDirAccDict({...inputDirAccDict, [strat]: e.target.value})}
                                className="h-7 text-xs bg-black/40 mt-1" dir="ltr" placeholder="مثلا 80"
                              />
                            </div>
                            <div className="flex flex-col gap-1 mt-4">
                              <Button size="sm" onClick={() => saveOverride(`direction_accuracy_${strat}`, parseFloat(inputDirAccDict[strat]))} className="h-6 text-[10px] bg-purple-600">ذخیره</Button>
                              {sData.has_override?.direction_accuracy && (
                                <Button size="sm" variant="outline" onClick={() => deleteOverride(`direction_accuracy_${strat}`)} className="h-6 text-[10px] text-red-400 border-red-500/30">واقعی</Button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {/* مجموع کل سیگنال‌ها */}
                    <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs font-medium text-white">مجموع سیگنال نمایشی</p>
                          <p className="text-[10px] text-gray-400 mt-1">مقدار واقعی: {siteStats.real_total_signals} سیگنال (۱۰۰ اخیر)</p>
                        </div>
                        <div className="flex gap-2 items-center">
                          <Input
                            type="number" min="0"
                            value={inputTotalSignals || ""}
                            onChange={(e) => setInputTotalSignals(e.target.value)}
                            className="h-8 w-24 bg-black/40" dir="ltr" placeholder="450"
                          />
                          <Button size="sm" onClick={() => saveOverride("total_signals", parseFloat(inputTotalSignals))} className="h-8 bg-blue-600">ذخیره</Button>
                          {siteStats.has_override?.total_signals && (
                            <Button size="sm" variant="outline" onClick={() => deleteOverride("total_signals")} className="h-8 text-red-400 border-red-500/30">واقعی</Button>
                          )}
                        </div>
                      </div>
                    </div>

                  </div>
                )}
              </div>
            </details>

          </div>
        )}
      </main>

      {/* ═══ مودال افزودن کاربر ═══ */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">
              افزودن کاربر جدید
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-xs text-gray-400">شماره موبایل</label>
              <Input
                value={newUserPhone}
                onChange={(e) => setNewUserPhone(e.target.value)}
                className="mt-1 border-white/10 bg-black/30"
                dir="ltr"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">نام</label>
              <Input
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                className="mt-1 border-white/10 bg-black/30"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">پلن</label>
              <select
                value={newUserPlan}
                onChange={(e) => setNewUserPlan(e.target.value)}
                className="mt-1 h-10 w-full rounded-md border-white/10 bg-black/30 px-2 text-sm"
              >
                <option value="free">رایگان</option>
                <option value="1_month">یک ماهه</option>
                <option value="3_months">سه ماهه</option>
                <option value="6_months">شش ماهه</option>
                <option value="12_months">یک ساله</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400">مدت (روز)</label>
              <Input
                type="number"
                value={newUserDays}
                onChange={(e) => setNewUserDays(Number(e.target.value))}
                className="mt-1 border-white/10 bg-black/30"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sendSmsAdd"
                checked={newUserSendSms}
                onChange={(e) => setNewUserSendSms(e.target.checked)}
                className="accent-[#d6ad60]"
              />
              <label htmlFor="sendSmsAdd" className="text-xs text-gray-400">
                ارسال پیامک اطلاع‌رسانی
              </label>
            </div>
            <Button
              onClick={handleAddUser}
              className="w-full bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
            >
              ثبت کاربر
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ مودال جزئیات کاربر ═══ */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-[#d6ad60]">
              <UserCheck className="h-5 w-5" /> مدیریت کاربر:{" "}
              {selectedUser?.phone}
            </DialogTitle>
          </DialogHeader>
          {userDetails ? (
            <div className="space-y-6 py-4">
              <div className="grid grid-cols-1 gap-4 rounded-xl border border-white/5 bg-black/20 p-4 text-sm sm:grid-cols-2">
                <div>
                  <span className="text-gray-400">نام:</span>{" "}
                  {userDetails.user.full_name || "نامشخص"}
                </div>
                <div>
                  <span className="text-gray-400">تاریخ عضویت:</span>{" "}
                  {formatFaDate(userDetails.user.created_at)}
                </div>
                <div>
                  <span className="text-gray-400">آخرین ورود:</span>{" "}
                  {formatFaDateTime(userDetails.user.last_login)}
                </div>
                <div>
                  <span className="text-gray-400">آخرین IP:</span>{" "}
                  <span className="dir-ltr font-mono text-gray-300">
                    {userDetails.user.last_ip}
                  </span>
                </div>
                <div className="sm:col-span-2">
                  <span className="text-gray-400">مرورگر:</span>{" "}
                  <span
                    className="text-xs text-gray-300"
                    title={userDetails.user.last_user_agent}
                  >
                    {userDetails.user.last_user_agent}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-3">
                  <p className="mb-1 text-[10px] text-green-400">
                    جمع پرداختی‌های تایید شده:
                  </p>
                  <p className="text-lg font-bold text-green-400" dir="ltr">
                    {((userDetails as any).total_paid || 0).toLocaleString(
                      "fa-IR"
                    )}
                    <span className="mr-1 text-xs text-gray-400">تومان</span>
                  </p>
                </div>
                <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-3">
                  <p className="mb-1 text-[10px] text-purple-400">
                    جمع عودت‌های وجه:
                  </p>
                  <p className="text-lg font-bold text-purple-400" dir="ltr">
                    {((userDetails as any).total_refunded || 0).toLocaleString(
                      "fa-IR"
                    )}
                    <span className="mr-1 text-xs text-gray-400">تومان</span>
                  </p>
                </div>
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3">
                  <p className="mb-1 text-[10px] text-blue-400">
                    مانده خالص:
                  </p>
                  <p className="text-lg font-bold text-blue-400" dir="ltr">
                    {((userDetails as any).net_balance || 0).toLocaleString(
                      "fa-IR"
                    )}
                    <span className="mr-1 text-xs text-gray-400">تومان</span>
                  </p>
                </div>
              </div>

              {!userDetails.user.is_active && (
                <div className="flex items-center justify-between rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-3">
                  <div className="flex items-center gap-2">
                    <UserX className="h-5 w-5 text-yellow-400" />
                    <span className="text-xs text-yellow-400">
                      این کاربر غیرفعال است
                    </span>
                  </div>
                  <Button
                    size="sm"
                    onClick={handleActivateUser}
                    className="gap-1 bg-green-600 text-white hover:bg-green-700"
                  >
                    <UserCheck2 className="h-4 w-4" /> فعال‌سازی کاربر
                  </Button>
                </div>
              )}

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  تغییر دستی پلن اشتراک:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {["1_month", "3_months", "6_months", "12_months"].map(
                    (plan) => (
                      <Button
                        key={plan}
                        size="sm"
                        variant="outline"
                        className="border-white/10 text-gray-300 hover:bg-white/10 hover:text-white"
                        onClick={() => handleChangePlan(plan)}
                      >
                        {getPlanNameFa(plan)}
                      </Button>
                    )
                  )}
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="sendSmsPlan"
                    checked={sendSmsPlan}
                    onChange={(e) => setSendSmsPlan(e.target.checked)}
                    className="accent-[#d6ad60]"
                  />
                  <label
                    htmlFor="sendSmsPlan"
                    className="text-[10px] text-gray-400"
                  >
                    ارسال پیامک اطلاع‌رسانی
                  </label>
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  تغییر دستی تاریخ انقضا:
                </h4>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    type="number"
                    placeholder="مثلاً 30"
                    value={adjustDays || ""}
                    onChange={(e) => setAdjustDays(Number(e.target.value))}
                    className="h-9 w-24 border-white/10 bg-black/30 text-white"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleAdjustDays}
                    className="gap-1 border-green-500/20 text-green-400 hover:bg-green-500/10"
                  >
                    اعمال روز
                  </Button>
                  <span className="text-xs text-gray-500">
                    (عدد منفی برای کاهش)
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="sendSmsDays"
                    checked={sendSmsDays}
                    onChange={(e) => setSendSmsDays(e.target.checked)}
                    className="accent-[#d6ad60]"
                  />
                  <label
                    htmlFor="sendSmsDays"
                    className="text-[10px] text-gray-400"
                  >
                    ارسال پیامک اطلاع‌رسانی
                  </label>
                </div>
              </div>

              {user.phone === "09129630901" && (
                <div>
                  <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                    مدیریت سطح دسترسی:
                  </h4>
                  {selectedUser.is_admin ? (
                    selectedUser.phone !== "09129630901" && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() =>
                          handleAction(
                            selectedUser.id,
                            `/admin/users/${selectedUser.id}/remove-admin`,
                            "دسترسی ادمین لغو شود؟"
                          )
                        }
                        className="gap-1"
                      >
                        <ShieldAlert className="h-4 w-4" /> لغو دسترسی ادمین
                      </Button>
                    )
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        handleAction(
                          selectedUser.id,
                          `/admin/users/${selectedUser.id}/make-admin`,
                          "کاربر به مدیر ارتقا یابد؟"
                        )
                      }
                      className="gap-1 border-orange-500/20 text-orange-400 hover:bg-orange-500/10"
                    >
                      <ShieldAlert className="h-4 w-4" /> ارتقا به مدیر
                    </Button>
                  )}
                </div>
              )}

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  ریست رمز عبور (توسط مدیر):
                </h4>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    placeholder="رمز جدید (حداقل ۶ حرف)"
                    value={newPasswordForUser}
                    onChange={(e) => setNewPasswordForUser(e.target.value)}
                    className="h-9 flex-1 border-white/10 bg-black/30 text-sm text-white"
                    dir="ltr"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleResetPassword}
                    className="gap-1 border-blue-500/20 text-blue-400 hover:bg-blue-500/10"
                  >
                    <Lock className="h-3.5 w-3.5" /> ثبت
                  </Button>
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  لغو اشتراک و عودت وجه:
                </h4>
                <p className="mb-2 text-[10px] leading-relaxed text-gray-400">
                  با ثبت این درخواست، پلن کاربر به پلن جدید تغییر می‌کند و مبلغ
                  عودت به حساب او بازگردانده می‌شود.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsRefundModalOpen(true)}
                  className="gap-1 border-red-500/20 text-red-400 hover:bg-red-500/10"
                >
                  <DollarSign className="h-3.5 w-3.5" /> ثبت درخواست عودت
                </Button>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  آمار دانلود افزونه:
                </h4>
                {extStats ? (
                  <div className="space-y-2 rounded-lg border border-white/5 bg-black/30 p-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">
                        تعداد کل دانلودها:
                      </span>
                      <span className="font-bold text-white">
                        {extStats.total_downloads} بار
                      </span>
                    </div>

                    {extStats.logs && extStats.logs.length > 0 && (
                      <div className="mt-2 max-h-40 space-y-1.5 overflow-y-auto border-t border-white/10 pt-2 pr-1">
                        {extStats.logs.map((log: any, idx: number) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between rounded bg-black/40 p-1.5 text-[10px]"
                          >
                            <span className="text-gray-300">
                              {formatFaDateTime(log.downloaded_at)}
                            </span>
                            <span className="dir-ltr font-mono text-gray-400">
                              {log.ip_address}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {extStats.total_downloads > 0 && (
                      <div className="mt-1 text-[10px] text-gray-500">
                        آخرین دانلود:{" "}
                        {formatFaDateTime(extStats.logs[0]?.downloaded_at)}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-2 text-center text-xs text-gray-500">
                    در حال بارگذاری...
                  </div>
                )}
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  حذف / غیرفعال‌سازی کاربر:
                </h4>
                <div className="mb-2 flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="deleteHard"
                    checked={deleteHard}
                    onChange={(e) => setDeleteHard(e.target.checked)}
                    className="accent-red-500"
                  />
                  <label
                    htmlFor="deleteHard"
                    className="text-[10px] text-red-400"
                  >
                    حذف کامل (غیرقابل بازگشت)
                  </label>
                </div>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleDeleteUser}
                  className="gap-1"
                >
                  <Trash2 className="h-4 w-4" /> حذف / غیرفعال‌سازی کاربر
                </Button>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  تاریخچه اشتراک‌ها:
                </h4>
                <div className="space-y-2">
                  {userDetails.subscriptions.length === 0 ? (
                    <p className="text-xs text-gray-500">ندارد</p>
                  ) : (
                    userDetails.subscriptions.map((s: any) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between rounded border border-white/5 bg-white/5 p-2 text-xs"
                      >
                        <span className="font-bold text-gray-200">
                          {getPlanNameFa(s.plan)}
                        </span>
                        <span className="text-gray-400">
                          تا {s.end ? formatFaDate(s.end) : "نامحدود"}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-bold text-[#d6ad60]">
                  تاریخچه پرداخت‌ها:
                </h4>
                <div className="space-y-2">
                  {userDetails.payments.length === 0 ? (
                    <p className="text-xs text-gray-500">ندارد</p>
                  ) : (
                    userDetails.payments.map((p: any) => {
                      const isRefund =
                        p.payment_method === "refund" || p.plan === "refund";
                      const bgColor = isRefund
                        ? "border-purple-500/20 bg-purple-500/10"
                        : "border-white/5 bg-white/5";
                      const textColor = isRefund
                        ? "text-purple-400"
                        : "text-gray-200";
                      const statusBg =
                        p.status === "approved"
                          ? "border-green-500/30 bg-green-500/10 text-green-400"
                          : p.status === "pending"
                            ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                            : p.status === "refunded"
                              ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
                              : "border-red-500/30 bg-red-500/10 text-red-400";
                      const statusText =
                        p.status === "approved"
                          ? "تایید شده"
                          : p.status === "pending"
                            ? "در حال بررسی"
                            : p.status === "refunded"
                              ? "عودت شده"
                              : "رد شده";

                      return (
                        <div
                          key={p.id}
                          className={`flex items-center justify-between rounded border p-2 text-xs ${bgColor}`}
                        >
                          <span className={`font-bold ${textColor}`}>
                            {getPlanNameFa(p.plan)}
                          </span>
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${statusBg}`}
                          >
                            {statusText}
                          </span>
                          <span className="text-gray-400">
                            {formatFaDate(p.created_at)}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-10">
              <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-t-2 border-[#d6ad60]"></div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ═══ مودال یادداشت ═══ */}
      <Dialog open={isNoteModalOpen} onOpenChange={setIsNoteModalOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">
              {noteAction?.type === "approve" ? "تایید پرداخت" : "رد پرداخت"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-gray-400">
              لطفاً دلیل{" "}
              {noteAction?.type === "approve" ? "تایید" : "رد"} را وارد کنید
              (اختیاری):
            </p>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="مثلاً: مبلغ کمتر واریز شده بود..."
              className="h-24 w-full rounded-md border border-white/10 bg-black/30 p-2 text-sm text-white"
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setIsNoteModalOpen(false)}
                className="flex-1 border-white/10 text-gray-300"
              >
                لغو
              </Button>
              <Button
                onClick={handleApproveWithNote}
                disabled={noteLoading}
                className={`flex-1 ${noteAction?.type === "approve" ? "bg-green-600" : "bg-red-600"} text-white`}
              >
                {noteLoading ? "..." : "تایید نهایی"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ مودال تراکنش ═══ */}
      <Dialog open={isTxDetailOpen} onOpenChange={setIsTxDetailOpen}>
        <DialogContent className="max-w-lg border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">
              جزئیات و ویرایش تراکنش
            </DialogTitle>
          </DialogHeader>
          {selectedTx && (
            <div className="space-y-4 py-2">
              <div className="space-y-1.5 rounded-lg border border-white/5 bg-black/30 p-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">کاربر:</span>
                  <span className="dir-ltr font-mono text-white">
                    {selectedTx.user_phone}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">پلن:</span>
                  <span className="text-white">
                    {getPlanNameFa(selectedTx.plan)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">روش پرداخت:</span>
                  <span className="text-white">
                    {paymentMethodLabel(selectedTx.payment_method)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">تاریخ درخواست:</span>
                  <span className="text-white">
                    {formatFaDateTime(selectedTx.created_at)}
                  </span>
                </div>
                {selectedTx.payment_time && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">زمان واریز:</span>
                    <span className="text-white">
                      {selectedTx.payment_time}
                    </span>
                  </div>
                )}
                {selectedTx.receipt_note && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">توضیحات کاربر:</span>
                    <span className="text-white">
                      {selectedTx.receipt_note}
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-gray-400">
                    مبلغ (تومان)
                  </label>
                  <Input
                    type="number"
                    value={txNewAmount}
                    onChange={(e) => setTxNewAmount(Number(e.target.value))}
                    className="border-white/10 bg-black/30 text-white"
                    dir="ltr"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-400">
                    وضعیت
                  </label>
                  <select
                    value={txNewStatus}
                    onChange={(e) => setTxNewStatus(e.target.value)}
                    className="h-10 w-full rounded-md border-white/10 bg-black/30 px-2 text-sm"
                  >
                    <option value="pending">در حال بررسی</option>
                    <option value="approved">تایید شده</option>
                    <option value="rejected">رد شده</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-gray-400">
                    یادداشت ادمین
                  </label>
                  <textarea
                    value={txNewNote}
                    onChange={(e) => setTxNewNote(e.target.value)}
                    placeholder="دلیل تغییر..."
                    className="h-24 w-full rounded-md border border-white/10 bg-black/30 p-2 text-sm text-white"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="txSendSms"
                    checked={txSendSms}
                    onChange={(e) => setTxSendSms(e.target.checked)}
                    className="accent-[#d6ad60]"
                  />
                  <label
                    htmlFor="txSendSms"
                    className="text-xs text-gray-400"
                  >
                    ارسال پیامک اطلاع‌رسانی به کاربر
                  </label>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setIsTxDetailOpen(false)}
                  className="flex-1 border-white/10 text-gray-300"
                >
                  لغو
                </Button>
                <Button
                  onClick={saveTxDetail}
                  disabled={txDetailLoading}
                  className="flex-1 bg-[#d6ad60] font-bold text-[#101827]"
                >
                  {txDetailLoading ? "..." : "ذخیره تغییرات"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ═══ مودال عودت ═══ */}
      <Dialog open={isRefundModalOpen} onOpenChange={setIsRefundModalOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="text-[#d6ad60]">
              ثبت درخواست عودت
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                نوع اقدام (فقط جهت اطلاع)
              </label>
              <select
                value={refundNewPlan}
                onChange={(e) => setRefundNewPlan(e.target.value)}
                className="h-10 w-full rounded-md border-white/10 bg-black/30 px-2 text-sm"
              >
                <option value="no_change">بدون تغییر (فقط عودت وجه)</option>
                <option value="deactivate">غیرفعال‌سازی اشتراک</option>
                <option value="1_month">تغییر به یک ماهه</option>
                <option value="3_months">تغییر به سه ماهه</option>
                <option value="6_months">تغییر به شش ماهه</option>
                <option value="12_months">تغییر به یک ساله</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                مبلغ عودت (تومان)
              </label>
              <Input
                type="number"
                value={refundAmount || ""}
                onChange={(e) => setRefundAmount(Number(e.target.value))}
                className="border-white/10 bg-black/30 text-white"
                dir="ltr"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                توضیحات (مثلاً شماره کارت)
              </label>
              <textarea
                value={refundNote}
                onChange={(e) => setRefundNote(e.target.value)}
                placeholder="شماره کارت: ..."
                className="h-24 w-full rounded-md border border-white/10 bg-black/30 p-2 text-sm text-white"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setIsRefundModalOpen(false)}
                className="flex-1 border-white/10 text-gray-300"
              >
                لغو
              </Button>
              <Button
                onClick={handleCreateRefund}
                disabled={refundLoading}
                className="flex-1 bg-[#d6ad60] font-bold text-[#101827]"
              >
                {refundLoading ? "..." : "ثبت درخواست"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ═══ مودال تایید ═══ */}
      <Dialog open={isConfirmOpen} onOpenChange={setIsConfirmOpen}>
        <DialogContent className="max-w-md border-white/10 bg-[#0d1b2d] text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-[#d6ad60]">
              <AlertTriangle className="h-5 w-5" /> تایید عملیات
            </DialogTitle>
          </DialogHeader>
          <p className="py-4 text-sm text-gray-300">{confirmAction?.message}</p>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setIsConfirmOpen(false)}
              className="border-white/10 text-gray-300"
            >
              لغو
            </Button>
            <Button
              onClick={executeAction}
              className={
                confirmAction?.type === "delete_backups"
                  ? "bg-red-500 text-white hover:bg-red-600"
                  : "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90"
              }
            >
              تایید
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Footer />
    </div>
  );
}