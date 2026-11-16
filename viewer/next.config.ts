import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import type { NextConfig } from "next";

const staticExport = process.env.KBS_VIEWER_STATIC === "1";

function discoveryFile(): { file: string; explicit: boolean } {
  const explicit = process.env.KBS_DISCOVERY;
  const root = process.env.INIT_CWD || process.cwd();
  return {
    file: explicit
      ? path.resolve(explicit)
      : path.resolve(root, ".kbs", "viewer.json"),
    explicit: Boolean(explicit),
  };
}

function discoveryApi(): string | undefined {
  const { file, explicit } = discoveryFile();
  if (!existsSync(file)) {
    if (explicit) {
      throw new Error(`KBS_DISCOVERY does not exist: ${file}`);
    }
    return undefined;
  }
  try {
    const parsed = JSON.parse(readFileSync(file, "utf8")) as {
      api?: unknown;
    };
    if (typeof parsed.api !== "string" || !parsed.api) {
      throw new Error("missing api");
    }
    return parsed.api.replace(/\/+$/, "");
  } catch (error) {
    throw new Error(
      `invalid viewer discovery file ${file}: ${
        error instanceof Error ? error.message : String(error)
      }`,
    );
  }
}

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
      allowedDevOrigins: [
        "127.0.0.1",
        "localhost",
        "dev.netbird.cloud",
        "*.netbird.cloud",
      ],
      async rewrites() {
        const api = discoveryApi();
        if (api) {
          return [
            {
              source: "/snapshot",
              destination: `${api}/snapshot`,
            },
            {
              source: "/api/:path*",
              destination: `${api}/api/:path*`,
            },
          ];
        }
        return [];
      },
    };

export default nextConfig;
