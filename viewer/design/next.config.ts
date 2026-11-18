import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: { root: path.resolve(process.cwd(), "..") },
  transpilePackages: ["@kbs/design"],
  agentRules: false,
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
