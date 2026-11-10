# KG design viewer

A pure visualisation of a `kg-build-system` graph design. The viewer reads a
compile-time viewer snapshot of a blueprint and workflow contract; it does not
import the Python framework at runtime, execute a build or call a model.

The app is a VS Code-style workbench with the Blender dark theme. It has one
frame, one document tab strip, and two collapsible side-bar sections:

| Side-bar section | What it is for |
| --- | --- |
| **Topology** | Canvas controls: filters, labels, containment, semantics, legend and layout. |
| **Detail** | Graph meaning and the design tree used to open subject documents. |

The tab strip is the document axis:

- **Graph** — the canonical graph view, pinned;
- **Subject documents** — a node, edge, property, asset or abstract category
  opened explicitly from the Detail tree, **Open Detail**, a Detail property
  row or the command palette.

There is no mode switch. Topology and Detail are side-bar sections; opening one
changes the side bar, not the active document or its editor.

The viewer is a design reader, not an audit or review tool: there are no
findings, decisions, coverage, sign-off or review sidecars.

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
| Graph document | graph canvas and **Inspect** bottom panel | selecting an entity fills Inspect with its description, properties and meaning |
| Subject document | meaning, properties and attached semantics of the subject | the level switch (Property, Node, Edge, Abstract, Asset), property rows and the branch selector; the bottom panel carries Trace/Evidence |

Both panels are shown by default. The side bar carries the **Topology** and
**Detail** sections; the bottom panel is the **Inspect** or Trace/Evidence
region for the active document. Each has one job, so a selected subject is not
repeated across regions. Panel width and height are one workbench geometry:
opening either side-bar section never changes them.

The editor is one global tab strip. The viewer has two kinds of tab view:

- **Graph** — the pinned canonical graph document;
- **Subject documents** — a node, edge, property, asset or abstract category,
  opened explicitly from **Open Detail**, the Detail tree, a Detail property
  row, or the command palette.

Single-clicking a node or a property row only changes the transient **Inspect**
selection; it does not open a tab. **Back** and **Forward** (arrows in the tab
strip, or `Alt+←` / `Alt+→`) walk the document history. There is no JSON/Data
tab.

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
  topology/            canonical design graph, detail controls and view
  detail/              the merged design view: meaning, properties and provenance
  proof/               the provenance model used by Detail
  shared/design/       meaning value, graph/entity meaning, and its renderer
  lib/                 snapshot types, loader, indexes, shared models
  scripts/             snapshot regeneration and browser screenshots
  public/data/         checked-in snapshots
  tests/               model and contract tests
```

Design decisions and removed surfaces are in [HIERARCHY.md](HIERARCHY.md); the
visual rules are in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) and
[DESIGN_BLENDER.md](DESIGN_BLENDER.md).
