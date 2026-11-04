"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, getUser } from "@/lib/auth";
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, Download } from "lucide-react";
import Link from "next/link";

export default function ExtensionConnectPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error" | "no_extension">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const init = async () => {
      // ۱. چک لاگین
      const token = getToken();
      const user = getUser();
      if (!token || !user) {
        router.replace("/login");
        return;
      }

      // ۲. پیدا کردن اکستنشن (بررسی اینکه آیا content script تزریق شده یا نه)
      const isExtensionInstalled = document.documentElement.getAttribute("data-trademun-extension") === "true";
      
      if (!isExtensionInstalled) {
        // یک روش جایگزین: چک کنیم که آیا `connector.js` توی صفحه اجرا شده یا نه
        // به این صورت که منتظر می‌مونیم ببینیم آیا `window.postMessage` جواب می‌ده
        const extensionDetected = await new Promise<boolean>((resolve) => {
          const timer = setTimeout(() => resolve(false), 1500);
          window.addEventListener("message", function handler(event) {
            if (event.data && event.data.type === "TRADEMUN_EXTENSION_READY") {
              clearTimeout(timer);
              window.removeEventListener("message", handler);
              resolve(true);
            }
          });
          // درخواست به اکستنشن
          window.postMessage({ type: "CHECK_TRADEMUN_EXTENSION" }, "*");
        });

        if (!extensionDetected) {
          setStatus("no_extension");
          return;
        }
      }

      // ۳. گرفتن توکن اکستنشن از بک‌اند
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/extension/token`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
        });

        const data = await res.json();
        if (!res.ok || !data.token) {
          throw new Error(data.detail || "خطا در دریافت توکن");
        }

        // ۴. ارسال توکن به اکستنشن از طریق connector.js
        // ما یک پیام به window می‌فرستیم و connector.js اون رو می‌گیره
        window.postMessage({ type: "TRADEMUN_EXTENSION_TOKEN", token: data.token }, "*");
        
        setStatus("success");
        
        // 👈 تلاش برای بستن تب و برگشت به تب قبلی
        setTimeout(() => {
          window.close();
        }, 2000);
        
      } catch (err: any) {
        setStatus("error");
        setErrorMsg(err.message || "خطا در ارتباط با سرور");
      }
    };

    init();
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-white p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }} 
        className="w-full max-w-md rounded-3xl border border-white/10 bg-gradient-to-br from-[#0d1b2d] to-[#07111f] p-8 shadow-2xl text-center"
      >
        {status === "loading" && (
          <>
            <Loader2 className="mx-auto h-16 w-16 text-[#d6ad60] animate-spin mb-6" />
            <h1 className="text-xl font-bold mb-2">در حال اتصال...</h1>
            <p className="text-sm text-gray-400">لطفاً صبر کنید تا اتصال اکستنشن برقرار شود.</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle2 className="mx-auto h-16 w-16 text-green-500 mb-6" />
            <h1 className="text-xl font-bold mb-2 text-green-400">اتصال با موفقیت انجام شد!</h1>
            <p className="text-sm text-gray-400 mb-6">می‌توانید این تب را ببندید و به صرافی برگردید. پنل تحلیل فعال شد.</p>
            <div className="text-xs text-gray-500">این تب به صورت خودکار بسته می‌شود...</div>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle className="mx-auto h-16 w-16 text-red-500 mb-6" />
            <h1 className="text-xl font-bold mb-2 text-red-400">خطا در اتصال</h1>
            <p className="text-sm text-gray-400 mb-6">{errorMsg}</p>
            <Link href="/dashboard" className="inline-block bg-[#d6ad60] text-[#101827] px-6 py-2 rounded-lg font-bold text-sm hover:opacity-90">
              بازگشت به داشبورد
            </Link>
          </>
        )}

        {status === "no_extension" && (
          <>
            <Download className="mx-auto h-16 w-16 text-yellow-500 mb-6" />
            <h1 className="text-xl font-bold mb-2 text-yellow-400">اکستنشن نصب نیست</h1>
            <p className="text-sm text-gray-400 mb-6">
              برای استفاده از این قابلیت، ابتدا اکستنشن تریدمون را نصب کنید.
              <br />
              راهنمای نصب در داشبورد موجود است.
            </p>
            <Link href="/dashboard" className="inline-block bg-[#d6ad60] text-[#101827] px-6 py-2 rounded-lg font-bold text-sm hover:opacity-90">
              بازگشت به داشبورد
            </Link>
          </>
        )}
      </motion.div>
    </div>
  );
}