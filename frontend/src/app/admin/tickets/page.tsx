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
import { ArrowRight, MessageSquare, Clock, Loader2, AlertCircle, CheckCircle2, Search, Inbox } from "lucide-react";

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

  const filteredTickets = tickets.filter(t => 
    (t.user_phone && t.user_phone.includes(searchQuery)) || 
    (t.user_name && t.user_name.includes(searchQuery)) || 
    (t.subject && t.subject.includes(searchQuery))
  );

  return (
    <div className="flex min-h-screen flex-col bg-[#030712] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-5xl space-y-5">
        
        {/* ═══ هدر ═══ */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2 font-display">
              <MessageSquare className="h-6 w-6 text-[#d6ad60]" /> مدیریت تیکت‌ها
            </h1>
            <p className="text-sm text-gray-400 mt-1">پاسخ به تیکت‌های کاربران</p>
          </div>
          <Link href="/admin">
            <Button variant="outline" className="gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white h-10">
              پنل ادمین <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* ═══ کارت‌های آمار ═══ */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-white/5 bg-[#051118] p-4">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2"><MessageSquare className="h-3.5 w-3.5" /> کل</div>
              <p className="text-2xl font-bold text-gray-100">{stats.total_count}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#051118] p-4">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2"><AlertCircle className="h-3.5 w-3.5" /> باز</div>
              <p className="text-2xl font-bold text-gray-100">{stats.open_count}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#051118] p-4">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2"><CheckCircle2 className="h-3.5 w-3.5" /> بسته</div>
              <p className="text-2xl font-bold text-gray-100">{stats.closed_count}</p>
            </div>
            <div className={`rounded-xl border p-4 ${stats.unread_count > 0 ? "border-[#d6ad60]/20 bg-[#d6ad60]/5" : "border-white/5 bg-[#051118]"}`}>
              <div className={`flex items-center gap-2 text-xs mb-2 ${stats.unread_count > 0 ? "text-[#d6ad60]/80" : "text-gray-500"}`}><MessageSquare className="h-3.5 w-3.5" /> خوانده‌نشده</div>
              <p className={`text-2xl font-bold ${stats.unread_count > 0 ? "text-[#d6ad60]" : "text-gray-500"}`}>{stats.unread_count}</p>
            </div>
          </div>
        )}

        {/* ═══ جستجو و فیلتر ═══ */}
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <Input 
              placeholder="جستجوی شماره، نام یا موضوع..." 
              value={searchQuery} 
              onChange={(e) => setSearchQuery(e.target.value)} 
              className="pr-10 bg-[#051118] border-white/10 text-white h-10 rounded-lg text-sm" 
            />
          </div>
          <div className="flex gap-1 bg-[#051118] p-1 rounded-lg border border-white/5">
            <Button 
              variant={filter === "open" ? "default" : "ghost"} 
              onClick={() => setFilter("open")} 
              className={`h-8 text-xs ${filter === "open" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
            >
              باز
            </Button>
            <Button 
              variant={filter === "closed" ? "default" : "ghost"} 
              onClick={() => setFilter("closed")} 
              className={`h-8 text-xs ${filter === "closed" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
            >
              بسته
            </Button>
          </div>
        </div>

        {/* ═══ لیست تیکت‌ها ═══ */}
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div>
        ) : filteredTickets.length === 0 ? (
          <div className="rounded-xl border border-white/5 bg-[#051118] p-16 text-center">
            <Inbox className="h-12 w-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">تیکتی با این مشخصات یافت نشد.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTickets.map((t, idx) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.03 }}>
                <Link href={`/admin/tickets/${t.id}`}>
                  <div className="group flex items-center justify-between gap-4 rounded-xl border border-white/5 bg-[#051118] p-4 transition-all hover:border-[#d6ad60]/30 hover:bg-[#0a1526]">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className="text-[10px] text-gray-500 font-mono">#{t.id}</span>
                        <span className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded font-mono text-gray-300">{t.user_phone}</span>
                        {t.user_name && <span className="text-[10px] text-gray-300 font-bold">{t.user_name}</span>}
                        {t.unread_count > 0 && (
                          <span className="rounded bg-[#d6ad60]/15 text-[#d6ad60] text-[9px] font-bold px-1.5 py-0.5">{t.unread_count} جدید</span>
                        )}
                      </div>
                      <h3 className="font-bold text-sm text-gray-100 truncate">{t.subject}</h3>
                      <p className="text-xs text-gray-400 truncate mt-1">{t.last_message}</p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(t.updated_at).toLocaleString("fa-IR")}</span>
                        <span className="flex items-center gap-1"><MessageSquare className="h-3 w-3" /> {t.messages_count} پیام</span>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-gray-600 group-hover:text-[#d6ad60] transition-all group-hover:-translate-x-1" />
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