/**
 * Start Next dev against a project discovered by `kbs view`.
 *
 * The discovery file is read once by next.config.ts. Restart this process if
 * the Python server moves to another port.
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const viewerRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const args = process.argv.slice(2);
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

const env = { ...process.env };
if (discovery) {
  env.KBS_DISCOVERY = path.resolve(discovery);
} else if (!env.KBS_DISCOVERY) {
  const root = env.INIT_CWD || process.cwd();
  env.KBS_DISCOVERY = path.resolve(root, ".kbs", "viewer.json");
}

const child = spawn(
  process.platform === "win32" ? "next.cmd" : "next",
  ["dev", ...args],
  { cwd: viewerRoot, env, stdio: "inherit" },
);
child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
