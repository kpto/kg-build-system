# Vendored assets

`d3.v7.min.js` — d3 v7.9.0 UMD bundle, the full library.

- Source: `https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js`
- SHA-256: `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539`
- Licence: ISC, Copyright 2010-2023 Mike Bostock. The licence notice is the first
  line of the bundle and must be kept.

It is vendored rather than fetched from a CDN so a generated `meta_graph.html`
opens with no network: build artifacts are routinely opened later, in CI logs, or
on machines without internet access. The whole bundle is inlined into the
generated HTML so the artifact stays a single file.

To update, replace the file and refresh the version, URL and digest above.
