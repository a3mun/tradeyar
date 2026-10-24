"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { setToken, setUser } from "@/lib/auth";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { ShieldCheck, Zap, Brain } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [timer, setTimer] = useState(0);

  useEffect(() => {
    if (timer > 0) {
      const t = setTimeout(() => setTimer(timer - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [timer]);

  const handleSendOtp = async () => {
    if (!phone || phone.length < 11) return setError("شماره موبایل نامعتبر است");
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });
      
      if (!res.ok && res.status !== 500) {
        const data = await res.json();
        throw new Error(data.detail || "خطا در ارسال کد");
      }
      
      setStep(2);
      setTimer(60);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length < 5) return setError("کد ۵ رقمی را وارد کنید");
    
    setLoading(true);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "کد نامعتبر است");
      }

      // ⬅️ ذخیره توکن و اطلاعات کاربر
      setToken(data.access_token);
      setUser(data.user);
      
      // ⬅️ استفاده از router.push (بدون رفرش)
      if (data.user.is_admin) {
        router.push("/admin");
      } else {
        router.push("/dashboard");
      }
      
    } catch (err: any) {
      setError(err.message);
      setLoading(false); 
    }
  };
  
  return (
    <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none flex items-end">
        <svg className="w-full h-[60vh]" viewBox="0 0 1000 400" preserveAspectRatio="none">
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.5" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <motion.path
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 3, ease: "easeInOut" }}
            d="M0,350 C100,350 150,300 250,250 C350,200 400,280 500,200 C600,120 650,180 750,100 C850,20 900,50 1000,10"
            fill="none"
            stroke="var(--primary)"
            strokeWidth="3"
          />
        </svg>
      </div>

      <Header />
      
      <main className="relative z-10 flex flex-1 items-center justify-center p-4 sm:p-8">
        <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-border/50 bg-background/80 backdrop-blur-xl shadow-2xl lg:grid-cols-2">
          
          <div className="relative hidden flex-col justify-between bg-gradient-to-br from-primary/10 via-background/50 to-background p-10 lg:flex">
            <div className="relative z-10">
              <h2 className="mb-4 text-3xl font-bold leading-tight text-foreground">
                دستیار هوشمند <br /> 
                <span className="text-primary">تحلیل بازار</span>
              </h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                با تریدمون، تحلیل تکنیکال دقیق و سیگنال‌های لحظه‌ای رو از صرافی‌های ایرانی دریافت کن.
              </p>
              <div className="mt-8 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/20 p-2 text-primary"><Zap className="h-5 w-5" /></div>
                  <span className="text-sm font-medium">تحلیل ۵ گروهی با ۲۰+ اندیکاتور</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/20 p-2 text-primary"><ShieldCheck className="h-5 w-5" /></div>
                  <span className="text-sm font-medium">سیستم مدیریت ریسک و هشدار تله‌ها</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/20 p-2 text-primary"><Brain className="h-5 w-5" /></div>
                  <span className="text-sm font-medium">تحلیل عمیق و هوش مصنوعی</span>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-12">
            <div className="mx-auto max-w-sm space-y-6 text-center">
              <div className="space-y-2">
                <h1 className="text-2xl font-bold">خوش آمدید 👋</h1>
                <p className="text-sm text-muted-foreground">
                  {step === 1 
                    ? "برای ورود یا ثبت‌نام، شماره موبایل خود را وارد کنید" 
                    : "کد ۵ رقمی ارسال شده را وارد کنید"}
                </p>
              </div>

              {error && <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

              {step === 1 ? (
                <div className="space-y-5 pt-4">
                  <div className="space-y-2 text-right">
                    <label className="text-xs text-muted-foreground">شماره موبایل</label>
                    <Input
                      type="tel"
                      placeholder="۰۹۱۲۳۴۵۶۷۸۹"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="text-center dir-ltr text-lg h-12"
                      maxLength={11}
                    />
                  </div>
                  <Button onClick={handleSendOtp} disabled={loading} className="w-full h-12 text-base">
                    {loading ? "در حال ارسال..." : "دریافت کد ورود"}
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleVerify} className="space-y-5 pt-4">
                  <div className="space-y-2 text-right">
                    <label className="text-xs text-muted-foreground">کد تایید</label>
                    <Input
                      type="text"
                      placeholder="- - - - -"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      className="text-center dir-ltr text-2xl tracking-[0.5em] font-mono h-14"
                      maxLength={5}
                    />
                  </div>
                  <Button type="submit" disabled={loading} className="w-full h-12 text-base">
                    {loading ? "در حال بررسی..." : "ورود به حساب"}
                  </Button>
                  <div className="text-center text-sm">
                    {timer > 0 ? (
                      <span className="text-muted-foreground">ارسال مجدد در {timer} ثانیه</span>
                    ) : (
                      <button type="button" onClick={handleSendOtp} className="text-primary hover:underline">
                        ارسال مجدد کد
                      </button>
                    )}
                  </div>
                </form>
              )}
            </div>
          </div>

        </div>
      </main>
      <Footer />
    </div>
  );
}