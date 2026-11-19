/** Development origins a Next app admits, as hostnames. */
export function devOrigins(...extra: string[]): string[] {
  const configured = (process.env.KBS_DEV_ORIGINS || "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  return [...new Set([...configured, "127.0.0.1", "localhost", ...extra])];
}
