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

Develop the design viewer and the console as separate Next dev servers; each
publishes a role under the per-user dev directory. See `design/README.md` and
`console/README.md`.
