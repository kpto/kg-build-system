/**
 * Start the console Next app and connect it to the project API.
 *
 * The API role is published by `kbs console --api-only`; no port is passed by
 * hand. The console role is published for diagnostics and for the dev launcher
 * duplicate check.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";

import { readRole, runNextDev, waitFor } from "../../dev-registry.mjs";

const consoleRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const args = process.argv.slice(2);
const forceFlag = args.indexOf("--force");
const force = forceFlag !== -1;
if (force) args.splice(forceFlag, 1);

const api = await readRole("api");
if (!api?.url) {
  console.error(
    "no API role found; start `kbs console --api-only --project .` first",
  );
  process.exit(1);
}

try {
  await waitFor(`${api.url}/api/health`, 3000);
} catch (error) {
  console.error(
    `API at ${api.url} is not healthy: ${error instanceof Error ? error.message : error}`,
  );
  console.error("start `kbs console --api-only --project .` first");
  process.exit(1);
}

await runNextDev({
  cwd: consoleRoot,
  role: "console",
  label: "kbs console",
  args,
  env: { KBS_API_URL: api.url },
  force,
});
