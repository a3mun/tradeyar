"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { ArrowRight, MessageSquare, Clock, Loader2, AlertCircle, CheckCircle2, Search } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function AdminTicketsPage() {
  const router = useRouter();
  const token = getToken();
  const [tickets, setTickets] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"open" | "closed">("open");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [ticketsRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/admin/tickets?status=${filter}`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${apiUrl}/admin/tickets/stats`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (ticketsRes.ok) setTickets(await ticketsRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    const u = getUser();
    if (!u || !u.is_admin) { router.replace("/login"); return; }
    fetchData();
  }, [filter, router]);

  // ⬅️ فیلتر بر اساس جستجو (شماره، نام یا موضوع)
  const filteredTickets = tickets.filter(t => 
    (t.user_phone && t.user_phone.includes(searchQuery)) || 
    (t.user_name && t.user_name.includes(searchQuery)) || 
    (t.subject && t.subject.includes(searchQuery))
  );

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-4xl space-y-4">
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <MessageSquare className="h-6 w-6 text-[#d6ad60]" /> مدیریت تیکت‌ها
            </h1>
            <p className="text-sm text-gray-400 mt-1">پاسخ به تیکت‌های کاربران</p>
          </div>
          <Link href="/admin">
            <Button variant="outline" size="sm" className="gap-2 border-white/10">
              پنل ادمین <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* کارت‌های آمار */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-4">
              <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full bg-[#d6ad60]/10 blur-xl" />
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-2"><MessageSquare className="h-3 w-3" /> کل</div>
              <p className="text-2xl font-bold text-white">{stats.total_count}</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="relative overflow-hidden rounded-2xl border border-green-500/30 bg-gradient-to-br from-green-500/20 to-green-500/5 backdrop-blur-xl p-4">
              <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full bg-green-500/20 blur-xl" />
              <div className="flex items-center gap-2 text-xs text-green-400 mb-2"><AlertCircle className="h-3 w-3" /> باز</div>
              <p className="text-2xl font-bold text-green-400">{stats.open_count}</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="relative overflow-hidden rounded-2xl border border-gray-500/30 bg-gradient-to-br from-gray-500/20 to-gray-500/5 backdrop-blur-xl p-4">
              <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full bg-gray-500/20 blur-xl" />
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-2"><CheckCircle2 className="h-3 w-3" /> بسته</div>
              <p className="text-2xl font-bold text-gray-300">{stats.closed_count}</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className={`relative overflow-hidden rounded-2xl border backdrop-blur-xl p-4 ${stats.unread_count > 0 ? "border-[#d6ad60]/40 bg-gradient-to-br from-[#d6ad60]/20 to-[#d6ad60]/5" : "border-white/10 bg-gradient-to-br from-white/10 to-white/5"}`}>
              <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full bg-[#d6ad60]/20 blur-xl" />
              <div className="flex items-center gap-2 text-xs text-[#d6ad60] mb-2"><MessageSquare className="h-3 w-3" /> خوانده‌نشده</div>
              <p className={`text-2xl font-bold ${stats.unread_count > 0 ? "text-[#d6ad60]" : "text-gray-500"}`}>{stats.unread_count}</p>
            </motion.div>
          </div>
        )}

        {/* جستجو و فیلتر */}
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <Input 
              placeholder="جستجوی شماره، نام یا موضوع..." 
              value={searchQuery} 
              onChange={(e) => setSearchQuery(e.target.value)} 
              className="pr-10 bg-white/5 border-white/10 text-white h-11 rounded-xl" 
            />
          </div>
          <div className="flex gap-2">
            <Button variant={filter === "open" ? "default" : "outline"} onClick={() => setFilter("open")} className={filter === "open" ? "bg-[#d6ad60] text-[#101827]" : ""}>باز</Button>
            <Button variant={filter === "closed" ? "default" : "outline"} onClick={() => setFilter("closed")} className={filter === "closed" ? "bg-[#d6ad60] text-[#101827]" : ""}>بسته</Button>
          </div>
        </div>

        {/* لیست تیکت‌ها (مدرن) */}
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div>
        ) : filteredTickets.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-16 text-center text-gray-400">تیکتی با این مشخصات یافت نشد.</div>
        ) : (
          <div className="space-y-3">
            {filteredTickets.map((t, idx) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}>
                <Link href={`/admin/tickets/${t.id}`}>
                  <div className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-5 hover:border-[#d6ad60]/40 transition-all">
                    
                    {t.unread_count > 0 && (
                      <div className="absolute top-0 right-0 w-24 h-24 bg-[#d6ad60]/10 rounded-bl-full blur-xl" />
                    )}
                    
                    <div className="flex items-center justify-between gap-4 relative z-10">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                          <span className="text-xs text-gray-500 font-mono">#{t.id}</span>
                          <span className="text-xs bg-white/10 px-2 py-0.5 rounded font-mono text-white">{t.user_phone}</span>
                          {/* ⬅️ نمایش نام کاربر (اگر ثبت شده باشد) */}
                          {t.user_name && (
                            <span className="text-xs text-gray-300 font-bold">{t.user_name}</span>
                          )}
                          {t.unread_count > 0 && (
                            <span className="rounded-full bg-[#d6ad60] text-[#101827] text-[10px] font-bold px-2 py-0.5">{t.unread_count} جدید</span>
                          )}
                        </div>
                        <h3 className="font-bold text-white truncate">{t.subject}</h3>
                        <p className="text-xs text-gray-400 truncate mt-1">{t.last_message}</p>
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
                          <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(t.updated_at).toLocaleString("fa-IR")}</span>
                          <span>{t.messages_count} پیام</span>
                        </div>
                      </div>
                      <ArrowRight className="h-5 w-5 text-gray-600 group-hover:text-[#d6ad60] transition-colors" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}