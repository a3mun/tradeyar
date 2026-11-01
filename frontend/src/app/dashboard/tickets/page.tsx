"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { motion } from "framer-motion";
import { MessageSquare, Plus, ArrowRight, Clock, Loader2, Home, AlertCircle, CheckCircle2, Paperclip, X } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function TicketsPage() {
  const router = useRouter();
  const token = getToken();
  const [tickets, setTickets] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [ticketsRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/tickets`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${apiUrl}/tickets/stats`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (ticketsRes.ok) setTickets(await ticketsRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    if (!getUser()) { router.replace("/login"); return; }
    fetchData();
  }, [router]);

  const handleSelectFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // چک کردن فرمت
    if (!file.type.match('image/jpeg') && !file.type.match('image/png')) {
      alert("فقط فایل‌های JPG و PNG مجاز هستند");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > 1 * 1024 * 1024) {
      alert("حجم فایل حداکثر ۱ مگابایت است");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCreate = async () => {
    if (subject.length < 3) return setError("موضوع باید حداقل ۳ حرف باشد");
    if (message.length < 5 && !selectedFile) return setError("متن پیام یا عکس الزامی است");
    setSending(true);
    setError("");
    try {
      // ۱. ساخت تیکت
      const res = await fetch(`${apiUrl}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject, message: message || "(تصویر پیوست)" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "خطا");

      // ۲. آپلود عکس (اگر وجود دارد)
      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        await fetch(`${apiUrl}/tickets/${data.id}/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
      }

      setIsOpen(false);
      setSubject("");
      setMessage("");
      handleClearFile();
      router.push(`/dashboard/tickets/${data.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const openTickets = tickets.filter((t) => t.status === "open");
  const atLimit = openTickets.length >= 1; // ⬅️ محدودیت ۱ تیکت باز

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-4xl space-y-6">
        {/* هدر */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <MessageSquare className="h-6 w-6 text-[#d6ad60]" /> تیکت‌های پشتیبانی
            </h1>
            <p className="text-sm text-gray-400 mt-1">سوال یا مشکلی داری؟ با ما در تماس باش.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="gap-2 border-white/10 text-gray-300 hover:bg-white/5 hover:text-white">
                <Home className="h-4 w-4" /> داشبورد
              </Button>
            </Link>
            <Button
              onClick={() => setIsOpen(true)}
              disabled={atLimit}
              className="h-10 gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold hover:opacity-90 disabled:opacity-40"
            >
              <Plus className="h-4 w-4" /> تیکت جدید
            </Button>
          </div>
        </div>

        {/* کارت آمار */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                <MessageSquare className="h-3 w-3" /> کل تیکت‌ها
              </div>
              <p className="text-2xl font-bold text-white">{stats.total_count}</p>
            </div>
            <div className="rounded-2xl border border-green-500/20 bg-green-500/5 backdrop-blur-xl p-4">
              <div className="flex items-center gap-2 text-xs text-green-400 mb-1">
                <AlertCircle className="h-3 w-3" /> باز
              </div>
              <p className="text-2xl font-bold text-green-400">{stats.open_count}</p>
            </div>
            <div className="rounded-2xl border border-gray-500/20 bg-gray-500/5 backdrop-blur-xl p-4">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                <CheckCircle2 className="h-3 w-3" /> بسته
              </div>
              <p className="text-2xl font-bold text-gray-300">{stats.closed_count}</p>
            </div>
            <div className={`rounded-2xl border backdrop-blur-xl p-4 ${stats.unread_count > 0 ? "border-[#d6ad60]/40 bg-[#d6ad60]/10" : "border-white/10 bg-white/5"}`}>
              <div className="flex items-center gap-2 text-xs text-[#d6ad60] mb-1">
                <MessageSquare className="h-3 w-3" /> خوانده‌نشده
              </div>
              <p className={`text-2xl font-bold ${stats.unread_count > 0 ? "text-[#d6ad60]" : "text-gray-500"}`}>
                {stats.unread_count}
              </p>
            </div>
          </div>
        )}

        {/* هشدار محدودیت */}
        {atLimit && (
          <div className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-xs text-yellow-400">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>شما یک تیکت باز دارید. لطفاً تا پاسخ و بسته شدن آن صبر کنید.</span>
          </div>
        )}

        {/* مودال تیکت جدید */}
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="bg-[#0d1b2d] border-white/10 text-white">
            <DialogHeader><DialogTitle className="text-[#d6ad60]">تیکت جدید</DialogTitle></DialogHeader>
            <div className="space-y-4 py-4">
              {error && <div className="rounded-lg bg-red-500/10 p-3 text-xs text-red-400">{error}</div>}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">موضوع</label>
                <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="مثلاً: مشکل در پرداخت" className="bg-black/30 border-white/10" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">پیام</label>
                <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={4} placeholder="توضیحات کامل..." className="w-full rounded-lg border border-white/10 bg-black/30 p-3 text-sm text-white" />
              </div>
              
              {/* آپلود عکس در مودال */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">عکس (اختیاری، حداکثر ۱ مگابایت)</label>
                {previewUrl ? (
                  <div className="relative inline-block">
                    <img src={previewUrl} alt="preview" className="max-h-32 rounded-lg border border-white/20" />
                    <button onClick={handleClearFile} className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1 hover:bg-red-600">
                      <X className="h-3 w-3 text-white" />
                    </button>
                  </div>
                ) : (
                  <>
                    <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" onChange={handleSelectFile} className="hidden" />
                    <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} className="w-full gap-2 border-white/10 text-gray-300 hover:bg-white/5">
                      <Paperclip className="h-4 w-4" /> انتخاب عکس
                    </Button>
                  </>
                )}
              </div>

              <Button onClick={handleCreate} disabled={sending} className="w-full h-10 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold hover:opacity-90">
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : "ارسال تیکت"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* لیست تیکت‌ها */}
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div>
        ) : tickets.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-16 text-center">
            <MessageSquare className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">هنوز تیکتی ارسال نکردی.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tickets.map((t) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <Link href={`/dashboard/tickets/${t.id}`}>
                  <div className="group flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 transition-all hover:border-[#d6ad60]/40 hover:bg-white/10">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-500 font-mono">#{t.id}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${t.status === "open" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
                          {t.status === "open" ? "فعال" : "بسته"}
                        </span>
                        {t.unread_count > 0 && (
                          <span className="rounded-full bg-[#d6ad60] text-[#101827] text-[10px] font-bold px-2 py-0.5">
                            {t.unread_count} جدید
                          </span>
                        )}
                      </div>
                      <h3 className="font-bold text-white truncate">{t.subject}</h3>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{t.last_message}</p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(t.updated_at).toLocaleString("fa-IR")}</span>
                        <span className="flex items-center gap-1"><MessageSquare className="h-3 w-3" /> {t.messages_count} پیام</span>
                      </div>
                    </div>
                    <ArrowRight className="h-5 w-5 text-gray-600 group-hover:text-[#d6ad60] transition-colors" />
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