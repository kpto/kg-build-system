import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: { root: path.resolve(process.cwd(), "..") },
  transpilePackages: ["@kbs/design"],
  agentRules: false,
  basePath: "/console",
  output: process.env.NODE_ENV === "development" ? undefined : "export",
  images: { unoptimized: true },
};

export default nextConfig;
