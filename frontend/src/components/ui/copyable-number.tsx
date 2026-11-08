"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface Props {
  value: number;
  display?: string;  // فرمت دلخواه (اگر نده، خودش formatNumber می‌کند)
  className?: string;
  decimals?: number;
}

function formatNum(v: number, decimals?: number): string {
  if (!isFinite(v)) return "—";
  if (decimals !== undefined) {
    return v.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  // تشخیص خودکار: اگر بزرگ‌تر از ۱۰۰۰ باشد، بدون اعشار
  if (Math.abs(v) >= 1000) {
    return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }
  if (Math.abs(v) >= 1) {
    return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  return v.toLocaleString("en-US", { maximumFractionDigits: 6 });
}

export function CopyableNumber({ value, display, className = "", decimals }: Props) {
  const [copied, setCopied] = useState(false);

  const text = display ?? formatNum(value, decimals);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      // کپی متن ساده بدون کاما (برای paste در صرافی)
      await navigator.clipboard.writeText(String(value));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = String(value);
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`group inline-flex items-center gap-1 transition-colors hover:text-cyan-400 ${className}`}
      title="کلیک برای کپی"
    >
      <span className="num">{text}</span>
      {copied ? (
        <Check className="h-2.5 w-2.5 text-green-500" />
      ) : (
        <Copy className="h-2.5 w-2.5 opacity-0 transition-opacity group-hover:opacity-60" />
      )}
    </button>
  );
}