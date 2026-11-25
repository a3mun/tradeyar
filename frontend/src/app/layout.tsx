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
const OG_IMAGE = `${SITE_URL}/og-image.jpg`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),

  title: {
    default: "تریدمون | تحلیل هوشمند بازارهای مالی",
    template: "%s | تریدمون",
  },
  description:
    "تریدمون دستیار تحلیل بازارهای مالی است؛ تحلیل تکنیکال ارزهای دیجیتال در صرافی‌های ایرانی، بررسی طلا و فارکس، بورس تهران، بیش از ۲۵ اندیکاتور، سیگنال‌ها، اسکنر فرصت‌ها و مشاور هوشمند.",
  applicationName: "تریدمون",
  authors: [{ name: "Trademun" }],
  creator: "Trademun",
  publisher: "Trademun",

  // Canonical را در metadata هر صفحه تعیین کنید؛ canonical سراسری باعث
  // می‌شود همه صفحات به صفحه اصلی canonical شوند.
  openGraph: {
    type: "website",
    locale: "fa_IR",
    siteName: "تریدمون",
    title: "تریدمون | تحلیل هوشمند بازارهای مالی",
    description:
      "تحلیل بازارهای مالی، ارز دیجیتال، طلا، فارکس و بورس تهران با ابزارهای تحلیلی و مشاور هوشمند تریدمون.",
    images: [
      {
        url: OG_IMAGE,
        width: 1200,
        height: 630,
        alt: "تریدمون؛ تحلیل هوشمند بازارهای مالی",
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    title: "تریدمون | تحلیل هوشمند بازارهای مالی",
    description:
      "تحلیل بازارهای مالی، ارز دیجیتال، طلا، فارکس و بورس تهران با ابزارهای تحلیلی تریدمون.",
    images: [OG_IMAGE],
  },

  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Trademun",
  },
  icons: {
    icon: "/icon-148.png",
    apple: "/icon-148.png",
  },

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
  // بزرگ‌نمایی را برای دسترس‌پذیری کاربران غیرفعال نکنید.
  userScalable: true,
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: "تریدمون",
      alternateName: "Trademun",
      url: SITE_URL,
      logo: {
        "@type": "ImageObject",
        url: `${SITE_URL}/icon-148.png`,
      },
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      url: SITE_URL,
      name: "تریدمون",
      alternateName: "Trademun",
      inLanguage: "fa-IR",
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="fa"
      dir="rtl"
      className={`dark ${vazirmatn.variable} ${lalezar.variable}`}
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
      </head>
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
