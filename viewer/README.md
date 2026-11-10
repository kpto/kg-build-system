# KG design viewer

A pure visualisation of a `kg-build-system` graph design. The viewer reads a
compile-time snapshot whose workflow plan carries its source blueprint document;
it does not import the Python framework at runtime, execute a build or call a
model.

The app is a VS Code-style workbench with the Blender dark theme. It has one
frame, one document tab strip, and two collapsible side-bar sections:

| Side-bar section | What it is for |
| --- | --- |
| **Control** | Controls for the active view: graph filters, labels, containment, semantics, legend and layout; workflow component and instruction filters. |
| **Explorer** | Everything in the design: assets, tables, projections, nodes, abstract categories, edges and their properties, plus the workflow components and step catalogue. Right-clicking an item jumps to its Graph or Workflow view; a table or projection opens its owning asset and focuses that item. |

The title-bar folder button opens another workflow or snapshot JSON file. The
workbench frame stays; the loaded artifact and its indexes are replaced. An
invalid file is reported in place and leaves the current artifact intact.

The tab strip is the document axis:

- **Graph** — the canonical graph view, pinned;
- **Workflow** — the compiled workflow plan, pinned;
- **Subject documents** — a node, edge, property, asset or abstract category.
  A single click in the Explorer tree or a context-menu action opens or reuses a
  preview tab; a double click, **Open Detail**, a right-click **Go to Detail**
  or the command palette opens a permanent tab.

There is no mode switch. Control and Explorer are side-bar sections, both may be
expanded at once, and their separator is adjustable. The Control body shows the
controls of the active view; a subject document has none. Opening or resizing a
section changes the side bar, not the active document or its editor.

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
| Graph document | graph canvas and floating **Inspect** window showing graph purpose and counts | selecting an entity fills Inspect with its description, properties and meaning; clicking empty space returns to graph purpose |
| Workflow document | compositor-style component graph with step counts and aggregated connections; no title banner, actions in a floating canvas toolbar; drag to pan, wheel to zoom, Fit to reset | filter by component or instruction kind in Control; click a component to select it, then use **Open step group** to enter its step-level flow graph with columns filling top-to-bottom; clicking a step node selects it, **Open step** opens its detail document, and **Back** returns to components. Selecting a component, step or boundary node highlights its incident links and dims the other nodes and links; entering another step group requires **Open step group** |
| Subject document | provenance assets, tables and projections first for node, edge and property documents; each reference opens its owning asset at the named item, and the effective licence follows those assets; a narrowed workflow graph follows, then meaning, properties and attached semantics | property rows, the branch selector and the Explorer tree for another subject document |

There is no bottom panel. The side bar carries the **Control** and **Explorer**
sections; the Graph document owns its floating **Inspect** window. A tab changes
its editor and, in Control, the controls applicable to that view. It never
opens, closes or switches a side-bar section. Side-bar width and the section
split are one workbench geometry.

Single-clicking a node or a property in the Graph inspector only changes the
transient inspection; it does not open a tab. Right-click any suitable node,
edge or property and choose **Go to Detail** to open its document.

The editor is one global tab strip. The viewer has three kinds of tab view:

- **Graph** — the pinned canonical graph document;
- **Workflow** — the pinned compiled workflow plan;
- **Subject documents** — a node, edge, property, asset or abstract category,
  opened explicitly from **Open Detail**, the Explorer tree, a Detail property
  row, or the command palette;
- **Step documents** — one workflow step, opened from the workflow section of Explorer.

Single-clicking a node or a property row only changes the transient **Inspect**
selection; it does not open a tab. Explorer rows single-click into a reusable
preview tab and double-click into a permanent tab. Right-clicking an Explorer
item offers **Go to Graph** for graph subjects and **Go to Workflow** for
workflow components and steps. A workflow component selected in Control or in
the Workflow graph expands its step group in Explorer; an explicit collapse sticks until the active subject changes. **Middle-click** closes a
subject or step tab; the pinned Graph and Workflow tabs cannot be closed. **Back** and
**Forward** (arrows in the tab strip, `Alt+←` / `Alt+→`, or the mouse
back/forward buttons) walk the document history. Every open tab keeps its own
editor state and scroll position. There is no JSON/Data tab.

## Snapshot

The default snapshot is the current Open Targets 26.09 **compile-only** build:

| Artifact | Value |
| --- | --- |
| Blueprint | 63 nodes, 163 edges, 61 relations, 9 projections, 239 bindings |
| Workflow | 998 steps, 1,419 connections |
| Meaning | graph purpose, 5 frames, 9 claims; semantics on every node, edge, property and binding |
| Mode | compile-only; the graph was not executed |

`viewer/public/data/opentargets.snapshot.json` is checked in (the `.gz` copy is
served through `/api/snapshot`). The snapshot contains only the workflow plan;
its `provenance.blueprint` member is the source blueprint, so no second artifact
is needed. Regenerate it from the Open Targets project:

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
  workflow/            compiled workflow plan: compositor graph and step detail
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
