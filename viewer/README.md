# KG design viewer

A pure visualisation of a `kg-build-system` graph design. The viewer reads a
compile-time snapshot whose workflow plan carries its source blueprint document;
it does not import the Python framework at runtime, execute a build or call a
model.

The app is a VS Code-style workbench with the Blender dark theme. It has one
frame, one document tab strip, and two collapsible side-bar sections:

| Side-bar section | What it is for |
| --- | --- |
| **Control** | Controls for the active view: graph filters, labels, containment, meaning, legend and layout; workflow component and instruction filters. |
| **Explorer** | Everything in the design: assets, source relations, derived relations, nodes, abstract categories, edges and their properties, bindings, plus the workflow components and step catalogue. Right-clicking an item jumps to its Graph or Workflow view; records, relations and bindings open their own documents. |

The viewer reads the snapshot from its configured `/snapshot` source, or from a
URL passed as `?snapshot=<url>`; there is no bundled project dataset and no file
picker. The workbench frame and its indexes are built for that snapshot.

The tab strip is the document axis:

- **Graph** — the canonical graph view, pinned;
- **Workflow** — the compiled workflow plan, pinned;
- **Subject documents** — a node, edge, property, asset, abstract category,
  source relation, derived relation or binding. A single click in the Explorer
  tree or a context-menu action opens or reuses a preview tab; a double click,
  **Open Detail**, a right-click **Go to Detail** or the command palette opens
  a permanent tab.

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
kbs view --snapshot path/to/snapshot.json --port 8002
kbs view --no-open
```

The snapshot may be a workflow plan, a blueprint, a viewer snapshot, or gzip of
one. A bare workflow plan is wrapped with the current directory as its title.

`kbs view` serves the bundled viewer directly; it does not start Next. With
`--dev` it also writes a minimal discovery file while it is running:

```text
<project>/.kbs/viewer.json
{"api": "http://127.0.0.1:8001"}
```

The file is restored to its previous value on exit, or removed if there was
none. A separately started Next dev sidecar reads it to discover the snapshot
API. Without `--dev`, no discovery file is written.

## Embedding

`kbs view --embed` serves the bundled viewer without a project snapshot and
prints a URL with `?embed=1`. The host frames that URL and supplies each document over
the message bridge; the viewer does not fetch project data in this mode.

Host to viewer:

```js
{
  type: "open",
  snapshot: <viewer snapshot, workflow plan or blueprint>,
  requestId?: "optional correlation id"
}
```

`snapshot` may be a parsed object or raw JSON text. The viewer replaces the
current workbench on every `open`.

Viewer to host:

```js
{ type: "ready", snapshot?: "loaded-snapshot-name" }
{ type: "select", subject: { kind, name, component?, property?, ... } }
{ type: "error", message }   // only for a malformed open payload
```

`ready` is posted once per mount, after the message listener exists. Selection
events use the workbench `SubjectSelection` shape. The host validates the
message origin and source; the viewer posts to the referrer origin when the
browser exposes one, otherwise to `*` (an embedding host should therefore use a
restrictive referrer policy or validate origin and source itself).

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

Start the project API with `kbs view --dev` from the project root, then start
Next dev against its discovery file:

```console
# terminal 1, in the project
uv run kbs view --dev --no-open --snapshot build/workflow_plan.json

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

`kbs view` serves the bundled `kg_build_system/viewer_dist` (or `viewer/out` in a
source checkout); Node is not required at runtime.
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
| Graph document | Blender-node-editor canvas with a dot and major grid, degree-sized nodes tinted by category, faint category hulls and hub labels; the shared visualisation header states visible nodes and links, carries the **Inspect** toggle and opens a floating inspector showing graph purpose and counts | selecting an entity fills Inspect with its meaning, properties and the fulfilment map; clicking empty space returns to graph purpose; **Clusters**, **Labels** and **Show** in Control reveal the other layers |
| Workflow document | compositor-style component graph in the shared visualisation frame; its header names the workflow or focused step group and states component or step counts, with step-group actions on the right; drag to pan, wheel to zoom, Fit in the bottom-left navigation cluster resets | filter by component or instruction kind in Control; click a component to select it, then use **Open step group** to enter its step-level flow graph with one block per dependency layer; a large layer wraps into aligned sub-columns and chains read left to right; clicking a step node selects it, **Open step** opens its detail document, and **Back** returns to components. Selecting a component, step or boundary node highlights its incident links and dims the other nodes and links; entering another step group requires **Open step group** |
| Subject document | one banner overview and one horizontal deck of flat cards: Meaning, Constitution (one DAG: the subject's purpose, one fulfilment per binding, graph ancestry and relation provenance, each axis in a labelled frame; shared declarations once; opens fitted, pan/zoom), Members, Connections and Bindings; the effective licence sits in the header | the left index rail navigates the static cards; each card fills the deck height and the next card peeks; property rows, the branch selector and binding pills open their own documents; the Explorer tree opens another subject document |
| Relation document | the same banner and card deck; the banner states asset, grain, identity, row source and licence; Meaning, Constitution, Members and Bindings follow. The Constitution is the relation's purpose over its asset (source) or its scanned sources and their assets (derived) | a column definition, a binding pill and the Constitution DAG |
| Asset document | the same banner and card deck; Meaning, Members, Fields and Bindings follow. The asset is the origin, so it has no Constitution card | a relation row, a field row or a binding pill |
| Binding document | its own banner states record, writes, identity, rows read, step and output; Meaning (when the binding carries one), Constitution, Expression and Build steps follow | the Explorer Bindings group, a record's Bindings table or a binding pill in the fulfilment map |
| Step document | the same banner and card deck; the banner states step id, component, instruction, bindings and ports; Ports, Payload, Connections, Bindings and the Meaning/Sources absence notes follow | a port, a payload field or a connected step |

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
- **Subject documents** — a node, edge, property, asset, abstract category,
  source relation, derived relation or binding, opened explicitly from **Open
  Detail**, the Explorer tree, a binding pill, a Detail property row, or the
  command palette;
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

## Snapshot source

The viewer does not bundle a project snapshot. It reads `/snapshot` from the
configured discovery endpoint, or a plain/gzip JSON URL passed as
`?snapshot=<url>`. A snapshot's `provenance.blueprint` member carries the source
blueprint, so no second artifact is needed.

The blueprint document follows the current model: `graph_declaration.meaning`,
topology `meaning`, `data.source_relations` and `data.derived_relations`,
column `definition` and `meaning`, and binding `name`/`mode`/`meaning`.
The loader still reads the legacy keys (`relations`, `projections`,
`semantics`, `description`, `debug_name`) so older snapshots remain viewable;
display text prefers purpose, claim, contract definition and field definition
over the retired description field.

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
  --output /tmp/viewer-topology.png \
  --width 1600 --height 1000
```

## Layout

```
viewer/
  app/                 shell entry, route handlers and global theme
  workbench/           VS Code layout, state, persistence, UI chrome
  topology/            canonical design graph, detail controls and view
  workflow/            compiled workflow plan: compositor graph and step detail
  detail/              the detail contract: bands, constitution, concept pills and expression
  proof/               the provenance model used by Detail
  shared/design/       meaning model and its renderer
  shared/ui/           generic primitives, concept marks, viewport and menus
  lib/                 snapshot types, loader, indexes, shared models
  scripts/             snapshot regeneration and browser screenshots
  public/data/         checked-in snapshots
  tests/               model and contract tests
```

Design decisions and removed surfaces are in [HIERARCHY.md](HIERARCHY.md); the
visual rules are in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) and
[DESIGN_BLENDER.md](DESIGN_BLENDER.md).
