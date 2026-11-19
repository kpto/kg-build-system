import path from "node:path";

import type { NextConfig } from "next";

import { devOrigins } from "../dev-origins";

const staticExport = process.env.KBS_CONSOLE_STATIC === "1";
const basePath = process.env.KBS_CONSOLE_BASE_PATH || "";
const api = (process.env.KBS_API_URL || "").replace(/\/+$/, "");

const shared = {
  reactStrictMode: true,
  turbopack: { root: path.resolve(process.cwd(), "..") },
  transpilePackages: ["@kbs/design"],
  agentRules: false,
  basePath: basePath || undefined,
  images: { unoptimized: true },
  allowedDevOrigins: devOrigins(),
} satisfies NextConfig;

const nextConfig: NextConfig = staticExport
  ? { ...shared, output: "export" }
  : {
      ...shared,
      async rewrites() {
        if (!api) return [];
        return [
          {
            source: "/api/:path*",
            destination: `${api}/api/:path*`,
          },
        ];
      },
    };

export default nextConfig;
