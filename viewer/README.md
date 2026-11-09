# KG Audit viewer

The viewer is the review surface for a `kg-build-system` blueprint and workflow
contract. It is a Next.js application that reads a compile-time viewer snapshot;
it does not import the Python framework at runtime, execute a build or call a
model.

The app is a VS Code-style workbench with the Blender dark theme. It has four
functions:

| Function | Purpose |
| --- | --- |
| **Proof** | multi-level value provenance: asset → relation/projection → field → binding → post-processing → target, with attached semantics and a type/presence chain |
| **Audit** | identity/key audit, grounding, semantics presence and type/presence findings, with evidence pointers and review state |
| **Semantics** | graph purpose, claims, frames and limitations, the semantic ledger, decisions and sign-off readiness |
| **Topology** | D3 force-directed orientation graph with zoom/pan/drag, filters and selection |

The workbench shell owns the snapshot, the review sidecar, the activity switch
and a stable per-function layout. Each function owns its sidebar, editor and
bottom-panel bodies. Sidebar width, bottom-panel height/tab, open tabs and
selection are persisted per snapshot + activity in `localStorage`; switching
functions restores the previous arrangement.

## Run

```console
cd viewer
npm install
npm run dev -- --hostname 0.0.0.0
```

Open <http://127.0.0.1:3000>. For a production build:

```console
npm run build
npx next start --hostname 0.0.0.0 --port 3000
```

## Snapshot

The default snapshot is the current Open Targets 26.09 **compile-only** build:

| Artifact | Value |
| --- | --- |
| Blueprint | 63 nodes, 163 edges, 61 relations, 9 projections, 239 bindings |
| Workflow | 998 steps, 1,419 connections |
| Semantics | graph purpose, 5 frames, 9 claims; semantics on every node, edge, property and binding |
| Mode | compile-only; the graph was not executed |

`viewer/public/data/opentargets.snapshot.json` is checked in (the `.gz` copy is
served through `/api/snapshot`). Regenerate it from the Open Targets project:

```console
cd ~/Repos/opentargets-kg
uv run python ~/Repos/kg-build-system/viewer/scripts/compile_opentargets_snapshot.py \
  --project . \
  --output ~/Repos/kg-build-system/viewer/public/data/opentargets.snapshot.json \
  --review-output /tmp/opentargets.review.json
```

The review sidecar is optional. `viewer/public/data/opentargets.review.json`
carries accepted decisions from a previous review; the Semantics function keeps
local decisions and approvals in `localStorage` and exports a JSON sidecar.

## Verification

```console
npm test
npm run build
npx tsc --noEmit
```

Headless browser screenshots use Selenium + the system Firefox:

```console
uv run --with selenium python scripts/screenshot.py \
  --url http://127.0.0.1:3000/ \
  --output /tmp/opentargets-viewer.png \
  --width 1600 --height 1000

uv run --with selenium python scripts/acceptance_redesign.py \
  --url http://127.0.0.1:3000/ --output /tmp/opentargets-acceptance
```

`acceptance_redesign.py` captures every activity, checks the D3 topology has
nodes and links, and verifies that resizing Proof and switching away/back keeps
its sidebar width and bottom-panel height stable.

## Layout

```
viewer/
  app/                 shell entry and global theme
  workbench/           VS Code layout, state, persistence, UI chrome
  proof/               Proof model and view
  audit/               Audit engine view and filters
  semantics/           semantic ledger, decisions, sign-off
  topology/            D3 force model and view
  lib/                 snapshot types, loader, indexes, shared models
  scripts/             snapshot regeneration and browser acceptance
  public/data/         checked-in snapshots and review sidecar
  tests/               model and contract tests
```

Design decisions and the feature cut are in [REDESIGN.md](REDESIGN.md).
