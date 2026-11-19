/**
 * Shared Next dev server for kbs dev mode.
 *
 * One supervisor owns the `next dev` process for one app directory. Every kbs
 * dev session opens a lease connection to the supervisor and keeps it open for
 * its lifetime. When the last lease closes, the supervisor stops Next and
 * removes its state, so a dev server never outlives its users.
 *
 * The command still prints the port on its first line. The supervisor, the
 * state file and the lease socket coordinate this command only; they are never
 * a serving path. kbs remains the public origin and proxies to the port.
 *
 * Manual cleanup:
 *   node scripts/dev-server.mjs stop [app-directory]
 */
import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  readdirSync,
  readSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { get } from "node:http";
import { connect, createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT = fileURLToPath(import.meta.url);
const ROOT = process.cwd();
const STATE_DIR = path.join(ROOT, ".kbs", "dev");
const GRACE_MS = 1000;
const START_TIMEOUT_MS = 30000;
const TAIL_MS = 200;
const LOCK_STALE_MS = 15000;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function appKey(appDir) {
  const relative = path.relative(ROOT, appDir) || path.basename(appDir);
  const slug =
    relative
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .toLowerCase() || "app";
  const hash = createHash("sha1").update(appDir).digest("hex").slice(0, 8);
  return `${slug}-${hash}`;
}

function appPaths(appDir) {
  const key = appKey(appDir);
  return {
    key,
    state: path.join(STATE_DIR, `${key}.json`),
    log: path.join(STATE_DIR, `${key}.log`),
    supervisorLog: path.join(STATE_DIR, `${key}.supervisor.log`),
    lock: path.join(STATE_DIR, `${key}.lock`),
  };
}

function readState(file) {
  try {
    const value = JSON.parse(readFileSync(file, "utf8"));
    return value && typeof value === "object" ? value : undefined;
  } catch {
    return undefined;
  }
}

function writeState(file, value) {
  mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  writeFileSync(temporary, JSON.stringify(value));
  renameSync(temporary, file);
}

function removeFile(file) {
  try {
    rmSync(file, { force: true });
  } catch {
    // A stale state file is harmless; health checks reject it.
  }
}

function isAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      const port = typeof address === "object" && address ? address.port : 0;
      probe.close(() => (port ? resolve(port) : reject(new Error("no port"))));
    });
  });
}

function httpHealthy(port, urlPath = "/") {
  return new Promise((resolve) => {
    const request = get(
      { host: "127.0.0.1", port, path: urlPath, timeout: 1000 },
      (response) => {
        response.resume();
        resolve(
          response.statusCode !== undefined && response.statusCode < 500,
        );
      },
    );
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function connectWithTimeout(options, timeout = 600) {
  return new Promise((resolve, reject) => {
    const socket = connect(options);
    const timer = setTimeout(() => {
      socket.destroy();
      reject(new Error("timeout"));
    }, timeout);
    socket.once("connect", () => {
      clearTimeout(timer);
      resolve(socket);
    });
    socket.once("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

async function controlReachable(state) {
  try {
    const socket = await connectWithTimeout(
      { host: "127.0.0.1", port: state.controlPort },
      400,
    );
    socket.destroy();
    return true;
  } catch {
    return false;
  }
}

function send(socket, message) {
  socket.write(`${JSON.stringify(message)}\n`);
}

function readReply(socket, timeout = 600) {
  return new Promise((resolve, reject) => {
    let buffer = "";
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error("timeout"));
    }, timeout);
    const onData = (chunk) => {
      buffer += chunk.toString();
      const index = buffer.indexOf("\n");
      if (index === -1) return;
      cleanup();
      resolve(buffer.slice(0, index));
    };
    const onError = (error) => {
      cleanup();
      reject(error);
    };
    const onClose = () => {
      cleanup();
      reject(new Error("closed"));
    };
    function cleanup() {
      clearTimeout(timer);
      socket.off("data", onData);
      socket.off("error", onError);
      socket.off("close", onClose);
    }
    socket.on("data", onData);
    socket.on("error", onError);
    socket.on("close", onClose);
  });
}

function nextBinary(appDir) {
  const name = process.platform === "win32" ? "next.cmd" : "next";
  const candidates = [
    path.join(appDir, "node_modules", ".bin", name),
    path.join(appDir, "..", "node_modules", ".bin", name),
  ];
  const found = candidates.find(existsSync);
  if (!found) {
    throw new Error(`next is not installed for ${appDir}`);
  }
  return found;
}

function killTree(pid, signal = "SIGTERM") {
  if (!Number.isInteger(pid) || pid <= 0) return;
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(pid), "/T", "/F"], { stdio: "ignore" });
    return;
  }
  try {
    process.kill(-pid, signal);
  } catch {
    try {
      process.kill(pid, signal);
    } catch {
      // Already gone.
    }
  }
}

async function tryLease(state) {
  const socket = await connectWithTimeout(
    { host: "127.0.0.1", port: state.controlPort },
    600,
  );
  send(socket, { token: state.token, pid: process.pid });
  const reply = JSON.parse(await readReply(socket, 600));
  if (!reply.ok) {
    socket.destroy();
    throw new Error(reply.error || "lease refused");
  }
  socket.pause();
  socket.removeAllListeners("data");
  return socket;
}

function logTail(file, size = 2000) {
  try {
    const content = readFileSync(file, "utf8");
    return content.slice(-size);
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Supervisor: owns Next, counts leases, stops when the last lease closes.
// ---------------------------------------------------------------------------

async function runSupervisor(appDir) {
  mkdirSync(STATE_DIR, { recursive: true });
  const paths = appPaths(appDir);

  if (!acquireLock(paths.lock, paths.state)) {
    process.exit(0);
  }

  const token = randomBytes(16).toString("hex");
  writeFileSync(paths.log, "");
  const log = (line) => {
    try {
      writeFileSync(paths.log, `${line}\n`, { flag: "a" });
    } catch {
      // Diagnostics must never take the server down.
    }
  };
  const logFd = openSync(paths.log, "a");

  let child;
  let control;
  let serverPort;
  let controlPort;
  let leases = new Set();
  let idleTimer;
  let startTimer;
  let shuttingDown = false;

  const state = () => ({
    appDir,
    pid: process.pid,
    serverPid: child?.pid,
    port: serverPort,
    controlPort,
    token,
    log: paths.log,
    startedAt: Date.now(),
  });

  async function launch(port) {
    serverPort = port;
    log(`[supervisor] starting next dev on 127.0.0.1:${serverPort}`);
    const running = spawn(
      nextBinary(appDir),
      ["dev", "--port", String(serverPort), "--hostname", "127.0.0.1"],
      {
        cwd: appDir,
        env: process.env,
        detached: true,
        stdio: ["ignore", logFd, logFd],
      },
    );
    child = running;
    const deadline = Date.now() + START_TIMEOUT_MS;
    while (Date.now() < deadline) {
      if (running.exitCode !== null) {
        throw new Error(`next dev exited with ${running.exitCode}`);
      }
      if (await httpHealthy(serverPort)) {
        running.once("exit", (code, signal) => {
          if (shuttingDown || child !== running) return;
          log(
            `[supervisor] next dev exited (${code ?? signal}); restarting on the same port`,
          );
          child = undefined;
          void restart();
        });
        return;
      }
      await delay(200);
    }
    throw new Error(`next dev did not answer on 127.0.0.1:${serverPort}`);
  }

  async function restart() {
    if (shuttingDown) return;
    const port = serverPort;
    for (let attempt = 0; attempt < 3 && !shuttingDown; attempt += 1) {
      await delay(500);
      try {
        await launch(port);
        writeState(paths.state, state());
        return;
      } catch (error) {
        log(`[supervisor] restart failed: ${String(error)}`);
      }
    }
    if (!shuttingDown) {
      log("[supervisor] next dev could not be restarted");
      void shutdown();
    }
  }

  async function start() {
    let lastError;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const port = await freePort();
      try {
        await launch(port);
        return;
      } catch (error) {
        lastError = error;
        log(`[supervisor] ${String(error)}`);
        if (child && child.exitCode === null) {
          killTree(child.pid);
          await delay(500);
        }
        child = undefined;
      }
    }
    throw lastError ?? new Error("next dev did not start");
  }

  function scheduleIdle() {
    if (shuttingDown) return;
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      idleTimer = undefined;
      if (leases.size === 0) void shutdown();
    }, GRACE_MS);
  }

  async function shutdown() {
    if (shuttingDown) return;
    shuttingDown = true;
    if (idleTimer) clearTimeout(idleTimer);
    if (startTimer) clearTimeout(startTimer);
    // Remove the state before the slow process teardown so a new client starts
    // a fresh supervisor instead of leasing a dying one.
    removeFile(paths.state);
    removeFile(paths.lock);
    log("[supervisor] no leases left; stopping next dev");
    if (control) control.close();
    for (const socket of leases) socket.destroy();
    leases.clear();
    if (child && child.exitCode === null) {
      killTree(child.pid);
      await delay(1500);
      if (child.exitCode === null) killTree(child.pid, "SIGKILL");
    }
    process.exit(0);
  }

  control = createServer((socket) => {
    let buffer = "";
    let registered = false;
    const onData = (chunk) => {
      buffer += chunk.toString();
      let index;
      while ((index = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 1);
        if (!line) continue;
        let message;
        try {
          message = JSON.parse(line);
        } catch {
          socket.destroy();
          return;
        }
        if (message.token !== token) {
          send(socket, { error: "bad token" });
          socket.destroy();
          return;
        }
        if (message.stop) {
          send(socket, { ok: true });
          socket.destroy();
          void shutdown();
          return;
        }
        if (registered) continue;
        registered = true;
        leases.add(socket);
        if (idleTimer) {
          clearTimeout(idleTimer);
          idleTimer = undefined;
        }
        send(socket, { ok: true });
        socket.pause();
        socket.removeListener("data", onData);
      }
    };
    socket.on("data", onData);
    socket.on("close", () => {
      if (!registered) return;
      leases.delete(socket);
      if (leases.size === 0) scheduleIdle();
    });
    socket.on("error", () => {});
  });

  const fail = async (error) => {
    log(`[supervisor] ${String(error)}`);
    shuttingDown = true;
    if (child && child.exitCode === null) killTree(child.pid);
    removeFile(paths.state);
    removeFile(paths.lock);
    process.exit(1);
  };

  process.on("SIGTERM", () => void shutdown());
  process.on("SIGINT", () => void shutdown());
  process.on("uncaughtException", (error) => void fail(error));
  process.on("unhandledRejection", (error) => void fail(error));

  try {
    await start();
    controlPort = await freePort();
    await new Promise((resolve, reject) => {
      control.once("error", reject);
      control.listen(controlPort, "127.0.0.1", resolve);
    });
    writeState(paths.state, state());
    startTimer = setTimeout(() => {
      if (leases.size === 0) void shutdown();
    }, START_TIMEOUT_MS);
  } catch (error) {
    await fail(error);
  }
}

function acquireLock(lock, statePath) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      writeFileSync(lock, String(process.pid), { flag: "wx" });
      return true;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      const state = readState(statePath);
      if (state && Number.isInteger(state.pid) && isAlive(state.pid)) {
        return false;
      }
      let age = LOCK_STALE_MS;
      try {
        age = Date.now() - statSync(lock).mtimeMs;
      } catch {
        // The lock disappeared between checks.
      }
      if (age < LOCK_STALE_MS) return false;
      removeFile(lock);
    }
  }
  return false;
}

// ---------------------------------------------------------------------------
// Client: ensure a supervisor, hold one lease, and stream its log.
// ---------------------------------------------------------------------------

function spawnSupervisor(appDir) {
  const paths = appPaths(appDir);
  const fd = openSync(paths.supervisorLog, "a");
  const child = spawn(
    process.execPath,
    [SCRIPT, "__supervisor", appDir],
    {
      cwd: ROOT,
      env: process.env,
      detached: true,
      stdio: ["ignore", fd, fd],
    },
  );
  child.unref();
  closeSync(fd);
  return child.pid;
}

async function attach(state, lease, paths) {
  let tail;
  const finish = (code) => {
    if (tail) clearInterval(tail);
    try {
      lease.destroy();
    } catch {
      // Already closed.
    }
    process.exit(code);
  };

  lease.on("close", () => finish(0));
  lease.on("error", () => finish(1));
  process.stdout.on("error", () => finish(0));
  process.on("SIGTERM", () => finish(0));
  process.on("SIGINT", () => finish(0));

  try {
    process.stdout.write(`${state.port}\n`);
  } catch {
    finish(0);
    return;
  }

  let offset = 0;
  try {
    offset = Math.max(0, statSync(paths.log).size - 4000);
  } catch {
    offset = 0;
  }
  tail = setInterval(() => {
    let size;
    try {
      size = statSync(paths.log).size;
    } catch {
      return;
    }
    if (size < offset) offset = 0;
    if (size === offset) return;
    const fd = openSync(paths.log, "r");
    const buffer = Buffer.alloc(size - offset);
    try {
      readSync(fd, buffer, 0, buffer.length, offset);
      offset = size;
      process.stdout.write(buffer);
    } catch {
      finish(0);
    } finally {
      closeSync(fd);
    }
  }, TAIL_MS);
}

async function runClient(appDir) {
  mkdirSync(STATE_DIR, { recursive: true });
  const paths = appPaths(appDir);
  const deadline = Date.now() + START_TIMEOUT_MS;
  let supervisorPid;
  let spawns = 0;

  while (Date.now() < deadline) {
    const state = readState(paths.state);
    if (state && state.appDir === appDir) {
      let lease;
      try {
        lease = await tryLease(state);
      } catch {
        // Only reap when the supervisor itself is unreachable. A reachable
        // supervisor may refuse a stale token; it must not be killed.
        if (await controlReachable(state)) {
          await delay(150);
          continue;
        }
        if (state.serverPid && isAlive(state.serverPid)) {
          killTree(state.serverPid);
        }
        if (state.pid && isAlive(state.pid)) {
          try {
            process.kill(state.pid, "SIGTERM");
          } catch {
            // Already gone.
          }
        }
        removeFile(paths.state);
        removeFile(paths.lock);
      }
      if (lease) {
        await attach(state, lease, paths);
        return;
      }
    }
    if (supervisorPid && isAlive(supervisorPid)) {
      // The supervisor is still starting; wait for its state file.
    } else if (spawns < 3) {
      supervisorPid = spawnSupervisor(appDir);
      spawns += 1;
    } else {
      const late = readState(paths.state);
      if (!late) break;
    }
    await delay(150);
  }

  const output = logTail(paths.log);
  throw new Error(
    `dev server for ${appDir} did not become ready` +
      (output ? `\n${output}` : ""),
  );
}

// ---------------------------------------------------------------------------
// Stop command.
// ---------------------------------------------------------------------------

async function stopOne(appDir) {
  const paths = appPaths(appDir);
  const state = readState(paths.state);
  if (!state) return false;
  try {
    const socket = await connectWithTimeout(
      { host: "127.0.0.1", port: state.controlPort },
      500,
    );
    send(socket, { token: state.token, stop: true });
    socket.destroy();
  } catch {
    // Fall through to signals.
  }
  if (state.serverPid && isAlive(state.serverPid)) {
    killTree(state.serverPid);
  }
  if (state.pid && isAlive(state.pid)) {
    try {
      process.kill(state.pid, "SIGTERM");
    } catch {
      // Already gone.
    }
  }
  removeFile(paths.state);
  removeFile(paths.lock);
  return true;
}

async function runStop(target) {
  const targets = [];
  if (target) {
    targets.push(path.resolve(ROOT, target));
  } else {
    let names = [];
    try {
      names = readdirSync(STATE_DIR).filter((name) => name.endsWith(".json"));
    } catch {
      return;
    }
    for (const name of names) {
      const state = readState(path.join(STATE_DIR, name));
      if (state && typeof state.appDir === "string") {
        targets.push(state.appDir);
      }
    }
  }
  let stopped = 0;
  for (const appDir of targets) {
    if (await stopOne(appDir)) {
      stopped += 1;
      process.stdout.write(`stopped ${path.relative(ROOT, appDir)}\n`);
    }
  }
  if (stopped === 0) {
    process.stdout.write("no running dev server\n");
  }
}

// ---------------------------------------------------------------------------
// Entry point.
// ---------------------------------------------------------------------------

const [target, ...rest] = process.argv.slice(2);

if (!target) {
  process.stderr.write(
    "usage: node scripts/dev-server.mjs <app-directory>\n" +
      "       node scripts/dev-server.mjs stop [app-directory]\n",
  );
  process.exit(2);
}

try {
  if (target === "stop") {
    await runStop(rest[0]);
  } else if (target === "__supervisor") {
    await runSupervisor(path.resolve(ROOT, rest[0]));
  } else {
    await runClient(path.resolve(ROOT, target));
  }
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
}
