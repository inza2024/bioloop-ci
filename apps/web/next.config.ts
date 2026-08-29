import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  // Use the stable TypeScript compiler API. The CLI path is still experimental
  // in Next.js 16 and is not needed by this project.
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
