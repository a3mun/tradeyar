"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import imageCompression from "browser-image-compression";
import { ArrowRight, Send, Clock, ShieldCheck, User, Loader2, Lock, Paperclip, X, Trash2, RefreshCw, Bell, BellRing } from "lucide-react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function formatChatTime(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "زمان نامشخص";
  const diff = Math.max(0, Date.now() - date.getTime());
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (minutes < 1) return "همین الان";
  if (minutes < 60) return `${minutes} دقیقه پیش`;
  if (hours < 24) return `${hours} ساعت پیش`;
  if (days < 7) return `${days} روز پیش`;
  return date.toLocaleDateString("fa-IR", { month: "short", day: "numeric" });
}

function readLastSeenMessage(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}

function saveLastSeenMessage(key: string, messageId: string) {
  try { window.localStorage.setItem(key, messageId); } catch { /* ذخیره‌سازی محلی اختیاری است. */ }
}

function errorMessage(data: any, fallback: string) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item: any) => item.msg).filter(Boolean).join("، ") || fallback;
  return fallback;
}

export default function AdminTicketDetailPage() {
  const router = useRouter();
  const params = useParams();
  const ticketId = String(params?.id ?? "");
  const token = getToken();
  const [ticket, setTicket] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [closing, setClosing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [compressing, setCompressing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | "unsupported">("default");
  const messagesRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const previousMessageCountRef = useRef<number | null>(null);
  const notificationSeenRef = useRef<Set<string>>(new Set());
  const programmaticScrollRef = useRef(false);
  const wasNearBottomRef = useRef(true);
  const forceScrollAfterSendRef = useRef(false);
  const [viewportHeight, setViewportHeight] = useState<number | null>(null);
  const [viewportTop, setViewportTop] = useState(0);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const initialViewportHeightRef = useRef<number | null>(null);
  const storageKey = `trademun-ticket-last-seen-admin-${ticketId}`;
  const requestInFlightRef = useRef(false);

  const fetchTicket = useCallback(async (showLoader = false, silent = false) => {
    if (requestInFlightRef.current) return;
    requestInFlightRef.current = true;
    if (showLoader) setLoading(true);
    if (!silent) setPageError("");
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errorMessage(data, "دریافت تیکت ناموفق بود"));
      setTicket((previous: any) => {
        if (previous && previous.id === data.id && previous.status === data.status && previous.updated_at === data.updated_at && previous.messages?.length === data.messages?.length && previous.messages?.[previous.messages.length - 1]?.id === data.messages?.[data.messages.length - 1]?.id) return previous;
        return data;
      });
    } catch (error: any) {
      if (!silent) setPageError(error?.message || "خطا در دریافت اطلاعات تیکت");
    } finally {
      requestInFlightRef.current = false;
      setLoading(false);
    }
  }, [ticketId, token]);

  // Keep the chat composer inside the *visible* mobile viewport when the keyboard opens.
  // The bottom navigation is given its own clearance while the keyboard is closed.
  useEffect(() => {
    const updateViewport = () => {
      const visual = window.visualViewport;
      const height = Math.round(visual?.height ?? window.innerHeight);
      const focused = document.activeElement === composerRef.current;
      if (initialViewportHeightRef.current === null) initialViewportHeightRef.current = window.innerHeight;
      if (!focused && height >= (initialViewportHeightRef.current ?? height) - 100) {
        initialViewportHeightRef.current = window.innerHeight;
      }
      const baseline = initialViewportHeightRef.current ?? window.innerHeight;
      const keyboard = focused && (baseline - height > 120 || window.innerHeight - height > 120);
      setViewportHeight(height);
      setViewportTop(Math.max(0, Math.round(visual?.offsetTop ?? 0)));
      setKeyboardOpen(keyboard);
    };
    updateViewport();
    const visual = window.visualViewport;
    visual?.addEventListener("resize", updateViewport);
    visual?.addEventListener("scroll", updateViewport);
    window.addEventListener("resize", updateViewport);
    window.addEventListener("orientationchange", updateViewport);
    document.addEventListener("focusin", updateViewport);
    const onFocusOut = () => window.setTimeout(updateViewport, 80);
    document.addEventListener("focusout", onFocusOut);
    return () => {
      visual?.removeEventListener("resize", updateViewport);
      visual?.removeEventListener("scroll", updateViewport);
      window.removeEventListener("resize", updateViewport);
      window.removeEventListener("orientationchange", updateViewport);
      document.removeEventListener("focusin", updateViewport);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, []);

  useEffect(() => {
    const user = getUser();
    if (!user || !user.is_admin) {
      router.replace("/login");
      return;
    }
    void fetchTicket(true);
  }, [fetchTicket, router]);

  // دریافت خودکار پیام‌های جدید؛ درخواست‌های هم‌زمان با قفل داخلی کنترل می‌شوند.
  useEffect(() => {
    if (!ticket || ticket.status !== "open") return;
    const poll = () => {
      // در پس‌زمینه فقط وقتی اعلان‌ها مجاز شده‌اند، polling ادامه پیدا می‌کند.
      if (document.visibilityState === "visible" || notificationPermission === "granted") void fetchTicket(false, true);
    };
    const timer = window.setInterval(poll, 3000);
    const onVisible = () => { if (document.visibilityState === "visible") poll(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", onVisible); };
  }, [ticket?.id, ticket?.status, fetchTicket, notificationPermission]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Telegram-like behavior: restore the unread position on open; follow new messages
  // only when the reader was already at the bottom. Never steal scroll from history reading.
  const recordVisibleMessage = useCallback(() => {
    const container = messagesRef.current;
    if (!container) return;
    const bounds = container.getBoundingClientRect();
    const nodes = Array.from(container.querySelectorAll<HTMLElement>("[data-ticket-message-id]"));
    let visibleId: string | null = null;
    for (const node of nodes) {
      const rect = node.getBoundingClientRect();
      if (rect.top < bounds.bottom && rect.bottom > bounds.top) {
        visibleId = node.dataset.ticketMessageId ?? visibleId;
      }
    }
    if (visibleId) saveLastSeenMessage(storageKey, visibleId);
  }, [storageKey]);

  const scrollToMessage = useCallback((messageId: number | string | null, behavior: ScrollBehavior = "smooth") => {
    const container = messagesRef.current;
    if (!container) return;
    programmaticScrollRef.current = true;
    if (messageId === null) {
      container.scrollTo({ top: container.scrollHeight, behavior });
      wasNearBottomRef.current = true;
      window.setTimeout(() => {
        programmaticScrollRef.current = false;
        recordVisibleMessage();
      }, behavior === "smooth" ? 700 : 140);
      return;
    }
    const target = container.querySelector<HTMLElement>(`[data-ticket-message-id="${String(messageId)}"]`);
    if (!target) {
      programmaticScrollRef.current = false;
      return;
    }
    const top = target.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - 8;
    container.scrollTo({ top: Math.max(0, top), behavior });
    wasNearBottomRef.current = false;
    window.setTimeout(() => {
      programmaticScrollRef.current = false;
      recordVisibleMessage();
    }, behavior === "smooth" ? 700 : 140);
  }, [recordVisibleMessage]);

  useEffect(() => {
    const messages = ticket?.messages || [];
    const count = messages.length;
    if (!count) return;
    const lastId = messages[count - 1]?.id ?? null;
    if (previousMessageCountRef.current === null) {
      previousMessageCountRef.current = count;
      const savedId = readLastSeenMessage(storageKey);
      const savedIndex = savedId ? messages.findIndex((item: any) => String(item.id) === savedId) : -1;
      if (savedIndex >= 0 && savedIndex < count - 1) {
        const firstUnread = messages[savedIndex + 1];
        requestAnimationFrame(() => requestAnimationFrame(() => scrollToMessage(firstUnread?.id ?? null, "auto")));
      } else {
        requestAnimationFrame(() => requestAnimationFrame(() => scrollToMessage(null, "auto")));
      }
      return;
    }

    const previousCount = previousMessageCountRef.current;
    if (count > previousCount) {
      const incoming = messages.slice(previousCount).filter((item: any) => !item.is_admin);
      const shouldFollow = forceScrollAfterSendRef.current || wasNearBottomRef.current;
      forceScrollAfterSendRef.current = false;
      if (shouldFollow) {
        requestAnimationFrame(() => requestAnimationFrame(() => scrollToMessage(null, "smooth")));
      }
      if (document.visibilityState === "hidden" && notificationPermission === "granted" && incoming.length) {
        const latest = incoming[incoming.length - 1];
        const notificationId = String(latest.id);
        if (!notificationSeenRef.current.has(notificationId)) {
          notificationSeenRef.current.add(notificationId);
          try {
            const notice = new Notification("پیام جدید در تیکت پشتیبانی", {
              body: latest.message || "یک تصویر برای شما ارسال شده است.",
              tag: `trademun-ticket-${ticketId}`,
            });
            notice.onclick = () => { window.focus(); notice.close(); };
          } catch { /* اعلان مرورگر در صورت محدودیت سیستم نادیده گرفته می‌شود. */ }
        }
      }
    }
    previousMessageCountRef.current = count;
  }, [ticket?.messages?.length, ticket?.id, scrollToMessage, storageKey, notificationPermission, ticketId]);

  const enableNotifications = async () => {
    if (typeof Notification === "undefined") { setNotificationPermission("unsupported"); return; }
    try {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
    } catch { setNotificationPermission("denied"); }
  };

  const handleScroll = () => {
    if (programmaticScrollRef.current) return;
    const el = messagesRef.current;
    if (!el) return;
    wasNearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 90;
    recordVisibleMessage();
  };

  const clearFile = () => {
    setSelectedFile(null);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSelectFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      alert("فقط فایل‌های JPG و PNG مجاز هستند");
      event.target.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert("حجم فایل حداکثر ۵ مگابایت است");
      event.target.value = "";
      return;
    }

    setCompressing(true);
    try {
      const compressed = await imageCompression(file, {
        maxSizeMB: 1,
        maxWidthOrHeight: 1920,
        useWebWorker: true,
        fileType: "image/jpeg",
        initialQuality: 0.8,
      });
      const baseName = file.name.replace(/\.[^.]+$/, "") || "attachment";
      const finalFile = new File([compressed], `${baseName}.jpg`, {
        type: "image/jpeg",
        lastModified: Date.now(),
      });
      setPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return URL.createObjectURL(finalFile);
      });
      setSelectedFile(finalFile);
    } catch (error) {
      console.error("Image compression failed:", error);
      alert("فشرده‌سازی عکس انجام نشد. لطفاً تصویر دیگری انتخاب کنید.");
      event.target.value = "";
    } finally {
      setCompressing(false);
    }
  };

  const handleSend = async () => {
    if (sending || compressing || (!reply.trim() && !selectedFile)) return;
    if (!ticket || ticket.status !== "open") return;
    setSending(true);
    setPageError("");
    try {
      let attachmentPath: string | null = null;
      let attachmentName: string | null = null;
      if (selectedFile) {
        setUploading(true);
        const formData = new FormData();
        formData.append("file", selectedFile);
        const uploadRes = await fetch(`${apiUrl}/admin/tickets/${ticketId}/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
        const uploadData = await uploadRes.json().catch(() => ({}));
        if (!uploadRes.ok) throw new Error(errorMessage(uploadData, "بارگذاری تصویر ناموفق بود"));
        attachmentPath = uploadData.path;
        attachmentName = uploadData.name;
      }

      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          message: reply.trim() || "(تصویر پیوست)",
          attachment_path: attachmentPath,
          attachment_name: attachmentName,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errorMessage(data, "ارسال پاسخ ناموفق بود"));

      setReply("");
      if (composerRef.current) composerRef.current.style.height = "44px";
      clearFile();
      forceScrollAfterSendRef.current = true;
      await fetchTicket();
    } catch (error: any) {
      setPageError(error?.message || "ارسال پاسخ انجام نشد");
    } finally {
      setSending(false);
      setUploading(false);
    }
  };

  const handleClose = async () => {
    if (closing || !confirm("این تیکت بسته شود؟ (پس از بستن امکان پاسخ وجود ندارد)")) return;
    setClosing(true);
    setPageError("");
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}/close`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errorMessage(data, "بستن تیکت ناموفق بود"));
      await fetchTicket();
    } catch (error: any) {
      setPageError(error?.message || "بستن تیکت ناموفق بود");
    } finally {
      setClosing(false);
    }
  };

  const handleDelete = async () => {
    if (deleting || !confirm("آیا مطمئنید؟ این تیکت و تمام پیام‌های آن برای همیشه حذف خواهد شد.")) return;
    setDeleting(true);
    setPageError("");
    try {
      const res = await fetch(`${apiUrl}/admin/tickets/${ticketId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errorMessage(data, "حذف تیکت ناموفق بود"));
      router.replace("/admin/tickets");
    } catch (error: any) {
      setPageError(error?.message || "حذف تیکت ناموفق بود");
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#07111f]"><Loader2 className="h-8 w-8 animate-spin text-[#d6ad60]" /></div>;
  }
  if (!ticket) {
    return (
      <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-[#030811] text-white">
        <Header />
        <main className="container mx-auto max-w-3xl flex-1 p-4">
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 text-sm text-red-300">
            {pageError || "تیکت پیدا نشد."}
            <div className="mt-4 flex gap-2">
              <Button onClick={() => void fetchTicket(true)} variant="outline" className="gap-2"><RefreshCw className="h-4 w-4" /> تلاش مجدد</Button>
              <Link href="/admin/tickets"><Button variant="ghost">بازگشت به تیکت‌ها</Button></Link>
            </div>
          </div>
        </main>
        </div>
    );
  }

  return (
    <div className="fixed inset-x-0 z-20 flex flex-col overflow-hidden bg-[#030811] text-white" style={{ top: `${viewportTop}px`, height: viewportHeight ? `${viewportHeight}px` : "100dvh", maxHeight: viewportHeight ? `${viewportHeight}px` : "100dvh" }}>
      <div className="shrink-0"><Header /></div>
      <main className="container mx-auto flex w-full max-w-4xl flex-1 min-h-0 flex-col overflow-hidden px-3 pt-1 sm:py-2" style={{ paddingBottom: keyboardOpen ? "max(0.5rem, env(safe-area-inset-bottom))" : "calc(76px + env(safe-area-inset-bottom))" }}>
        <div className="mb-1.5 flex shrink-0 flex-wrap items-center justify-between gap-2">
          <Link href="/admin/tickets">
            <Button variant="ghost" size="sm" className="gap-2 text-gray-400 hover:text-white"><ArrowRight className="h-4 w-4" /> بازگشت</Button>
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            {notificationPermission !== "unsupported" && <Button type="button" size="sm" variant="outline" onClick={() => void enableNotifications()} disabled={notificationPermission === "granted" || notificationPermission === "denied"} className="h-8 gap-1 border-white/10 text-[11px] text-gray-300">{notificationPermission === "granted" ? <BellRing className="h-3.5 w-3.5 text-emerald-400" /> : <Bell className="h-3.5 w-3.5" />}{notificationPermission === "granted" ? "اعلان‌ها فعال" : notificationPermission === "denied" ? "اعلان مسدود" : "فعال‌سازی اعلان"}</Button>}
            <span className={`rounded-full px-3 py-1 text-xs font-bold ${ticket.status === "open" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>{ticket.status === "open" ? "فعال" : "بسته"}</span>
            {ticket.status === "open" && <Button size="sm" variant="destructive" onClick={handleClose} disabled={closing || deleting} className="h-8 gap-1 text-xs">{closing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Lock className="h-3 w-3" />} بستن تیکت</Button>}
            <Button size="sm" variant="destructive" onClick={handleDelete} disabled={closing || deleting} className="h-8 gap-1 bg-red-600 text-xs hover:bg-red-700">{deleting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />} حذف</Button>
          </div>
        </div>

        <div className="mb-2 shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-[radial-gradient(ellipse_at_top_right,rgba(214,173,96,0.12),transparent_45%),linear-gradient(135deg,#14243a,#071321)] px-3.5 py-2 shadow-[0_12px_35px_rgba(0,0,0,0.2)]">
          <div className="mb-0.5 flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-gray-500">#{ticket.id}</span><span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/15 bg-emerald-400/5 px-2 py-1 text-[10px] text-emerald-300"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,.8)]" /> همگام‌سازی خودکار</span>
            <span className="rounded bg-[#d6ad60]/20 px-2 py-0.5 font-mono text-xs text-[#d6ad60]">{ticket.user_phone}</span>
            {ticket.user_name && <span className="text-xs font-bold text-gray-300">{ticket.user_name}</span>}
            <span className="flex items-center gap-1 text-[10px] text-gray-500"><Clock className="h-3 w-3" /> {new Date(ticket.created_at).toLocaleString("fa-IR")}</span>
          </div>
          <h1 className="truncate text-sm font-bold text-white">{ticket.subject}</h1>
        </div>

        {pageError && <div role="alert" className="mb-2 shrink-0 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300">{pageError}</div>}

        <div ref={messagesRef} onScroll={handleScroll} className="mb-1.5 min-h-0 flex-1 space-y-2.5 overflow-y-auto overscroll-contain rounded-2xl border border-white/10 bg-[radial-gradient(ellipse_at_top,rgba(214,173,96,0.07),transparent_50%),linear-gradient(180deg,rgba(13,27,45,0.96),rgba(4,12,22,0.98))] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_14px_38px_rgba(0,0,0,0.16)] [overflow-anchor:none] sm:p-4">
          {(ticket.messages || []).map((message: any) => {
            const isMe = Boolean(message.is_admin);
            return (
              <motion.div key={message.id} data-ticket-message-id={message.id} initial={{ opacity: 0, y: 7 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.16 }} className={`flex items-end gap-2 ${isMe ? "justify-end" : "justify-start"}`}>
                {!isMe && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/20 bg-white/10"><User className="h-4 w-4 text-gray-300" /></div>}
                <div className={`flex min-w-0 max-w-[88%] flex-col sm:max-w-[76%] ${isMe ? "items-end" : "items-start"}`}>
                  <div className={`rounded-[17px] px-3 py-2 shadow-md ${isMe ? "rounded-tr-sm bg-gradient-to-br from-[#c89a49] to-[#e2c17e] text-[#07111f]" : "rounded-tl-sm border border-white/10 bg-gradient-to-br from-[#1a2c45] to-[#051118] text-white"}`}>
                    <div className={`mb-1 flex items-center gap-1.5 ${isMe ? "text-[#07111f]/70" : "text-gray-400"}`}>
                      {isMe ? <ShieldCheck className="h-3 w-3" /> : <User className="h-3 w-3" />}
                      <span className="text-[10px] font-bold">{isMe ? "شما (پشتیبانی)" : ticket.user_phone}</span>
                    </div>
                    {message.message && <p className="whitespace-pre-wrap break-words text-[13px] leading-6">{message.message}</p>}
                    {message.attachment_path && <a href={`${apiUrl}${message.attachment_path}`} target="_blank" rel="noreferrer" className="mt-2 block"><img src={`${apiUrl}${message.attachment_path}`} alt={message.attachment_name || "پیوست"} loading="lazy" className="max-h-64 max-w-full rounded-xl border border-white/10 object-contain" /></a>}
                  </div>
                  <span className="mt-1 text-[9px] text-gray-500">{formatChatTime(message.created_at)}</span>
                </div>
                {isMe && <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[#d6ad60]/40 bg-[#d6ad60]/20"><ShieldCheck className="h-4 w-4 text-[#d6ad60]" /></div>}
              </motion.div>
            );
          })}
        </div>

        {ticket.status === "open" ? (
          <div className="relative z-10 shrink-0 space-y-1.5 rounded-2xl border border-[#d6ad60]/20 bg-[linear-gradient(135deg,rgba(17,32,51,0.98),rgba(5,14,25,0.99))] p-2 shadow-[0_12px_35px_rgba(0,0,0,0.28)] backdrop-blur-xl sm:p-2.5" style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}>
            {compressing && <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 p-2 text-xs text-gray-400"><Loader2 className="h-4 w-4 animate-spin text-[#d6ad60]" /> در حال فشرده‌سازی عکس...</div>}
            {previewUrl && !compressing && <div className="relative inline-block"><img src={previewUrl} alt="پیش‌نمایش پیوست" className="max-h-32 rounded-lg border border-white/20" /><button type="button" aria-label="حذف تصویر انتخاب‌شده" onClick={clearFile} className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 hover:bg-red-600"><X className="h-3 w-3 text-white" /></button></div>}
            <div className="flex items-end gap-2">
              <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" onChange={handleSelectFile} className="hidden" />
              <Button type="button" variant="outline" size="icon" aria-label="پیوست تصویر" onClick={() => fileInputRef.current?.click()} disabled={sending || compressing} className="h-11 w-11 shrink-0 border-white/10"><Paperclip className="h-4 w-4" /></Button>
              <textarea ref={composerRef} value={reply} onChange={(event) => { setReply(event.target.value); event.currentTarget.style.height = "44px"; event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 112)}px`; }} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void handleSend(); } }} rows={1} maxLength={2000} enterKeyHint="send" aria-label="متن پیام" placeholder="" className="h-11 max-h-28 min-h-11 min-w-0 flex-1 resize-none rounded-xl border border-white/10 bg-[#030b14]/80 px-3.5 py-2.5 text-base text-white outline-none transition-colors placeholder:text-gray-500 focus:border-[#d6ad60]/50 focus:ring-2 focus:ring-[#d6ad60]/10 sm:text-sm" />
              <Button onClick={() => void handleSend()} disabled={sending || uploading || compressing || (!reply.trim() && !selectedFile)} className="h-11 shrink-0 gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] font-bold text-[#101827] hover:opacity-90">{sending || uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}<span className="hidden sm:inline">ارسال</span></Button>
            </div>
            {uploading && <p className="text-[10px] text-gray-400">در حال بارگذاری پیوست...</p>}
          </div>
        ) : <div className="rounded-xl border border-gray-500/20 bg-gray-500/5 p-3 text-center text-xs text-gray-400">این تیکت بسته شده است و امکان ارسال پاسخ ندارد.</div>}
      </main>
    </div>
  );
}
