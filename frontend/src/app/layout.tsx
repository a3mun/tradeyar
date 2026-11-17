import type { Metadata, Viewport } from "next";
import { Vazirmatn, Lalezar } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { WebSocketProvider } from "@/lib/hooks/useWebSocket";
import { SignalDataProvider } from "@/hooks/useSignalData";
import "./globals.css";
import { BottomNav } from "@/components/ui/bottom-nav";
import { MaintenanceGuard } from "@/components/layout/MaintenanceGuard";

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  variable: "--font-vazirmatn",
  display: "swap",
  weight: ["400", "500", "700", "900"],
});

const lalezar = Lalezar({
  subsets: ["arabic", "latin"],
  variable: "--font-lalezar",
  display: "swap",
  weight: "400",
});

const SITE_URL = "https://trademun.ir";
const OG_IMAGE = `${SITE_URL}/og-image.jpg`; // 🔴 نام فایل رو دقیقاً همین گذاشتید

export const metadata: Metadata = {
  // ═══ سئو پایه (گوگل) ═══
  // 🔴 تیتر شامل شعار شما + کلمات کلیدی سئو
  title: {
    default: "معامله هوشمند از اینجا شروع میشه! | تریدمون",
    template: "%s | تریدمون",
  },
  description:
    "تریدمون، دستیار هوشمند تحلیل بازارهای مالی؛ بررسی لحظه‌ای طلا، ارز دیجیتال، فارکس و بورس با تحلیل تکنیکال، فاندامنتال، ۳۲ اندیکاتور تخصصی و هوش مصنوعی با مقایسه بهترین صرافی ایرانی برای معامله.",
  keywords: [
    "تریدمون", "تحلیل تکنیکال", "تحلیل فاندامنتال", "تحلیل بازار",
    "کریپتو", "فارکس", "بورس", "طلا", "ارز دیجیتال", "هوش مصنوعی",
    "نوبیتکس", "بیت پین", "تبدیل", "والکس", "صرافی ایرانی", "مقایسه بازار",
    "سیگنال", "Trademun", "trading", "crypto", "forex", "technical analysis",
  ],
  authors: [{ name: "Trademun" }],
  creator: "Trademun",
  publisher: "Trademun",
  metadataBase: new URL(SITE_URL),
  alternates: {
    canonical: SITE_URL,
  },

  // ═══ Open Graph (تلگرام، فیسبوک، لینکدین) ═══
  openGraph: {
    // 🔴 شعار شما به عنوان تیتر اصلی
    title: "معامله هوشمند از اینجا شروع میشه! | تریدمون",
    description:
      "تحلیل هوشمند ارز دیجیتال، طلا، فارکس و بورس تهران در صرافی های ایرانی.",
    url: SITE_URL,
    siteName: "تریدمون",
    locale: "fa_IR",
    type: "website",
    images: [
      {
        url: OG_IMAGE,
        width: 1200,
        height: 630,
        alt: "تریدمون - معامله هوشمند از اینجا شروع میشه!",
      },
    ],
  },

  // ═══ Twitter Card ═══
  twitter: {
    card: "summary_large_image",
    title: "معامله هوشمند از اینجا شروع میشه! | تریدمون",
    description:
      "تحلیل هوشمند ارز دیجیتال، طلا، فارکس و بورس تهران در صرافی های ایرانی.",
    images: [OG_IMAGE],
  },

  // ═══ PWA و آیکون‌ها ═══
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Trademun",
  },
  icons: {
    icon: "/icon-192.png",
    apple: "/icon-192.png",
  },

  // ═══ تنظیمات ربات‌های جستجو ═══
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0e1a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl" className={`dark ${vazirmatn.variable} ${lalezar.variable}`}>
      <body className="font-sans antialiased bg-background text-foreground">
        <MaintenanceGuard>
          <WebSocketProvider>
            <SignalDataProvider>
              <TooltipProvider>
                {children}
                <BottomNav />
              </TooltipProvider>
            </SignalDataProvider>
          </WebSocketProvider>
        </MaintenanceGuard>
      </body>
    </html>
  );
}