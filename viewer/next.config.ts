import type { NextConfig } from "next";

const staticExport = process.env.KBS_VIEWER_STATIC === "1";

const nextConfig: NextConfig = staticExport
  ? {
      reactStrictMode: true,
      agentRules: false,
      output: "export",
      images: { unoptimized: true },
    }
  : {
      reactStrictMode: true,
      agentRules: false,
      async rewrites() {
        return [
          {
            source: "/snapshot",
            destination: "/data/opentargets.snapshot.json.gz",
          },
        ];
      },
    };

export default nextConfig;
