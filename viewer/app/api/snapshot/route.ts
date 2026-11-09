import { readFile } from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * Serve the Open Targets snapshot as pre-compressed bytes.
 *
 * Next strips `Content-Encoding` from route responses, so the route names the
 * payload `application/gzip` and the client decompresses it with
 * `DecompressionStream`. The plain public JSON remains a static fallback.
 */
export async function GET() {
  const file = path.join(
    process.cwd(),
    "public",
    "data",
    "opentargets.snapshot.json.gz",
  );
  const body = await readFile(file);
  return new Response(new Uint8Array(body), {
    headers: {
      "Content-Type": "application/gzip",
      "Cache-Control": "no-store",
    },
  });
}
