/**
 * Start Next dev, choose its port, and publish the `viewer` dev role.
 *
 * A console started in any project reads that role instead of being configured
 * with a port. `--discovery` keeps the standalone snapshot-API workflow.
 */
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { runNextDev } from "../../dev-registry.mjs";

const viewerRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const args = process.argv.slice(2);
const forceFlag = args.indexOf("--force");
const force = forceFlag !== -1;
if (force) args.splice(forceFlag, 1);

let discovery = process.env.KBS_DISCOVERY;
const flag = args.indexOf("--discovery");
if (flag !== -1) {
  discovery = args[flag + 1];
  args.splice(flag, 2);
  if (!discovery) {
    console.error("--discovery requires a path");
    process.exit(2);
  }
}

const env = {};
if (discovery) {
  env.KBS_DISCOVERY = path.resolve(discovery);
} else if (process.env.KBS_DISCOVERY) {
  env.KBS_DISCOVERY = process.env.KBS_DISCOVERY;
} else {
  const candidate = path.resolve(
    process.env.INIT_CWD || process.cwd(),
    ".kbs",
    "viewer.json",
  );
  if (existsSync(candidate)) env.KBS_DISCOVERY = candidate;
}

await runNextDev({
  cwd: viewerRoot,
  role: "viewer",
  label: "kbs design viewer",
  args,
  env,
  force,
});
