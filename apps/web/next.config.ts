import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.BIOLOOP_NEXT_DIST_DIR ?? ".next",
  poweredByHeader: false,
  reactStrictMode: true,
  // Use the stable TypeScript compiler API. The CLI path is still experimental
  // in Next.js 16 and is not needed by this project.
  experimental: {
    useTypeScriptCli: false,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
      {
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "public, max-age=0, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

export default nextConfig;
