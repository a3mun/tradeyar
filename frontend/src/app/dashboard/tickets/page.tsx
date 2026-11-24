"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { motion } from "framer-motion";
import { MessageSquare, Plus, ArrowRight, Clock, Loader2, Home, AlertCircle, Inbox, RefreshCw } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function errorMessage(data: any, fallback: string) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item: any) => item.msg).filter(Boolean).join("، ") || fallback;
  return fallback;
}

export default function TicketsPage() {
  const router = useRouter();
  const token = getToken();
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setPageError("");
    try {
      const ticketsRes = await fetch(`${apiUrl}/tickets`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      const ticketsData = await ticketsRes.json().catch(() => []);
      if (!ticketsRes.ok) throw new Error(errorMessage(ticketsData, "دریافت تیکت‌ها ناموفق بود"));
      setTickets(Array.isArray(ticketsData) ? ticketsData : []);
    } catch (err: any) {
      setPageError(err?.message || "ارتباط با سرور برقرار نشد.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!getUser()) {
      router.replace("/login");
      return;
    }
    void fetchData();
  }, [fetchData, router]);

  const openTickets = tickets.filter((ticket) => ticket.status === "open");
  const atLimit = openTickets.length >= 1;

  const handleDialogChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) setError("");
  };

  const handleCreate = async () => {
    const cleanSubject = subject.trim();
    const cleanMessage = message.trim();
    if (sending) return;
    if (cleanSubject.length < 3) return setError("موضوع باید حداقل ۳ حرف باشد");
    if (cleanSubject.length > 200) return setError("موضوع نمی‌تواند بیشتر از ۲۰۰ حرف باشد");
    if (cleanMessage.length < 5) return setError("متن پیام باید حداقل ۵ حرف باشد");
    if (cleanMessage.length > 2000) return setError("متن پیام نمی‌تواند بیشتر از ۲۰۰۰ حرف باشد");
    setSending(true);
    setError("");
    try {
      const res = await fetch(`${apiUrl}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject: cleanSubject, message: cleanMessage }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errorMessage(data, "ایجاد تیکت ناموفق بود"));
      setIsOpen(false);
      setSubject("");
      setMessage("");
      router.push(`/dashboard/tickets/${data.id}`);
    } catch (err: any) {
      setError(err?.message || "ارسال تیکت انجام نشد");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-[#030811] text-white">
      <Header />
      <main className="container mx-auto max-w-5xl flex-1 space-y-4 p-3 py-5 sm:p-5">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div><h1 className="flex items-center gap-2 font-display text-2xl font-extrabold tracking-tight sm:text-3xl text-white"><MessageSquare className="h-6 w-6 text-[#d6ad60]" /> تیکت‌های پشتیبانی</h1><p className="mt-1 text-sm text-gray-400">سوال یا مشکلی داری؟ با ما در تماس باش.</p></div>
          <div className="flex gap-2">
            <Link href="/dashboard"><Button variant="outline" size="sm" className="h-10 gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white"><Home className="h-4 w-4" /> داشبورد</Button></Link>
            <Button onClick={() => { setError(""); setIsOpen(true); }} disabled={atLimit} className="h-10 gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] font-bold text-[#101827] hover:opacity-90 disabled:opacity-40"><Plus className="h-4 w-4" /> تیکت جدید</Button>
          </div>
        </div>





        {atLimit && <p className="-mt-2 text-[11px] text-gray-500">یک درخواست در حال پیگیری دارید؛ پس از بسته شدن آن می‌توانید تیکت جدید ثبت کنید.</p>}

        <Dialog open={isOpen} onOpenChange={handleDialogChange}>
          <DialogContent className="border-white/10 bg-[#051118] text-white sm:max-w-md">
            <DialogHeader><DialogTitle className="text-[#d6ad60]">تیکت جدید</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              {error && <div role="alert" className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">{error}</div>}
              <div><label htmlFor="ticket-subject" className="mb-1 block text-xs text-gray-400">موضوع</label><Input id="ticket-subject" value={subject} maxLength={200} onChange={(event) => { setSubject(event.target.value); setError(""); }} placeholder="مثلاً: مشکل در پرداخت" className="h-10 border-white/10 bg-black/30 text-sm" /></div>
              <div><label htmlFor="ticket-message" className="mb-1 block text-xs text-gray-400">پیام</label><textarea id="ticket-message" value={message} onChange={(event) => { setMessage(event.target.value); setError(""); }} maxLength={2000} rows={4} placeholder="توضیحات کامل..." className="w-full rounded-lg border border-white/10 bg-black/30 p-3 text-sm text-white outline-none focus:border-[#d6ad60]/50" /><p className="mt-1 text-left text-[10px] text-gray-500">{message.length}/۲۰۰۰</p></div>
              <div className="flex items-start gap-2 rounded-lg border border-white/5 bg-white/5 p-3"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-gray-500" /><p className="text-[10px] leading-relaxed text-gray-400">بعد از ایجاد تیکت، در صفحه چت می‌توانید عکس یا اسکرین‌شات را به پیام‌های خود پیوست کنید.</p></div>
              <Button onClick={() => void handleCreate()} disabled={sending} className="h-10 w-full bg-gradient-to-l from-[#c89a49] to-[#e2c17e] font-bold text-[#101827] hover:opacity-90">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : "ارسال تیکت"}</Button>
            </div>
          </DialogContent>
        </Dialog>

        {pageError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><span>{pageError}</span><Button variant="outline" size="sm" onClick={() => void fetchData()} className="gap-2 border-red-500/20"><RefreshCw className="h-3.5 w-3.5" /> تلاش مجدد</Button></div>}

        {loading ? <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div> :
          tickets.length === 0 ? <div className="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,#112238,#071321)] p-12 text-center shadow-[0_16px_45px_rgba(0,0,0,0.2)] sm:p-16"><Inbox className="mx-auto mb-3 h-12 w-12 text-gray-600" /><p className="text-gray-400">هنوز تیکتی ارسال نکردی.</p></div> :
          <div className="space-y-1.5">{tickets.map((ticket) => <motion.div key={ticket.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link href={`/dashboard/tickets/${ticket.id}`} className="group flex items-center justify-between gap-4 rounded-2xl border border-white/[0.09] bg-[#101923] p-3 shadow-[0_10px_28px_rgba(0,0,0,0.18)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[#d6ad60]/30 hover:from-[#14243a] hover:to-[#091522]">
              <div className="min-w-0 flex-1"><div className="mb-1.5 flex flex-wrap items-center gap-2"><span className="font-mono text-[10px] text-gray-600">#{ticket.id}</span><span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold ${ticket.status === "open" ? "border-green-500/20 bg-green-500/5 text-green-500/90" : "border-white/10 bg-white/5 text-gray-500"}`}>{ticket.status === "open" ? "فعال" : "بسته"}</span></div><h3 className="truncate text-sm font-bold text-gray-100">{ticket.subject}</h3><p className="mt-1 truncate text-xs text-gray-400">{ticket.last_message || "بدون پیام"}</p><div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-gray-500"><span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {ticket.updated_at ? new Date(ticket.updated_at).toLocaleString("fa-IR") : "—"}</span></div></div>
              <ArrowRight className="h-4 w-4 shrink-0 text-gray-600 transition-all group-hover:-translate-x-1 group-hover:text-[#d6ad60]" />
            </Link>
          </motion.div>)}</div>}
      </main>
    </div>
  );
}
