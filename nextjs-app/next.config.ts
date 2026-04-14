import type { NextConfig } from "next";

const allowedOrigins = (process.env.ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const allowedDevOrigins = allowedOrigins.map((origin) => {
  try {
    return new URL(origin).hostname;
  } catch {
    return origin.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
});

const nextConfig: NextConfig = {
  allowedDevOrigins,
  experimental: {
    serverActions: {
      allowedOrigins,
    },
  },
};

export default nextConfig;