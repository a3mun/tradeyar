"use client";

/**
 * AnimatedLogo — لوگو با افکت‌های مدرن (نسخه ۶ — نهایی)
 * ============================================================
 * 🔴 فاز ۱۴.۹.۱۰:
 *   • قابل تنظیم: مربع / مستطیل
 *   • حلقه چرخان (اختیاری، پیش‌فرض false)
 *   • حباب‌های طلایی
 *   • بدون blur، بدون افت کیفیت
 */

import { useEffect, useState } from "react";

interface AnimatedLogoProps {
  /** عرض کل (شامل حلقه + ذرات) */
  width?: number;
  /** ارتفاع کل (شامل حلقه + ذرات) */
  height?: number;
  /** عرض خود تصویر */
  imgWidth?: number;
  /** ارتفاع خود تصویر */
  imgHeight?: number;
  /** مسیر تصویر (پیش‌فرض: /icon-512.png) */
  src?: string;
  /** نمایش ذرات */
  showParticles?: boolean;
  /** نمایش حلقه چرخان (پیش‌فرض: false) */
  showOrbit?: boolean;
  /** کلاس اضافی */
  className?: string;
}

interface Particle {
  id: number;
  left: number;
  delay: number;
  duration: number;
  size: number;
}

export function AnimatedLogo({
  width = 100,
  height = 100,
  imgWidth = 64,
  imgHeight = 64,
  src = "/icon-512.png",
  showParticles = true,
  showOrbit = false,
  className = "",
}: AnimatedLogoProps) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (!showParticles) return;
    setParticles(
      Array.from({ length: 10 }).map((_, i) => ({
        id: i,
        left: 10 + Math.random() * 80,
        delay: Math.random() * 2.5,
        duration: 2.5 + Math.random() * 1.5,
        size: 2 + Math.random() * 2,
      }))
    );
  }, [showParticles]);

  return (
    <>
      <style jsx global>{`
        @keyframes logo-glow {
          0%, 100% {
            filter: drop-shadow(0 0 3px rgba(214, 173, 96, 0.35))
                    drop-shadow(0 0 6px rgba(214, 173, 96, 0.2));
          }
          50% {
            filter: drop-shadow(0 0 6px rgba(214, 173, 96, 0.6))
                    drop-shadow(0 0 12px rgba(214, 173, 96, 0.3));
          }
        }
        @keyframes logo-orbit {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes logo-particle {
          0% {
            transform: translateY(0) scale(1);
            opacity: 0;
          }
          15% { opacity: 1; }
          85% { opacity: 1; }
          100% {
            transform: translateY(-80px) scale(0.3);
            opacity: 0;
          }
        }
        .logo-animated-img {
          animation: logo-glow 4s ease-in-out infinite;
        }
        .logo-animated-img:hover {
          animation: logo-glow 1.5s ease-in-out infinite;
        }
        .logo-orbit-ring {
          animation: logo-orbit 14s linear infinite;
        }
        .logo-particle {
          animation: logo-particle linear infinite;
        }
      `}</style>

      <div
        className={`relative inline-flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
        {/* حلقه‌ی چرخان (اختیاری) */}
        {showOrbit && (
          <svg
            className="logo-orbit-ring pointer-events-none absolute inset-0"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            style={{ width, height }}
            aria-hidden="true"
          >
            <ellipse
              cx="50"
              cy="50"
              rx="46"
              ry="46"
              fill="none"
              stroke="rgba(214, 173, 96, 0.20)"
              strokeWidth="0.5"
              strokeDasharray="3 10"
            />
            <ellipse
              cx="50"
              cy="50"
              rx="46"
              ry="46"
              fill="none"
              stroke="rgba(214, 173, 96, 0.95)"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeDasharray="30 259"
            />
          </svg>
        )}

        {/* حباب‌های طلایی */}
        {showParticles && (
          <div
            className="pointer-events-none absolute inset-0 overflow-hidden"
            aria-hidden="true"
          >
            {particles.map((p) => (
              <div
                key={p.id}
                className="logo-particle absolute rounded-full bg-[#d6ad60]"
                style={{
                  left: `${p.left}%`,
                  bottom: "20%",
                  width: `${p.size}px`,
                  height: `${p.size}px`,
                  animationDelay: `${p.delay}s`,
                  animationDuration: `${p.duration}s`,
                  boxShadow: "0 0 5px rgba(214, 173, 96, 0.8)",
                }}
              />
            ))}
          </div>
        )}

        {/* لوگو */}
        <img
          src={src}
          alt="Trademun"
          className="logo-animated-img relative z-10 object-contain"
          style={{ width: imgWidth, height: imgHeight }}
          draggable={false}
        />
      </div>
    </>
  );
}