/**
 * Start one Next dev server, print its port first, then stream its logs.
 * The kbs dev proxy reads the first line and health-checks the port.
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createServer } from "node:net";
import path from "node:path";

const target = process.argv[2];
if (!target) {
  console.error("usage: node scripts/dev-server.mjs <app-directory>");
  process.exit(2);
}

const port = await new Promise((resolve, reject) => {
  const probe = createServer();
  probe.once("error", reject);
  probe.listen(0, "127.0.0.1", () => {
    const address = probe.address();
    const selected = typeof address === "object" && address ? address.port : 0;
    probe.close(() => (selected ? resolve(selected) : reject(new Error("no port"))));
  });
});

process.stdout.write(`${port}\n`);

const appDir = path.resolve(process.cwd(), target);
const binary = process.platform === "win32" ? "next.cmd" : "next";
const command = [
  path.join(appDir, "node_modules", ".bin", binary),
  path.join(appDir, "..", "node_modules", ".bin", binary),
].find((candidate) => existsSync(candidate));
if (!command) {
  console.error(`next is not installed for ${appDir}`);
  process.exit(2);
}
const child = spawn(
  command,
  ["dev", "--port", String(port), "--hostname", "127.0.0.1"],
  {
    cwd: appDir,
    env: process.env,
    stdio: "inherit",
  },
);
child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
