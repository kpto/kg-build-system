# Console

The notebook console Next app. It renders the project catalog, the design viewer
and the iteration timeline, and talks to the Python notebook API.

## Build and serve

The console is a static Next export with `basePath=/console`:

```console
cd viewer
npm ci
npm run build:static --workspace console
```

Serve it with the Python host:

```console
kbs console --project /path/to/project
```

`kbs console` serves the console at `/console/`, the design viewer at `/` and the
API at `/console/api/`. The Viewer tab frames the static viewer; a revision tab
adds `?snapshot=/console/api/revision-view?revision=...` and the viewer reloads
that snapshot. Node is not required at runtime.

## Scope

- the shell and tab rail;
- the Viewer tab and its static viewer frame;
- the Iteration tab as a lane graph of typed events;
- Revisions, Eval designs, Eval runs, Results, Findings, Proposals and Designs
  catalog tabs, with linked navigation;
- the shared `@kbs/design` tokens and primitives.

The console identity lives at the bottom of the rail, not in a top banner.
