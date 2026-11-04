"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Globe, Download, FileArchive, FolderOpen, MonitorPlay, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ExtensionGuidePage() {
  const steps = [
    {
      icon: <Download className="h-6 w-6" />,
      title: "۱. دانلود فایل افزونه",
      desc: "از داشبورد تریدمون، دکمه «دانلود افزونه» را بزنید تا فایل zip دریافت شود."
    },
    {
      icon: <FolderOpen className="h-6 w-6" />,
      title: "۲. استخراج (Extract) فایل",
      desc: "فایل zip را از حالت فشرده خارج کنید تا پوشه‌ای شامل فایل‌های افزونه در دسترس باشد."
    },
    {
      icon: <Globe className="h-6 w-6" />, // 👈 جایگزین Chrome شد
      title: "۳. باز کردن تنظیمات کروم",
      desc: "در مرورگر کروم (Chrome) به آدرس chrome://extensions بروید."
    },
    {
      icon: <FileArchive className="h-6 w-6" />,
      title: "۴. فعال‌سازی حالت توسعه‌دهنده",
      desc: "در گوشه بالای صفحه، گزینه Developer mode (حالت توسعه‌دهنده) را فعال کنید."
    },
    {
      icon: <FolderOpen className="h-6 w-6" />,
      title: "۵. بارگذاری افزونه",
      desc: "روی دکمه Load unpacked (بارگذاری بسته) کلیک کرده و پوشه‌ای که در مرحله ۲ استخراج کردید را انتخاب کنید."
    },
    {
      icon: <MonitorPlay className="h-6 w-6" />,
      title: "۶. ورود به حساب کاربری",
      desc: "روی آیکون افزونه در نوار بالای مرورگر کلیک کنید. دکمه «اتصال به حساب تریدمون» را زده و فرآیند را کامل کنید."
    }
  ];

  return (
    <div className="min-h-screen bg-[#07111f] text-white py-12 px-4">
      <div className="max-w-3xl mx-auto">
        
        {/* هدر */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
       
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">راه‌اندازی افزونه نوسان‌گیر تریدمون</h1>
          <p className="text-gray-400 text-sm sm:text-base leading-relaxed max-w-xl mx-auto">
            افزونه ما به صورت کاملاً امن و بدون نیاز به ثبت‌نام در فروشگاه گوگل نصب می‌شود. مراحل زیر را به ترتیب انجام دهید.
          </p>
        </motion.div>

        {/* مرحله‌ها */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="space-y-4 mb-12">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-4 p-4 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md">
              <div className="bg-[#d6ad60]/10 text-[#d6ad60] p-3 rounded-xl shrink-0">
                {step.icon}
              </div>
              <div>
                <h3 className="font-bold text-base text-white mb-1">{step.title}</h3>
                <p className="text-xs sm:text-sm text-gray-400 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </motion.div>

        {/* هشدار امنیتی و بازگشت */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-5 mb-8 flex items-start gap-3">
            <ShieldCheck className="h-6 w-6 text-green-500 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-green-500 text-sm mb-1">آیا این افزونه امن است؟</h3>
              <p className="text-xs text-gray-300 leading-relaxed text-justify">
                بله. این افزونه فقط در صفحات صرافی‌های دریا گلد و آلفا گلد فعال می‌شود و هیچ‌گونه دسترسی به اطلاعات شخصی یا حساب بانکی شما ندارد. همچنین هیچ سفارشی به صورت خودکار توسط افزونه ثبت نمی‌شود.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/dashboard">
              <Button variant="outline" className="w-full sm:w-auto border-white/20 text-white hover:bg-white/10 gap-2">
                <ArrowRight className="h-4 w-4" /> بازگشت به داشبورد
              </Button>
            </Link>
            <a href="/downloads/trademun-extension.zip" target="_blank" rel="noreferrer" download>
              <Button className="w-full sm:w-auto bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] font-bold gap-2">
                <Download className="h-4 w-4" /> دانلود افزونه
              </Button>
            </a>
          </div>
        </motion.div>

      </div>
    </div>
  );
}