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
| **Explorer** | Everything in the design: assets, tables, projections, nodes, abstract categories, edges and their properties, plus the workflow components and step catalogue. Right-clicking an item jumps to its Graph or Workflow view; tables and projections open their own documents. |

The viewer opens the snapshot named by the URL (`?snapshot=reference` selects the
reference estate); there is no file picker. The workbench frame and its indexes
are built for that snapshot.

The tab strip is the document axis:

- **Graph** — the canonical graph view, pinned;
- **Workflow** — the compiled workflow plan, pinned;
- **Subject documents** — a node, edge, property, asset or abstract category.
  A single click in the Explorer tree or a context-menu action opens or reuses a
  preview tab; a double click, **Open Detail**, a right-click **Go to Detail**
  or the command palette opens a permanent tab.

There is no mode switch. Control and Explorer are side-bar sections, both open
by default at a 50/50 split, and their separator is adjustable. The Control body
shows the controls of the active view; a subject document has none. Opening or resizing a
section changes the side bar, not the active document or its editor.

The viewer is a design reader, not an audit or review tool: there are no
findings, decisions, coverage, sign-off or review sidecars.

## Run from a project

A published `kg-build-system` wheel bundles the compiled viewer. Run it from the
project root:

```console
uv run kbs view
```

The command reads `build/workflow_plan.json` by default. It opens the browser and
serves the project’s own design at <http://127.0.0.1:8001/>. It never falls back
to a bundled demo.

```console
kbs view --snapshot path/to/workflow_plan.json
kbs view --snapshot path/to/reference.snapshot.json --port 8002
kbs view --no-open
```

The snapshot may be a workflow plan, a blueprint, a viewer snapshot, or gzip of
one. A bare workflow plan is wrapped with the current directory as its title.

When `kbs view` runs from a source checkout, it also writes a minimal discovery
file while it is running:

```text
<project>/.kbs/viewer.json
{"api": "http://127.0.0.1:8001"}
```

The file is removed on exit. A wheel has no source viewer, so it never writes
one.

## Develop the viewer

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

## Develop against a project

Start the project API with `kbs view` from the project root, then start Next dev
against its discovery file:

```console
# terminal 1, in the project
uv run kbs view --snapshot build/workflow_plan.json

# terminal 2
cd viewer
npm run dev:discovery -- --discovery /abs/project/.kbs/viewer.json --port 3001
```

or:

```console
KBS_DISCOVERY=/abs/project/.kbs/viewer.json npm run dev
```

Next reads the discovery file once at startup and hard-codes the API origin. It
proxies `/snapshot` and `/api/*` to that server. Restart Next if the Python
server moves to another port.

Run one Next dev instance per project. Each project discovers its own API from
its own `.kbs/viewer.json`.

## Bundle in the Python wheel

`hatch_build.py` compiles the viewer during a wheel build:

```text
npm ci
npm run build:static
viewer/out -> kg_build_system/viewer_dist
```

`kbs view` serves `kg_build_system/viewer_dist`; Node is not required at runtime.
Node and network access are required at build time. For a local wheel build with
an existing `viewer/out`:

```console
KBS_SKIP_VIEWER_BUILD=1 uv build --wheel
```

`KBS_SKIP_VIEWER_INSTALL=1` reuses `viewer/node_modules`. `KBS_NPM` selects an npm
executable. The wheel excludes `viewer/out/data`; project snapshots are served by
`kbs view`, not bundled into the package.

## Low detail first

The first paint shows the design, not its annotations.

| Surface | Default | Revealed by |
| --- | --- | --- |
| Graph document | Blender-node-editor canvas with a dot and major grid, degree-sized nodes tinted by category, faint category hulls and hub labels; the shared visualisation header states visible nodes and links, carries the **Inspect** toggle and opens a floating inspector showing graph purpose and counts | selecting an entity fills Inspect with its description, properties, meaning and the fulfilment map; clicking empty space returns to graph purpose; **Clusters**, **Labels** and **Show** in Control reveal the other layers |
| Workflow document | compositor-style component graph in the shared visualisation frame; its header names the workflow or focused step group and states component or step counts, with step-group actions on the right; drag to pan, wheel to zoom, Fit in the bottom-left navigation cluster resets | filter by component or instruction kind in Control; click a component to select it, then use **Open step group** to enter its step-level flow graph with one block per dependency layer; a large layer wraps into aligned sub-columns and chains read left to right; clicking a step node selects it, **Open step** opens its detail document, and **Back** returns to components. Selecting a component, step or boundary node highlights its incident links and dims the other nodes and links; entering another step group requires **Open step group** |
| Subject document | one stack of bands in the shared order: Overview, Meaning, Fulfilment (the axis map), Sources, Build steps, Expression, Members, Connections, Bindings; the effective licence sits in the header | a section header collapses its band; property rows and the branch selector open their own documents; the Explorer tree opens another subject document |
| Relation document | the same bands; Overview states kind, asset, columns, row source, scans, bindings and licence; Meaning, Fulfilment, Sources, Build steps, Expression, Members and Bindings follow | a column definition, the expression outline and the fulfilment map's full axis view |
| Step document | the same bands; Overview, Meaning and Sources state what a step is and what it is not, then Ports, Payload, Connections and Bindings | a port, a payload field or a connected step |

Every item document follows the content contract in
[`DETAIL_CONTENT.md`](./DETAIL_CONTENT.md); its skin is in
[`DESIGN_BLENDER.md`](./DESIGN_BLENDER.md).

There is no bottom panel. The side bar carries the **Control** and **Explorer**
sections; the Graph document owns its flat **Inspect** panel. A tab changes
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
  detail/              the shared detail contract: bands, axis map and expression
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
