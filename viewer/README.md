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

## Start the dev stack

Run each process in its own terminal, starting from the repository root:

```console
# 1. the project API
kbs console --api-only --project /path/to/project

# 2. the design viewer
cd viewer/design && npm run dev

# 3. the console
cd viewer/console && npm run dev
```

Each launcher chooses an available port and publishes a role under the per-user
dev directory. Open the console URL printed by step 3; it embeds the viewer. See
`design/README.md` and `console/README.md` for `KBS_DEV_DIR`, `--force` and
remote development origins.
