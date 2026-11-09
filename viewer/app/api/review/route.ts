import { readFile } from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Serve the optional Open Targets review sidecar. */
export async function GET() {
  const file = path.join(
    process.cwd(),
    "public",
    "data",
    "opentargets.review.json",
  );
  try {
    const body = await readFile(file);
    return new Response(new Uint8Array(body), {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
