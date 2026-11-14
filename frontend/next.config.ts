import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  output: "standalone",
  allowedDevOrigins: ["192.168.1.7"],
  
  // 🔴 فاز ۱۶.۳ — بهینه‌سازی bundle
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "framer-motion",
      "recharts",
      "@radix-ui/react-icons",
    ],
  },
  
  // 🔴 فشرده‌سازی خودکار
  compress: true,
  
  // 🔴 حذف console.log در production
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
};

export default nextConfig;