"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { ArrowRight, MessageSquare, Clock, Loader2, AlertCircle, CheckCircle2, Search, Inbox, RefreshCw } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function getError(data: any) {
  return typeof data?.detail === "string" ? data.detail : "دریافت اطلاعات تیکت‌ها ناموفق بود.";
}

export default function AdminTicketsPage() {
  const router = useRouter();
  const token = getToken();
  const [tickets, setTickets] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"open" | "closed">("open");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [ticketsRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/admin/tickets?status=${filter}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }),
        fetch(`${apiUrl}/admin/tickets/stats`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }),
      ]);
      const ticketsData = await ticketsRes.json().catch(() => []);
      const statsData = await statsRes.json().catch(() => ({}));
      if (!ticketsRes.ok) throw new Error(getError(ticketsData));
      if (!statsRes.ok) throw new Error(getError(statsData));
      setTickets(Array.isArray(ticketsData) ? ticketsData : []);
      setStats(statsData);
    } catch (err: any) {
      setError(err?.message || "ارتباط با سرور برقرار نشد.");
    } finally {
      setLoading(false);
    }
  }, [filter, token]);

  useEffect(() => {
    const user = getUser();
    if (!user || !user.is_admin) {
      router.replace("/login");
      return;
    }
    void fetchData();
  }, [fetchData, router]);

  const filteredTickets = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query) return tickets;
    return tickets.filter((ticket) =>
      [ticket.user_phone, ticket.user_name, ticket.subject, ticket.last_message, String(ticket.id)]
        .some((value) => String(value ?? "").toLocaleLowerCase().includes(query))
    );
  }, [tickets, searchQuery]);

  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-[#030811] text-white">
      <Header />
      <main className="container mx-auto max-w-6xl flex-1 space-y-4 p-3 py-5 sm:p-5">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="flex items-center gap-2 font-display text-2xl font-extrabold tracking-tight sm:text-3xl"><MessageSquare className="h-6 w-6 text-[#d6ad60]" /> مدیریت تیکت‌ها</h1>
            <p className="mt-1 text-sm text-gray-400">پاسخ‌گویی و پیگیری درخواست‌های کاربران</p>
          </div>
          <Link href="/admin"><Button variant="outline" className="h-10 gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white">پنل ادمین <ArrowRight className="h-4 w-4" /></Button></Link>
        </div>

        {stats && <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-3 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition-all duration-200 hover:border-[#d6ad60]/25"><div className="mb-1 flex items-center gap-2 text-[11px] text-gray-500"><MessageSquare className="h-3.5 w-3.5" /> کل</div><p className="text-xl font-bold text-gray-100">{stats.total_count ?? 0}</p></div>
          <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-3 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition-all duration-200 hover:border-[#d6ad60]/25"><div className="mb-1 flex items-center gap-2 text-[11px] text-gray-500"><AlertCircle className="h-3.5 w-3.5" /> باز</div><p className="text-xl font-bold text-gray-100">{stats.open_count ?? 0}</p></div>
          <div className="rounded-2xl border border-white/[0.09] bg-[#101923] p-3 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition-all duration-200 hover:border-[#d6ad60]/25"><div className="mb-1 flex items-center gap-2 text-[11px] text-gray-500"><CheckCircle2 className="h-3.5 w-3.5" /> بسته</div><p className="text-xl font-bold text-gray-100">{stats.closed_count ?? 0}</p></div>
          <div className={`rounded-2xl border p-3 shadow-[0_10px_28px_rgba(0,0,0,0.16)] ${stats.unread_count > 0 ? "border-[#d6ad60]/25 bg-[linear-gradient(135deg,rgba(214,173,96,0.12),rgba(8,19,33,0.95))]" : "border-white/10 bg-[#0a1727]"}`}><div className={`mb-2 flex items-center gap-2 text-xs ${stats.unread_count > 0 ? "text-[#d6ad60]/80" : "text-gray-500"}`}><MessageSquare className="h-3.5 w-3.5" /> خوانده‌نشده</div><p className={`text-2xl font-bold ${stats.unread_count > 0 ? "text-[#d6ad60]" : "text-gray-500"}`}>{stats.unread_count ?? 0}</p></div>
        </div>}

        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1"><Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" /><Input placeholder="جستجوی شماره، نام، موضوع یا شناسه..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} className="h-10 rounded-lg border-white/10 bg-[#051118] pr-10 text-sm text-white" /></div>
          <div className="flex gap-1 rounded-lg border border-white/5 bg-[#051118] p-1">
            <Button variant={filter === "open" ? "default" : "ghost"} onClick={() => setFilter("open")} className={`h-8 text-xs ${filter === "open" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:bg-white/5 hover:text-white"}`}>باز</Button>
            <Button variant={filter === "closed" ? "default" : "ghost"} onClick={() => setFilter("closed")} className={`h-8 text-xs ${filter === "closed" ? "bg-[#d6ad60] text-[#101827] hover:bg-[#d6ad60]/90" : "text-gray-400 hover:bg-white/5 hover:text-white"}`}>بسته</Button>
          </div>
        </div>

        {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><span>{error}</span><Button variant="outline" size="sm" onClick={() => void fetchData()} className="gap-2 border-red-500/20"><RefreshCw className="h-3.5 w-3.5" /> تلاش مجدد</Button></div>}

        {loading ? <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div> :
          filteredTickets.length === 0 ? <div className="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,#112238,#071321)] p-12 text-center shadow-[0_16px_45px_rgba(0,0,0,0.2)] sm:p-16"><Inbox className="mx-auto mb-3 h-12 w-12 text-gray-600" /><p className="text-gray-400">{searchQuery ? "نتیجه‌ای برای جستجوی شما پیدا نشد." : "در این بخش تیکتی وجود ندارد."}</p></div> :
          <div className="space-y-1.5">{filteredTickets.map((ticket, index) => <motion.div key={ticket.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.02, 0.15) }}>
            <Link href={`/admin/tickets/${ticket.id}`} className="group flex items-center justify-between gap-4 rounded-2xl border border-white/[0.09] bg-[#101923] p-3 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[#d6ad60]/30 hover:from-[#14243a] hover:to-[#091522]">
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 flex flex-wrap items-center gap-2"><span className="font-mono text-[10px] text-gray-500">#{ticket.id}</span><span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-gray-300">{ticket.user_phone}</span>{ticket.user_name && <span className="text-[10px] font-bold text-gray-300">{ticket.user_name}</span>}{ticket.unread_count > 0 && <span className="rounded bg-[#d6ad60]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#d6ad60]">{ticket.unread_count} جدید</span>}</div>
                <h3 className="truncate text-sm font-bold text-gray-100">{ticket.subject}</h3><p className="mt-1 truncate text-xs text-gray-400">{ticket.last_message || "بدون پیام"}</p>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-gray-500"><span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {ticket.updated_at ? new Date(ticket.updated_at).toLocaleString("fa-IR") : "—"}</span><span className="flex items-center gap-1"><MessageSquare className="h-3 w-3" /> {ticket.messages_count ?? 0} پیام</span></div>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-gray-600 transition-all group-hover:-translate-x-1 group-hover:text-[#d6ad60]" />
            </Link>
          </motion.div>)}</div>}
      </main>
      <Footer />
    </div>
  );
}
