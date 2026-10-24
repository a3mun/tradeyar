"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { LogOut, CheckCircle2, XCircle, CreditCard, Users, Calendar, Clock, Globe, Monitor, UserCheck } from "lucide-react";

const getPlanNameFa = (plan: string) => {
  const map: Record<string, string> = {
    "1_month": "یک ماهه",
    "3_months": "سه ماهه",
    "6_months": "شش ماهه",
    "12_months": "یک ساله",
    "free": "رایگان",
  };
  return map[plan] || plan;
};

export default function AdminPage() {
  const router = useRouter();
  const [user, setUserData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"payments" | "users">("payments");
  const [payments, setPayments] = useState<any[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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
    } catch (err) {
      console.error("خطا در دریافت اطلاعات", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (id: number, action: "approve" | "reject") => {
    if (!confirm(`آیا از ${action === "approve" ? "تایید" : "رد"} این پرداخت مطمئنید؟`)) return;
    try {
      const res = await fetch(`${apiUrl}/admin/payments/${id}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      alert(data.message || "عملیات با موفقیت انجام شد");
      fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleLogout = () => { removeToken(); router.replace("/login"); };

  if (!user) return null;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8">
        <div className="max-w-5xl mx-auto space-y-6">
          
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-primary">پنل مدیریت</h1>
            <Button variant="destructive" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 ml-2" /> خروج
            </Button>
          </div>

          {/* تب‌ها */}
          <div className="flex gap-2 border-b pb-2">
            <Button 
              variant={activeTab === "payments" ? "default" : "ghost"} 
              onClick={() => setActiveTab("payments")}
              className="gap-2"
            >
              <CreditCard className="h-4 w-4" /> درخواست‌های پرداخت
            </Button>
            <Button 
              variant={activeTab === "users" ? "default" : "ghost"} 
              onClick={() => setActiveTab("users")}
              className="gap-2"
            >
              <Users className="h-4 w-4" /> مدیریت کاربران
            </Button>
          </div>

          {/* محتوای تب‌ها */}
          {activeTab === "payments" ? (
            <div className="space-y-4">
              {loading ? (
                <p className="text-center text-muted-foreground py-4">در حال دریافت اطلاعات...</p>
              ) : payments.length === 0 ? (
                <div className="text-center text-muted-foreground py-6 bg-muted/20 rounded-lg">هیچ درخواستی وجود ندارد.</div>
              ) : (
                payments.map((p) => (
                  <div key={p.id} className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-xl border bg-card shadow-sm hover:shadow-md transition-shadow">
                    <div className="w-full space-y-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono dir-ltr text-base font-bold bg-muted px-2 py-1 rounded">{p.user_phone}</span>
                        <span className="text-xs bg-primary/10 text-primary px-3 py-1 rounded-full font-bold">{getPlanNameFa(p.plan)}</span>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {new Date(p.created_at).toLocaleString('fa-IR')}
                        </span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground bg-muted/20 p-3 rounded-lg">
                        <div className="flex items-center gap-2"><Calendar className="h-4 w-4 text-blue-500" /><span>عضویت: {p.user_joined_at ? new Date(p.user_joined_at).toLocaleDateString('fa-IR') : "نامشخص"}</span></div>
                        <div className="flex items-center gap-2"><UserCheck className="h-4 w-4 text-green-500" /><span>آخرین ورود: {p.user_last_login ? new Date(p.user_last_login).toLocaleString('fa-IR') : "نامشخص"}</span></div>
                        <div className="flex items-center gap-2"><Globe className="h-4 w-4 text-orange-500" /><span className="dir-ltr font-mono">{p.ip_address}</span></div>
                        <div className="flex items-center gap-2 truncate"><Monitor className="h-4 w-4 text-purple-500" /><span className="truncate" title={p.user_agent}>{p.user_agent}</span></div>
                        
                        {/* نمایش نام و زمان واریز */}
                        <div className="flex items-center gap-2"><UserCheck className="h-4 w-4 text-blue-500" /><span>نام: {p.full_name}</span></div>
                        <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-yellow-500" /><span>زمان واریز: {p.payment_time}</span></div>
                      </div>
                      {p.receipt_note && (
                        <div className="text-xs bg-yellow-500/10 text-yellow-600 p-2 rounded-lg border border-yellow-500/20">
                          <strong>توضیحات کاربر:</strong> {p.receipt_note}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2 w-full md:w-auto shrink-0 pt-2 md:pt-0 border-t md:border-t-0 md:border-r md:pr-4">
                      <Button size="sm" className="flex-1 md:flex-none bg-green-600 hover:bg-green-700 text-white gap-1" onClick={() => handleAction(p.id, "approve")}>
                        <CheckCircle2 className="h-4 w-4" /> تایید
                      </Button>
                      <Button size="sm" variant="destructive" className="flex-1 md:flex-none gap-1" onClick={() => handleAction(p.id, "reject")}>
                        <XCircle className="h-4 w-4" /> رد
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {loading ? (
                <p className="text-center text-muted-foreground py-4">در حال دریافت اطلاعات...</p>
              ) : usersList.length === 0 ? (
                <div className="text-center text-muted-foreground py-6 bg-muted/20 rounded-lg">هیچ کاربری یافت نشد.</div>
              ) : (
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full text-sm text-right">
                    <thead className="bg-muted/50 text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3 font-medium">شماره موبایل</th>
                        <th className="px-4 py-3 font-medium">نام</th>
                        <th className="px-4 py-3 font-medium">نوع پلن</th>
                        <th className="px-4 py-3 font-medium">تاریخ عضویت</th>
                        <th className="px-4 py-3 font-medium">نقش</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {usersList.map((u) => (
                        <tr key={u.id} className="hover:bg-muted/30">
                          <td className="px-4 py-3 font-mono dir-ltr">{u.phone}</td>
                          <td className="px-4 py-3">{u.full_name}</td>
                          <td className="px-4 py-3">
                            <span className="bg-primary/10 text-primary px-2 py-1 rounded text-xs font-bold">{getPlanNameFa(u.plan)}</span>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(u.created_at).toLocaleDateString('fa-IR')}</td>
                          <td className="px-4 py-3">
                            {u.is_admin ? (
                              <span className="text-green-500 text-xs font-bold">مدیر</span>
                            ) : (
                              <span className="text-muted-foreground text-xs">کاربر</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>
      </main>
      <Footer />
    </div>
  );
}