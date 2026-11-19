/**
 * Shared development registry for the console, viewer and API.
 *
 * Each process binds an available port and writes one role file under a
 * per-user directory. Nothing reads a port from an argument; a reader checks the
 * URL before using it.
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";

export const ROLES = ["api", "console", "viewer"];

export function devDir() {
  if (process.env.KBS_DEV_DIR) return path.resolve(process.env.KBS_DEV_DIR);
  const home = os.homedir();
  if (process.platform === "win32") {
    return path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "kbs", "dev");
  }
  if (process.platform === "darwin") {
    return path.join(home, "Library", "Caches", "kbs", "dev");
  }
  if (process.env.XDG_RUNTIME_DIR) {
    return path.join(process.env.XDG_RUNTIME_DIR, "kbs", "dev");
  }
  return path.join(home, ".cache", "kbs", "dev");
}

export function rolePath(role) {
  if (!ROLES.includes(role)) throw new Error(`unknown dev role ${role}`);
  return path.join(devDir(), `${role}.json`);
}

export async function readRole(role) {
  try {
    const value = JSON.parse(await readFile(rolePath(role), "utf8"));
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

export async function writeRole(role, url) {
  const file = rolePath(role);
  await mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const value = {
    url: url.replace(/\/+$/, ""),
    pid: process.pid,
    started_at: new Date().toISOString(),
  };
  const temporary = `${file}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  await rename(temporary, file);
  return value;
}

export async function removeRole(role) {
  const entry = await readRole(role);
  if (entry && entry.pid !== process.pid) return;
  try {
    await unlink(rolePath(role));
  } catch {
    // already gone
  }
}

export function findFreePort(host = "127.0.0.1") {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, host, () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => (port ? resolve(port) : reject(new Error("no free port"))));
    });
  });
}

export async function waitFor(url, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = "not started";
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (response.ok) return response;
      lastError = `${response.status} ${response.statusText}`.trim();
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`${url} did not become ready: ${lastError}`);
}

export function displayUrl(host, port) {
  const display = ["0.0.0.0", "::", "[::]"].includes(host) ? "127.0.0.1" : host;
  const bracketed = display.includes(":") && !display.startsWith("[") ? `[${display}]` : display;
  return `http://${bracketed}:${port}`;
}

/**
 * Start one Next dev server on a free port, publish its role, and clean up.
 * Extra arguments are passed to `next dev`; `--port` is not required.
 */
export async function runNextDev({ cwd, role, label, args = [], env = {}, force = false }) {
  const existing = await readRole(role);
  if (existing?.url && !force) {
    try {
      await waitFor(existing.url, 1500);
      console.error(`${label} is already running at ${existing.url}; pass --force to replace it`);
      process.exit(1);
    } catch {
      await removeRole(role);
    }
  }

  const nextArgs = [...args];
  let port = 0;
  const portFlag = nextArgs.indexOf("--port");
  if (portFlag === -1) {
    port = await findFreePort();
    nextArgs.push("--port", String(port));
  } else {
    port = Number(nextArgs[portFlag + 1]);
  }
  if (!nextArgs.includes("--hostname")) nextArgs.push("--hostname", "127.0.0.1");

  const child = spawn(
    process.platform === "win32" ? "next.cmd" : "next",
    ["dev", ...nextArgs],
    { cwd, env: { ...process.env, ...env }, stdio: "inherit" },
  );

  let stopped = false;
  const stop = async (code = 0) => {
    if (stopped) return;
    stopped = true;
    child.kill();
    await removeRole(role);
    process.exit(code);
  };
  process.on("SIGINT", () => stop(0));
  process.on("SIGTERM", () => stop(0));
  child.on("exit", async (code, signal) => {
    await removeRole(role);
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });

  const url = displayUrl("127.0.0.1", port);
  try {
    await waitFor(url);
  } catch (error) {
    child.kill();
    console.error(`${label} did not start: ${error instanceof Error ? error.message : error}`);
    await removeRole(role);
    process.exit(1);
  }
  await writeRole(role, url);
  console.log(`${label}: ${url}`);
  console.log(`Role: ${rolePath(role)}`);
  return { child, port, url };
}

export function nextExecutable() {
  const local = path.join("node_modules", ".bin", process.platform === "win32" ? "next.cmd" : "next");
  return existsSync(local) ? local : process.platform === "win32" ? "next.cmd" : "next";
}
