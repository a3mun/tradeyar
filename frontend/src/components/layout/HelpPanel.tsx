"use client";

import { useState } from "react";
import { HelpCircle, X, Book, Zap, BarChart3, Shield, Sparkles } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

const SECTIONS = [
  {
    icon: <Zap className="h-4 w-4 text-purple-400" />,
    title: "شروع سریع",
    content: [
      "نماد رو از جستجو یا Popular انتخاب کن",
      "صرافی مورد نظرت رو از تنظیمات انتخاب کن",
      "تایم‌فریم و پروفایل ریسک رو تنظیم کن",
      "سیگنال توی کارت وسط صفحه نمایش داده می‌شه",
    ],
  },
  {
    icon: <BarChart3 className="h-4 w-4 text-green-400" />,
    title: "تحلیل ۵ گروهی",
    content: [
      "مومنتوم: RSI, Stochastic, Williams, CCI, ROC",
      "روند: EMA200, MACD, ADX, Supertrend",
      "نوسان: Bollinger, ATR, Keltner, Donchian",
      "حجم: OBV, CVD, Delta, CMF, MFI",
      "ساختار: Pivot, Swing, Fibonacci, S/R",
    ],
  },
  {
    icon: <Shield className="h-4 w-4 text-blue-400" />,
    title: "مدیریت ریسک",
    content: [
      "هر سیگنال حد ضرر (SL) و هدف (TP) داره",
      "R:R = 2 یعنی ۱ ریسک، ۲ سود",
      "پروفایل جسورانه: ۲-۳٪ سرمایه",
      "پروفایل محتاطانه: ۱-۲٪ سرمایه",
      "هیچ‌وقت بدون SL وارد نشو",
    ],
  },
  {
    icon: <Sparkles className="h-4 w-4 text-yellow-400" />,
    title: "تحلیل هوش مصنوعی",
    content: [
      "کلید DeepSeek خودت رو وارد کن (رایگان)",
      "دکمه «تحلیل با AI» بزن",
      "AI با لحن خودمونی راهنمایی می‌کنه",
      "به‌عنوان مشاوره، نه تصمیم نهایی",
    ],
  },
  {
    icon: <Book className="h-4 w-4 text-cyan-400" />,
    title: "راستی‌آزمایی",
    content: [
      "سیگنال‌ها خودکار ثبت می‌شن",
      "سیستم روی هر بار باز شدن بررسی می‌کنه",
      "برد/باخت/منقضی خودکار تشخیص داده می‌شه",
      "آمار توی صفحه پایین نمایش داده می‌شه",
    ],
  },
];

export function HelpPanel() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger className="inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground">
        <HelpCircle className="h-4 w-4" />
      </SheetTrigger>
      <SheetContent side="left" className="w-96 overflow-y-auto">
        <div className="mt-6 space-y-4">
          <div className="text-center">
            <h2 className="text-lg font-bold">راهنما</h2>
            <p className="text-xs text-muted-foreground mt-1">
              آشنایی سریع با تریدمون
            </p>
          </div>

          <div className="space-y-3">
            {SECTIONS.map((section, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-border/40 bg-muted/10 p-3"
              >
                <div className="flex items-center gap-2 mb-2">
                  {section.icon}
                  <h3 className="text-xs font-bold">{section.title}</h3>
                </div>
                <ul className="space-y-1 pr-4 text-[10px] text-muted-foreground list-disc">
                  {section.content.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-center">
            <p className="text-[10px] text-muted-foreground">
              Trademun v6.0 · دستیار هوشمند معامله‌گر
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}