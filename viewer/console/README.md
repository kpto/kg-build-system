# Console

The notebook console Next app. It renders the project catalog, the design viewer
and the iteration timeline, and talks to the Python notebook API.

## Develop

The three dev processes choose their own ports and publish roles under the
per-user dev directory. No `--port` is needed:

```console
cd viewer
npm install

# 1. the project API
kbs console --api-only --project /path/to/project

# 2. the design viewer
cd viewer/design && npm run dev

# 3. this console
cd viewer/console && npm run dev
```

Open the console URL printed by step 3. The console rewrites `/api/*` to the API
role and embeds the viewer role with `?embed=1`; snapshots are pushed over
`postMessage`.

`--port` is optional on each launcher; `--force` replaces a healthy existing
instance. `KBS_DEV_DIR` overrides the per-user role directory.

To open the dev console from another host, bind the API, viewer and console
beyond loopback and name that host as a development origin:

```console
# API
kbs console --api-only --project /path/to/project --host 0.0.0.0

# viewer, then console, from each directory
npm run dev -- --hostname 0.0.0.0

# viewer and console: admit the host that the browser uses
KBS_DEV_ORIGINS=127.0.0.1,localhost,<host> npm run dev -- --hostname 0.0.0.0
```

`KBS_DEV_ORIGINS` is a comma-separated list of development origins; it defaults
to `127.0.0.1,localhost`. It applies to the viewer and the console. Next
rejects data requests from an unlisted host even when the server binds
`0.0.0.0`.

## Scope

- the shell and tab rail;
- the Viewer tab and its snapshot bridge;
- the Iteration tab as a lane graph of typed events;
- Revisions, Eval designs, Eval runs, Results, Findings, Proposals and Designs
  catalog tabs, with linked navigation;
- the shared `@kbs/design` tokens and primitives.

The console identity lives at the bottom of the rail, not in a top banner.

## Build

```console
cd viewer
npm ci
npm run build:static --workspace console
```

The static export is built with `basePath=/console`. `kbs console` serves it at
`/console/`, its API at `/console/api/*`, and the design viewer export at `/` on
the same available port. The wheel build runs this automatically.
