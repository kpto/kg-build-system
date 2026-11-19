---
title: Dev mode
summary: Run the design viewer and console dev servers behind one kbs reverse proxy, driven by the framework repo's untracked .env.
section: reference
perspective: reference
order: 182
status: normative
verified: 2026-11-19
sources:
  - scripts/dev-server.mjs
  - kg_build_system/cli/service/_private/dev/env.py
  - kg_build_system/cli/service/_private/dev/session.py
  - kg_build_system/cli/service/_private/dev/proxy.py
  - kg_build_system/cli/service/_private/dev/service.py
  - kg_build_system/cli/service/_private/view.py
  - kg_build_system/cli/service/_private/main.py
---

> [!lede]
> `kbs view --dev` and `kbs console --dev` read the framework repository's
> untracked `.env`, start the developer's own viewer and console commands, and
> put both behind one reverse proxy. `kbs` keeps the snapshot and project API.

## Configuration

The file is `<framework-repo>/.env` and is untracked. It has exactly two keys:

```dotenv
KBS_DEV_VIEWER="node scripts/dev-server.mjs viewer/design"
KBS_DEV_CONSOLE="node scripts/dev-server.mjs viewer/console"
```

Both commands run with the `.env` directory as their working directory. The
command owns its framework and its port.

## First-line port contract

The command prints a bare port as its first stdout line:

```text
3001
```

Everything after that line is a log line and is prefixed with `[viewer]` or
`[console]`. `kbs` rejects a first line that is not an integer in `1..65535`.
It then polls the upstream until it answers.

`scripts/dev-server.mjs <app-directory>` is the framework helper: it finds or
starts one shared `next dev` for that app, prints its port, and holds a lease
for the lifetime of the `kbs` session.

## Shared server

One dev server runs per app for one framework checkout. The first `kbs` session
starts a small supervisor that owns `next dev`; later sessions attach to the
same server and print the same port. Each session holds one lease connection.

- When the last lease closes, the supervisor stops `next dev` and removes its
  state. The lease also closes when a session is killed, so a crashed session
  does not leave a server behind.
- The lease counts `kbs` dev sessions, not browser tabs. A tab may be idle while
  its `kbs` session is still using the server.
- A short grace period merges a stop followed immediately by a start.
- If a supervisor is killed, the next session reaps the orphan server and starts
  a fresh one.

State, lock and logs live in `.kbs/dev/` under the framework repository and are
ignored by git. Stop the shared server manually with:

```console
node scripts/dev-server.mjs stop viewer/design
node scripts/dev-server.mjs stop            # every app
```

## Commands

```console
kbs view --dev [--port 8000] [--snapshot PATH]
kbs console --dev [--project DIR] [--port 8000]
```

- `kbs view --dev` requires `KBS_DEV_VIEWER`.
- `kbs console --dev` requires both commands.
- The proxy port defaults to `8000` and tries `8001–8010`; an explicit `--port`
  is strict.
- The proxy binds loopback by default.
- `--snapshot` still selects the viewer snapshot in view dev mode.

## Routing

| Path | Target |
| --- | --- |
| `/snapshot`, `/api/snapshot` | `kbs` snapshot handler |
| `/console/api/*`, `/api/*` | `kbs` project API handler |
| `/console/*` | console dev server |
| everything else | viewer dev server |

The proxy streams HTTP responses, relays WebSocket upgrades for Next HMR, and
rewrites upstream `Host`, `Origin`, `Referer` and `Location` so the browser
only sees the `kbs` origin.

Child processes run in their own process group and are stopped on SIGINT or
SIGTERM. If either command fails before printing a port or becoming healthy,
`kbs` stops the other and exits non-zero. The shared dev supervisor runs outside
that process group, so stopping one `kbs` session leaves the server available to
the others; the last lease stops it.
