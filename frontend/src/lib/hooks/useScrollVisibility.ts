"use client";

/**
 * useScrollVisibility — نشون/مخفی بر اساس اسکرول
 * ============================================================
 * نسخه ۲.۰ · فاز ۷
 *
 * 🔴 تغییرات نسخه ۲.۰:
 *   • جای IntersectionObserver، از scroll event استفاده می‌کنه
 *   • چون IntersectionObserver به element مرجع نیاز داره که اگه
 *     mount نباشه کار نمی‌کنه
 *   • ساده، مطمئن، سبک
 */

import { useEffect, useState } from "react";

/**
 * @param threshold فاصله‌ی اسکرول به پیکسل
 * @returns آیا باید نمایش داده بشه؟
 */
export function useScrollVisibility(threshold: number = 200): boolean {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY > threshold);
    };

    // ─── بار اول ───
    onScroll();

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);

  return visible;
}