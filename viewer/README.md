# Viewer workspace

Two Next apps share one design language:

```text
shared/    @kbs/design: tokens, theme names and primitives
design/    the knowledge graph design viewer
console/   the project notebook console
```

Install once from this directory:

```console
cd viewer
npm install
```

## Build and serve

Build both static exports:

```console
npm run build:static --workspace design
npm run build:static --workspace console
```

Serve a project with the Python host:

```console
kbs console --project /path/to/project
```

`kbs console` serves the console at `/console/`, the design viewer at `/` and the
API at `/console/api/`. `kbs view` serves the standalone design viewer and its
snapshot. Node is not required at runtime.

## Dev mode

`kbs view --dev` and `kbs console --dev` read the untracked framework-repo
`.env`:

```dotenv
KBS_DEV_VIEWER="node scripts/dev-server.mjs viewer/design"
KBS_DEV_CONSOLE="node scripts/dev-server.mjs viewer/console"
```

Each command runs from the `.env` directory and must print its port as the first
line. `kbs` reads that port, waits for the server, and serves the snapshot and
API itself. The proxy binds `127.0.0.1:8000`, or the next free port in
`8001–8010`. HTTP and the Next HMR WebSocket are proxied.

One dev server runs per app and is shared by every `kbs` session in the
checkout. The first session starts it; later sessions print the same port. When
the last session exits, the shared server stops. Stop it manually with:

```console
node scripts/dev-server.mjs stop viewer/design
node scripts/dev-server.mjs stop
```
