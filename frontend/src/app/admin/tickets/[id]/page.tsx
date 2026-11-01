"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { ArrowRight, Send, Clock, ShieldCheck, User, Loader2, Lock, Paperclip, X, Trash2 } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function AdminTicketDetailPage() {
  const router = useRouter();
  const params = useParams();
  const ticketId = params?.id;
  const token = getToken();
  const [ticket, setTicket] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [closing, setClosing] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTicket = async () => {
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setTicket(data);
    } catch {
      router.replace("/admin/tickets");
    }
    setLoading(false);
  };

  useEffect(() => {
    const u = getUser();
    if (!u || !u.is_admin) { router.replace("/login"); return; }
    fetchTicket();
  }, [ticketId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [ticket?.messages?.length]);

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

  const handleSend = async () => {
    if (!reply.trim() && !selectedFile) return;
    setSending(true);
    try {
      // ۱. آپلود فایل
      let attachmentPath = null;
      let attachmentName = null;
      if (selectedFile) {
        setUploading(true);
        const formData = new FormData();
        formData.append("file", selectedFile);
        const upRes = await fetch(`${apiUrl}/admin/tickets/${ticketId}/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
        const upData = await upRes.json();
        if (!upRes.ok) throw new Error(upData.detail);
        attachmentPath = upData.path;
        attachmentName = upData.name;
        setUploading(false);
      }

      // ۲. ارسال پیام
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          message: reply.trim() || "(تصویر پیوست)",
          attachment_path: attachmentPath,
          attachment_name: attachmentName,
        }),
      });
      if (res.ok) {
        setReply("");
        handleClearFile();
        await fetchTicket();
      }
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSending(false);
      setUploading(false);
    }
  };

  const handleClose = async () => {
    if (!confirm("این تیکت بسته شود؟ (دیگر امکان پاسخ نیست)")) return;
    setClosing(true);
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}/close`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) await fetchTicket();
    } finally {
      setClosing(false);
    }
  };

    const handleDelete = async () => {
    if (!confirm("آیا مطمئنید؟ این تیکت و تمام پیام‌های آن برای همیشه حذف خواهد شد.")) return;
    setClosing(true);
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) router.replace("/admin/tickets");
      else alert("خطا در حذف تیکت");
    } finally { setClosing(false); }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f]">
        <Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" />
      </div>
    );
  }

  if (!ticket) return null;

  return (
    <div className="flex min-h-screen flex-col bg-[#07111f] text-white">
      <Header />
      <main className="flex-1 container mx-auto p-4 py-8 max-w-3xl">
        <div className="mb-4 flex items-center justify-between">
          <Link href="/admin/tickets">
            <Button variant="ghost" size="sm" className="gap-2 text-gray-400 hover:text-white">
              <ArrowRight className="h-4 w-4" /> بازگشت
            </Button>
          </Link>
          <div className="flex gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-bold ${ticket.status === "open" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
              {ticket.status === "open" ? "فعال" : "بسته"}
            </span>
            {ticket.status === "open" && (
              <Button size="sm" variant="destructive" onClick={handleClose} disabled={closing} className="gap-1 h-7 text-xs">
                {closing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Lock className="h-3 w-3" />} بستن تیکت
              </Button>

              
            )}

               <Button size="sm" variant="destructive" onClick={handleDelete} disabled={closing} className="gap-1 h-7 text-xs bg-red-600 hover:bg-red-700">
                   {closing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />} حذف کامل
               </Button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-5 mb-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500 font-mono">#{ticket.id}</span>
            <span className="text-xs bg-white/10 px-2 py-0.5 rounded font-mono">{ticket.user_phone}</span>
            <span className="text-[10px] text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" /> {new Date(ticket.created_at).toLocaleString("fa-IR")}
            </span>
          </div>
          <h1 className="text-xl font-bold text-white">{ticket.subject}</h1>
        </div>

        <div className="space-y-3 mb-4">
          {ticket.messages.map((m: any, idx: number) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`flex ${m.is_admin ? "justify-end" : "justify-start"}`}
            >
              <div className={`max-w-[80%] rounded-2xl p-3 ${m.is_admin ? "bg-[#d6ad60]/10 border border-[#d6ad60]/30" : "bg-white/5 border border-white/10"}`}>
                <div className="flex items-center gap-2 mb-1">
                  {m.is_admin ? <ShieldCheck className="h-3 w-3 text-[#d6ad60]" /> : <User className="h-3 w-3 text-gray-400" />}
                  <span className="text-[10px] font-bold text-gray-400">{m.is_admin ? "پشتیبانی" : ticket.user_phone}</span>
                  <span className="text-[9px] text-gray-600">{new Date(m.created_at).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <p className="text-sm text-white whitespace-pre-wrap">{m.message}</p>
                {m.attachment_path && (
                  <a href={`${apiUrl}${m.attachment_path}`} target="_blank" rel="noreferrer" className="block mt-2">
                    <img src={`${apiUrl}${m.attachment_path}`} alt={m.attachment_name || "attachment"} className="max-w-full max-h-64 rounded-lg border border-white/10" />
                  </a>
                )}
              </div>
            </motion.div>
          ))}
          <div ref={bottomRef} />
        </div>

        {ticket.status === "open" ? (
          <div className="space-y-2">
            {previewUrl && (
              <div className="relative inline-block">
                <img src={previewUrl} alt="preview" className="max-h-32 rounded-lg border border-white/20" />
                <button onClick={handleClearFile} className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1 hover:bg-red-600">
                  <X className="h-3 w-3 text-white" />
                </button>
              </div>
            )}
            <div className="flex gap-2">
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" onChange={handleSelectFile} className="hidden" />
              <Button type="button" variant="outline" size="icon" onClick={() => fileInputRef.current?.click()} className="h-11 border-white/10">
                <Paperclip className="h-4 w-4" />
              </Button>
              <Input
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="پاسخ خود را بنویسید..."
                className="bg-black/30 border-white/10 text-white h-11"
              />
              <Button onClick={handleSend} disabled={sending || uploading || (!reply.trim() && !selectedFile)} className="h-11 gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold hover:opacity-90">
                {sending || uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-gray-500/20 bg-gray-500/5 p-3 text-center text-xs text-gray-400">
            این تیکت بسته شده است.
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}