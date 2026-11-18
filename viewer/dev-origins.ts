/**
 * Development origins a Next app admits, as hostnames.
 *
 * The allow-list comes from three places, merged and de-duplicated:
 *
 * 1. `KBS_DEV_ORIGINS`, a comma-separated list for one run;
 * 2. `dev-origins.local.json`, a git-ignored file beside this module, for the
 *    hosts one developer reaches the dev servers from;
 * 3. loopback, always.
 *
 * Next reads only one config file per app (`next.config.ts` here), so a second
 * `next.config.js` would shadow it. The local file is the override instead.
 */
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

type LocalOrigins = string[] | { allowedDevOrigins?: unknown };

const LOCAL_FILE = fileURLToPath(new URL("./dev-origins.local.json", import.meta.url));

function localOrigins(): string[] {
  const file = process.env.KBS_DEV_ORIGINS_FILE || LOCAL_FILE;
  if (!existsSync(file)) return [];
  try {
    const parsed = JSON.parse(readFileSync(file, "utf8")) as LocalOrigins;
    const entries = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed.allowedDevOrigins)
        ? parsed.allowedDevOrigins
        : [];
    return entries
      .filter((entry): entry is string => typeof entry === "string")
      .map((entry) => entry.trim())
      .filter(Boolean);
  } catch (error) {
    throw new Error(
      `invalid dev origins file ${file}: ${
        error instanceof Error ? error.message : String(error)
      }`,
    );
  }
}

export function devOrigins(...extra: string[]): string[] {
  const configured = (process.env.KBS_DEV_ORIGINS || "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  return [
    ...new Set([
      ...configured,
      ...localOrigins(),
      "127.0.0.1",
      "localhost",
      ...extra,
    ]),
  ];
}
