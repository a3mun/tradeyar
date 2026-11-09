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

export const metadata: Metadata = {
  title: "Trademun — تریدمون",
  description: "دستیار هوشمند تحلیل و مانیتورینگ بازار",
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