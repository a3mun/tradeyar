import type { Metadata, Viewport } from "next";
import { Vazirmatn } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { WebSocketProvider } from "@/lib/hooks/useWebSocket";
import { SignalDataProvider } from "@/hooks/useSignalData";
import "./globals.css";
import { BottomNav } from "@/components/ui/bottom-nav";

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  variable: "--font-vazirmatn",
  display: "swap",
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
    <html lang="fa" dir="rtl" className="dark">
      <body
        className={`${vazirmatn.variable} font-sans antialiased bg-background text-foreground`}
      >
        <WebSocketProvider>
          <SignalDataProvider>
            <TooltipProvider>
              {children}
              <BottomNav />
            </TooltipProvider>
          </SignalDataProvider>
        </WebSocketProvider>
      </body>
    </html>
  );
}