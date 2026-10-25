"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LogOut, CheckCircle2, XCircle, CreditCard, Users, Calendar, Clock, Globe, Monitor, UserCheck, Download, Upload, History, PlusCircle, Activity, ShieldAlert, MinusCircle, ArrowUpDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { motion } from "framer-motion";
import Link from "next/link";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "1_month": "یک ماهه", "3_months": "سه ماهه", "6_months": "شش ماهه", "12_months": "یک ساله",
    "free": "رایگان", "monthly": "ماهانه", "بدون اشتراک": "بدون اشتراک", "نامحدود (مدیر)": "نامحدود (مدیر)"
  };
  return map[plan] || plan || "نامشخص";
};

export default function AdminPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"payments" | "users">("users");
  const [payments, setPayments] = useState<any[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userDetails, setUserDetails] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [adjustDays, setAdjustDays] = useState<number>(0);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const token = getToken();

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
        if (res.ok) setPayments(data.items || []);
      } else {
        const res = await fetch(`${apiUrl}/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) setUsersList(data.items || []);
      }
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const sortedUsers = [...usersList].sort((a, b) => {
    if (!sortConfig) return 0;
    const { key, direction } = sortConfig;
    if (a[key] < b[key]) return direction === 'asc' ? -1 : 1;
    if (a[key] > b[key]) return direction === 'asc' ? 1 : -1;
    return 0;
  });

  const requestSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const openUserDetails = async (u: any) => {
    setSelectedUser(u);
    setIsModalOpen(true);
    setUserDetails(null);
    setAdjustDays(0);
    try {
      const res = await fetch(`${apiUrl}/admin/users/${u.id}/details`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (res.ok) setUserDetails(data);
    } catch (err) { console.error(err); }
  };

  const handleAction = async (id: number, action: string, endpoint: string, body: any = null) => {
    if (!confirm("آیا مطمئنید؟")) return;
    try {
      const res = await fetch(`${apiUrl}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: body ? JSON.stringify(body) : null });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      alert(data.message);
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) { alert(err.message); }
  };

  const handleBackup = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/backup`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error("خطا");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `trademun_backup_${Date.now()}.db`; a.click();
    } catch (err) { alert("خطا"); }
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
    const input = document.createElement("input"); input.type = "file"; input.accept = ".db";
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

  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#07111f] text-white">
      <div className="absolute inset-0 z-0 opacity-20">
        <div className="absolute inset-0 bg-gradient-to-br from-[#d6ad6010] via-transparent to-[#10b98110]" />
      </div>

      <header className="relative z-10 flex items-center justify-between p-4 sm:p-6 border-b border-white/5">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <img src="/icon-192.png" alt="Trademun" className="h-10 w-10 rounded-xl object-contain" />
          <span className="text-xl font-bold">تریدمون</span>
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#d6ad60] bg-[#d6ad60]/10 px-3 py-1 rounded-full hidden sm:inline-block">مدیر سیستم</span>
          <Button variant="destructive" size="sm" onClick={() => { removeToken(); router.replace("/login"); }} className="gap-2">
            <LogOut className="h-4 w-4" /> خروج
          </Button>
        </div>
      </header>

      <main className="relative z-10 container mx-auto p-4 py-8 max-w-6xl space-y-6">
        
        {/* هدر پنل */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-[#0d1b2dd0] p-4 rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="bg-[#d6ad60]/10 p-2 rounded-lg"><UserCheck className="h-6 w-6 text-[#d6ad60]" /></div>
            <div>
              <h1 className="text-xl font-bold text-white">اتاق فرمان</h1>
              <p className="text-xs text-gray-400">خوش آمدید، {user.full_name || "مدیر"}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleBackup} className="gap-2 border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10"><Download className="h-4 w-4" /> بک‌آپ</Button>
            <Button variant="outline" size="sm" onClick={handleExcel} className="gap-2 border-green-500/30 text-green-500 hover:bg-green-500/10"><Download className="h-4 w-4" /> خروجی اکسل</Button>
            <Button variant="outline" size="sm" onClick={handleRestore} className="gap-2 border-orange-500/30 text-orange-500 hover:bg-orange-500/10"><Upload className="h-4 w-4" /> بازگردانی</Button>
          </div>
        </div>

        {/* کارت‌های آماری */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-[#0d1b2dd0] p-4 rounded-xl border border-white/10 shadow-lg flex items-center gap-3 backdrop-blur-md">
            <div className="bg-[#d6ad60]/10 p-2 rounded-lg text-[#d6ad60]"><Users className="h-5 w-5" /></div>
            <div><p className="text-xs text-gray-400">کل کاربران</p><p className="text-lg font-bold text-white">{usersList.length}</p></div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-[#0d1b2dd0] p-4 rounded-xl border border-white/10 shadow-lg flex items-center gap-3 backdrop-blur-md">
            <div className="bg-green-500/10 p-2 rounded-lg text-green-500"><Activity className="h-5 w-5" /></div>
            <div><p className="text-xs text-gray-400">کاربران فعال</p><p className="text-lg font-bold text-white">{usersList.filter(u => u.plan !== "free").length}</p></div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-[#0d1b2dd0] p-4 rounded-xl border border-white/10 shadow-lg flex items-center gap-3 backdrop-blur-md">
            <div className="bg-yellow-500/10 p-2 rounded-lg text-yellow-500"><CreditCard className="h-5 w-5" /></div>
            <div><p className="text-xs text-gray-400">درخواست‌های در انتظار</p><p className="text-lg font-bold text-white">{payments.length}</p></div>
          </motion.div>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-2 border-b border-white/10 pb-2 overflow-x-auto">
          <Button variant={activeTab === "users" ? "default" : "ghost"} onClick={() => setActiveTab("users")} className={`gap-2 shrink-0 ${activeTab === "users" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><Users className="h-4 w-4" /> مدیریت کاربران</Button>
          <Button variant={activeTab === "payments" ? "default" : "ghost"} onClick={() => setActiveTab("payments")} className={`gap-2 shrink-0 ${activeTab === "payments" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}><CreditCard className="h-4 w-4" /> درخواست‌های پرداخت</Button>
        </div>

        {activeTab === "users" ? (
          <div className="space-y-4">
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0d1b2dd0] shadow-xl backdrop-blur-xl">
                <table className="w-full text-sm text-right">
                  <thead className="bg-white/5 text-gray-400">
                    <tr>
                      <th className="px-4 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('phone')}>شماره موبایل {sortConfig?.key === 'phone' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-4 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('full_name')}>نام {sortConfig?.key === 'full_name' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-4 py-3 font-medium">نقش</th>
                      <th className="px-4 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('plan')}>پلن {sortConfig?.key === 'plan' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-4 py-3 font-medium cursor-pointer hover:text-[#d6ad60]" onClick={() => requestSort('created_at')}>تاریخ عضویت {sortConfig?.key === 'created_at' && <ArrowUpDown className="inline h-3 w-3" />}</th>
                      <th className="px-4 py-3 font-medium">عملیات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {sortedUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3 font-mono dir-ltr font-bold text-white">{u.phone}</td>
                        <td className="px-4 py-3 text-gray-300">{u.full_name}</td>
                        <td className="px-4 py-3">{u.is_admin ? <span className="text-green-500 text-xs font-bold bg-green-500/10 px-2 py-1 rounded flex items-center gap-1 w-fit"><ShieldAlert className="h-3 w-3" /> مدیر</span> : <span className="text-gray-400 text-xs">کاربر</span>}</td>
                        <td className="px-4 py-3"><span className="bg-[#d6ad60]/10 text-[#d6ad60] px-2 py-1 rounded text-xs font-bold">{getPlanNameFa(u.plan)}</span></td>
                        <td className="px-4 py-3 text-gray-400 text-xs">{new Date(u.created_at).toLocaleDateString('fa-IR')}</td>
                        <td className="px-4 py-3"><Button size="sm" variant="outline" className="text-xs h-8 gap-1 border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => openUserDetails(u)}><History className="h-3 w-3" /> جزئیات</Button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {loading ? <p className="text-center text-gray-400 py-4">در حال دریافت...</p> : payments.length === 0 ? <div className="text-center text-gray-400 py-6 bg-[#0d1b2dd0] rounded-2xl border border-white/10">هیچ درخواستی نیست.</div> : (
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
                    <Button size="sm" className="flex-1 md:flex-none bg-green-600 hover:bg-green-700 text-white gap-1" onClick={() => handleAction(p.id, "approve", `/admin/payments/${p.id}/approve`)}><CheckCircle2 className="h-4 w-4" /> تایید</Button>
                    <Button size="sm" variant="destructive" className="flex-1 md:flex-none gap-1" onClick={() => handleAction(p.id, "reject", `/admin/payments/${p.id}/reject`)}><XCircle className="h-4 w-4" /> رد</Button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}
      </main>

      {/* مدال جزئیات */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-[#0d1b2d] border-white/10 text-white">
          <DialogHeader><DialogTitle className="flex items-center gap-2 text-[#d6ad60]"><UserCheck className="h-5 w-5" /> مدیریت کاربر: {selectedUser?.phone}</DialogTitle></DialogHeader>
          {userDetails ? (
            <div className="space-y-6 py-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-black/20 p-4 rounded-xl border border-white/5">
                <div><span className="text-gray-400">نام:</span> {userDetails.user.full_name || "نامشخص"}</div>
                <div><span className="text-gray-400">تاریخ عضویت:</span> {new Date(userDetails.user.created_at).toLocaleDateString('fa-IR')}</div>
                <div><span className="text-gray-400">آخرین ورود:</span> {userDetails.user.last_login ? new Date(userDetails.user.last_login).toLocaleString('fa-IR') : "نامشخص"}</div>
                <div><span className="text-gray-400">آخرین IP:</span> <span className="font-mono dir-ltr text-gray-300">{userDetails.user.last_ip}</span></div>
                <div className="sm:col-span-2"><span className="text-gray-400">مرورگر:</span> <span className="text-xs text-gray-300" title={userDetails.user.last_user_agent}>{userDetails.user.last_user_agent}</span></div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی پلن اشتراک:</h4>
                <div className="flex flex-wrap gap-2">
                  {["1_month", "3_months", "6_months", "12_months"].map((plan) => (
                    <Button key={plan} size="sm" variant="outline" className="border-white/10 text-gray-300 hover:text-white hover:bg-white/10" onClick={() => handleAction(selectedUser.id, "change-plan", `/admin/users/${selectedUser.id}/change-plan?plan=${plan}`)}>{getPlanNameFa(plan)}</Button>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تغییر دستی تاریخ انقضا:</h4>
                <div className="flex flex-wrap items-center gap-2">
                  <Input type="number" placeholder="مثلاً 30" value={adjustDays || ""} onChange={(e) => setAdjustDays(Number(e.target.value))} className="w-24 h-9 bg-black/30 border-white/10 text-white" />
                  <Button size="sm" variant="outline" onClick={() => handleAction(selectedUser.id, "adjust-days", `/admin/users/${selectedUser.id}/adjust-days?days=${adjustDays}`)} className="gap-1 text-green-500 border-green-500/20 hover:bg-green-500/10">اعمال روز</Button>
                  <span className="text-xs text-gray-500">(عدد منفی برای کاهش)</span>
                </div>
              </div>

              {user.phone === "09129630901" && (
                <div>
                  <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">مدیریت سطح دسترسی:</h4>
                  {selectedUser.is_admin ? (
                    selectedUser.phone !== "09129630901" && (
                      <Button size="sm" variant="destructive" onClick={() => handleAction(selectedUser.id, "remove-admin", `/admin/users/${selectedUser.id}/remove-admin`)} className="gap-1"><ShieldAlert className="h-4 w-4" /> لغو دسترسی ادمین</Button>
                    )
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => handleAction(selectedUser.id, "make-admin", `/admin/users/${selectedUser.id}/make-admin`)} className="gap-1 text-orange-500 border-orange-500/20 hover:bg-orange-500/10"><ShieldAlert className="h-4 w-4" /> ارتقا به مدیر</Button>
                  )}
                </div>
              )}

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه اشتراک‌ها:</h4>
                <div className="space-y-2">
                  {userDetails.subscriptions.map((s: any) => (
                    <div key={s.id} className="text-xs flex justify-between items-center bg-white/5 p-2 rounded border border-white/5">
                      <span className="font-bold text-gray-200">{getPlanNameFa(s.plan)}</span>
                      <span className="text-gray-400">تا {s.end ? new Date(s.end).toLocaleDateString('fa-IR') : "نامحدود"}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-bold text-sm mb-2 text-[#d6ad60]">تاریخچه پرداخت‌ها:</h4>
                <div className="space-y-2">
                  {userDetails.payments.map((p: any) => (
                    <div key={p.id} className="text-xs flex justify-between items-center bg-white/5 p-2 rounded border border-white/5">
                      <span className="text-gray-200">{getPlanNameFa(p.plan)}</span>
                      <span className={p.status === "approved" ? "text-green-500" : p.status === "pending" ? "text-yellow-500" : "text-red-500"}>{p.status === "approved" ? "تایید شده" : p.status === "pending" ? "در انتظار" : "رد شده"}</span>
                      <span className="text-gray-400">{new Date(p.created_at).toLocaleDateString('fa-IR')}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (<div className="flex justify-center py-10"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#d6ad60]"></div></div>)}
        </DialogContent>
      </Dialog>
    </main>
  );
}