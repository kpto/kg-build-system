# KG design viewer

A pure visualisation of a `kg-build-system` graph design. The viewer reads a
compile-time viewer snapshot of a blueprint and workflow contract; it does not
import the Python framework at runtime, execute a build or call a model.

The app is a VS Code-style workbench with the Blender dark theme. It has three
functions, in reading order:

| Function | Question it answers |
| --- | --- |
| **Topology** | What exists in the graph, and how is it connected? |
| **Proof** | Where does one value come from, and what does it pass through? |
| **Meaning** | What does the graph claim, and within which frames and limits? |

Topology is the first and default surface. The viewer is a design reader, not
an audit or review tool: there are no findings, decisions, coverage, sign-off or
review sidecars.

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

## Low detail first

The first paint shows the design, not its annotations.

| Surface | Default | Revealed by |
| --- | --- | --- |
| Topology | circles, thin relation links, labels on hubs only | the sidebar **Detail** controls: labels off/hubs/all, edge labels, containment, semantics, properties |
| Proof | the selected property's lanes and type chain | the level switch (Property, Node, Edge, Abstract, Asset) and the branch selector |
| Meaning | graph purpose and counts | **Show claims**, **Expand frames**, **Show limitations**, **Show subjects** |

The bottom panel starts hidden. Open it with the title-bar panel toggle or
`Cmd/Ctrl+J`. It shows selection detail only; there is no JSON/Data tab.

## Snapshot

The default snapshot is the current Open Targets 26.09 **compile-only** build:

| Artifact | Value |
| --- | --- |
| Blueprint | 63 nodes, 163 edges, 61 relations, 9 projections, 239 bindings |
| Workflow | 998 steps, 1,419 connections |
| Meaning | graph purpose, 5 frames, 9 claims; semantics on every node, edge, property and binding |
| Mode | compile-only; the graph was not executed |

`viewer/public/data/opentargets.snapshot.json` is checked in (the `.gz` copy is
served through `/api/snapshot`). Regenerate it from the Open Targets project:

```console
cd ~/Repos/opentargets-kg
uv run python ~/Repos/kg-build-system/viewer/scripts/compile_opentargets_snapshot.py \
  --project . \
  --output ~/Repos/kg-build-system/viewer/public/data/opentargets.snapshot.json
```

The reference estate is available at `?snapshot=reference`; it is not the
default dataset.

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
  --output /tmp/opentargets-topology.png \
  --width 1600 --height 1000
```

## Layout

```
viewer/
  app/                 shell entry, route handlers and global theme
  workbench/           VS Code layout, state, persistence, UI chrome
  topology/            D3 force model, detail controls and view
  proof/               proof model and view
  meaning/             purpose, frames, claims and attached semantics
  lib/                 snapshot types, loader, indexes, shared models
  scripts/             snapshot regeneration and browser screenshots
  public/data/         checked-in snapshots
  tests/               model and contract tests
```

Design decisions and removed surfaces are in [HIERARCHY.md](HIERARCHY.md); the
visual rules are in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) and
[DESIGN_BLENDER.md](DESIGN_BLENDER.md).
