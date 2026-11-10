"use client";

/**
 * AnimatedLogo — لوگو با افکت‌های مدرن (نسخه ۱۰ — نهایی)
 * ============================================================
 * 🔴 فاز ۱۵:
 *   • حباب‌ها با اندازه‌های متنوع (۱ تا ۴ پیکسل)
 *   • فاصله‌های عمودی و افقی متنوع
 *   • ۱۰ تا پشت، ۲ تا جلو
 *   • سایه مشکی ثابت و ملایم
 */

import { useEffect, useState } from "react";

interface AnimatedLogoProps {
  width?: number;
  height?: number;
  imgWidth?: number;
  imgHeight?: number;
  src?: string;
  showParticles?: boolean;
  className?: string;
}

interface Particle {
  id: number;
  left: number;
  bottom: number; // ارتفاع شروع (متفاوت)
  delay: number;
  duration: number;
  size: number;
  zIndex: number;
  driftX: number;
}

export function AnimatedLogo({
  width = 100,
  height = 100,
  imgWidth = 64,
  imgHeight = 64,
  src = "/icon-512.png",
  showParticles = true,
  className = "",
}: AnimatedLogoProps) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (!showParticles) return;
    
    // اندازه‌های متنوع: ۱ تا ۴ پیکسل
    const sizes = [1, 1.5, 2, 2.5, 3, 3.5, 4, 1.5, 2, 3, 2.5, 1];
    
    setParticles(
      Array.from({ length: 12 }).map((_, i) => {
        const isBack = i < 10; // ۱۰ تا پشت، ۲ تا جلو
        return {
          id: i,
          left: 5 + Math.random() * 90,
          bottom: 5 + Math.random() * 15, // شروع از ارتفاع مختلف (۵٪ تا ۲۰٪)
          delay: Math.random() * 5.0, // تاخیر متنوع (۰ تا ۵ ثانیه)
          duration: 4.0 + Math.random() * 3.5, // سرعت متنوع (۴ تا ۷.۵ ثانیه)
          size: sizes[i % sizes.length],
          zIndex: isBack ? 0 : 20,
          driftX: (Math.random() - 0.5) * 50, // جابه‌جایی افقی تا ۲۵ پیکسل
        };
      })
    );
  }, [showParticles]);

  return (
    <>
      <style jsx global>{`
        @keyframes logo-particle {
          0% {
            transform: translate(0, 0) scale(1);
            opacity: 0;
          }
          15% { opacity: 1; }
          85% { opacity: 1; }
          100% {
            transform: translate(var(--drift-x, 0px), -90px) scale(0.3);
            opacity: 0;
          }
        }
        .logo-particle {
          animation: logo-particle linear infinite;
        }
      `}</style>

      <div
        className={`relative inline-flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
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
                  bottom: `${p.bottom}%`,
                  width: `${p.size}px`,
                  height: `${p.size}px`,
                  animationDelay: `${p.delay}s`,
                  animationDuration: `${p.duration}s`,
                  boxShadow: `0 0 ${p.size * 1.5}px rgba(214, 173, 96, 0.6)`,
                  zIndex: p.zIndex,
                  ["--drift-x" as any]: `${p.driftX}px`,
                }}
              />
            ))}
          </div>
        )}

        {/* لوگو */}
        <img
          src={src}
          alt="Trademun"
          className="relative z-10 object-contain"
          style={{
            width: imgWidth,
            height: imgHeight,
            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.5))",
          }}
          draggable={false}
        />
      </div>
    </>
  );
}