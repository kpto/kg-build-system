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
