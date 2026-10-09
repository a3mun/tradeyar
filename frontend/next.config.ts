import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  output: "standalone",  // ← این خط اضافه شد
  allowedDevOrigins: ["192.168.1.7"],
};

export default nextConfig;