# KG Studio — Architecture

KG Studio is a visual authoring front end for `kg_build_system`. It edits one JSON
**project IR document**, generates a complete Python KG project from it, and maps
type errors and compilation problems back onto the IR so the UI can highlight the
offending component.

It lives entirely under `studio/` and treats `kg_build_system` as an imported
library. The framework is not modified: studio reuses its public authoring API,
its type and expression IR codecs, and its `create_blueprint` / `compile` entry
points.

```
                      ┌──────────────────────────────────────────────┐
   browser  ──────►   │  Next.js frontend                            │
                      │  tabs: topology · contracts · projections ·  │
                      │        bindings · sources · modules · plan   │
                      │  + inspector, problems panel, live status    │
                      └───────────────▲──────────────┬───────────────┘
                                      │ REST + WS    │ PATCH (IR ops)
                      ┌───────────────┴──────────────▼───────────────┐
                      │  FastAPI backend (studio_backend)            │
                      │                                              │
                      │  ir.store      project.ir.json (source of    │
                      │                  truth, atomic writes,       │
                      │                  monotonically increasing    │
                      │                  revision)                   │
                      │    │                                         │
                      │    ├─ ir.index       derived type/slot index │
                      │    ├─ generate.*    IR → whole Python project│
                      │    │                 + anchors.json (symbol  │
                      │    │                 index: file:line → IR)  │
                      │    ├─ pyright client pyright-langserver      │
                      │    │                  (--stdio LSP) →        │
                      │    │                  diagnostics → IR refs  │
                      │    ├─ blueprint      kg_build_system.compile │
                      │    │                  (namespace_path=…) →   │
                      │    │                  validation errors +    │
                      │    │                  workflow step graph    │
                      │    └─ watcher        IR/data file changes →  │
                      │                       regenerate → republish │
                      └──────────────────────────────────────────────┘
                                      │
                                      ▼
                       studio_test_project/   (fully generated)
```

## 1. The IR document is the source of truth

`project.ir.json` describes the whole KG project: logical tables and structs,
projections, topology components, graph bindings, physical sources and the
configured workflow modules. Everything the UI shows is read from it; every UI
edit is a patch to it. Generated Python is a build artifact and is never parsed
back into the document.

This is deliberately **not** the framework blueprint. A blueprint is compiled
*output* of Python authoring, so using it as the editable model would be circular
(code would have to exist before it could be edited). The IR document is the
*authoring* state that precedes code.

Two pieces of the document reuse framework IR shapes verbatim, validated through
the framework's own codecs (`kg_build_system.types.ir_codec`,
`kg_build_system.expressions.ir_codec`):

- **logical types** — `{"kind": "unit" | "nullable" | "array" | "struct" | "custom", …}`
- **expressions** — `{"kind": "literal" | "field" | "operation", …}` trees

Consequence: an expression composed in the UI is the same tree the framework would
produce by compiling hand-written authoring code, which is what makes the generator
and the round-trip check tractable.

`logical_type` on an IR expression node is **derived, never authored**. The backend
computes it (`ir.infer`) and overwrites whatever the client sent, so a stale or
wrong type cannot enter the document. The generator emits Python for the operation
chain; the authoritative type is whatever `create_blueprint` computes from that
Python.

### References

Every editable thing has a stable id, and `refs` address it:

```
<table|struct|projection|component|binding|source|module>:<id>[.<part>[.<name>]]

component:site                     the whole node component
component:site.property.summary    one property slot
binding:site_binding.property.summary   the expression filling that slot
table:sites.field.site_id          one field
```

Ids are snake_case and are the authoring identity; they are also what the
component's declaration name is derived from (`site` → `SiteNode`). Deleting and
re-adding a component therefore reuses an id only when the id is free.

## 2. Generation

`generate.project.write_project(document, project_root)` renders the whole project:

| path | contents |
| --- | --- |
| `<pkg>/table/<table>/__init__.py` | one generated data contract package per table/group |
| `<pkg>/table/projections/<projection>.py` | projections |
| `<pkg>/topology/common.py` | templates and categories shared across node packages |
| `<pkg>/topology/<node>/__init__.py` | the node component |
| `<pkg>/topology/<node>/<predicate>__<destination>.py` | an edge component |
| `<pkg>/bindings/common.py` | shared property stamps |
| `<pkg>/bindings/<node>/…` | node and edge bindings, mirroring `topology/` |
| `<pkg>/sources.py` | `bind_source` per physical source |
| `<pkg>/build.py` | composition entry point with the configured modules |

The layout follows the framework's node-first convention (`KG_BUILD_SYSTEM_SPEC.md`
§14) so generated projects are indistinguishable in shape from `reference_project`,
and data files under `<project>/data/` are inputs the studio never owns.

### Why the generator is studio-owned, not a framework provider

The stated intent was "a new independent provider generating project code from an
IR document". The framework's provider contract cannot express that: a provider
returns a `GeneratedPackage`, whose model only renders `Table`, `Struct` and
`TableGroup` declarations into a single product package, and whose discovery model
is one request assignment inside a package `__init__.py`. A studio project must
also emit topology, bindings, sources and `build.py`, across many packages, with
one owner.

So studio keeps the *behaviours* that make the framework's generator safe, and owns
the model:

- deterministic rendering (byte-identical for the same document);
- a `.kg-studio.json` manifest recording the document fingerprint and the hash of
  every owned file, so nothing unowned is ever overwritten and stale files are
  pruned;
- atomic replacement and `__pycache__` hygiene;
- every rendered file is parsed with `libcst` before anything is written, so a
  rendering bug fails as one error instead of a broken project;
- a `# Generated by kg-studio. Do not edit manually.` header plus the IR ref it
  came from, on every declaration.

The framework's own `InferDataContractProvider` is still used where it fits: the
studio "import data shape" action runs it over a data file and folds the resulting
`GeneratedPackage` into the IR document as tables and fields.

### Anchors

Writing the project also produces `studio/backend/…/anchors.json` (kept outside the
generated project): for each owned file, the line/column range of every declaration
and expression, paired with the IR ref that produced it. It is built by walking the
rendered source with `libcst`, so it describes the code as it actually is rather
than what the renderer intended. `file:line:col` from any tool resolves through it
to an IR ref by innermost containing range.

## 3. Diagnostics

`pyright-langserver --stdio` is started once per workspace as a real LSP client
(JSON-RPC over stdio). It is the only type checker; studio does not re-implement
Python typing.

- All owned project files are `didOpen`ed; on regeneration the affected buffers are
  closed and reopened, so pyright re-reads from disk.
- `textDocument/publishDiagnostics` is collected per file.
- Each diagnostic is resolved through the anchor index to an IR ref, and grouped:
  per-ref for inline badges in the editors, per-file for the problems list.
- A diagnostic with no anchor (e.g. an import line) maps to its file's owner ref.

Two further sources feed the same problem model:

- **blueprint validation** — `create_blueprint(namespace_path=…)` raises
  `ValueError` for framework-level violations (bad build key, label collision,
  endpoint descent, missing source). The message names logical/declaration names,
  which resolve to IR refs through the derived index.
- **build execution** — on demand, `build()` runs the compiled contract; step
  failures surface against the component or source that produced them.

Status is therefore three-tiered and each tier is labelled as such in the UI:
`types` (pyright), `blueprint` (framework validation), `build` (execution).

## 4. The plan view

`compile(namespace_path=…)` returns a `WorkflowContractIR` whose `steps` and
`connections` are exactly the runtime DAG. The backend projects that into a
positioned graph (module → lane, topological layer → column, elkjs layout
server-side is unnecessary — the frontend lays out) and the UI draws it as a
compositor: one node per step with input sockets on the left, output sockets on
the right, bezier links between slots, coloured by module, with the step payload
(SQL, export target, aggregation) inspectable per node. Raw SQL in a payload is
selectable text, because inspecting lowered SQL is a primary use of this view.

## 5. Frontend

Next.js (app router) + TypeScript + Zustand + Tailwind. `@xyflow/react` for the
plan view, `d3-force` for the topology graph, `@dnd-kit` for ordered stacks.

Principle: **visual first**. Free text is allowed only where text *is* the value
(names, descriptions, literal values, JSON annotation arguments). Structure is
always composed by picking:

- **Topology** — the metagraph, drawn as a force-directed node-link graph in the
  same visual language as the `meta_graph.html` the framework itself emits, and
  for the same reason: `d3-force` computes positions, React owns the SVG. Node
  components are circles (filled for a concrete node, dashed ring for a
  category), edge components are diamonds sitting *between* the two nodes they
  join. Drawing a relationship as a node rather than a line is what makes it
  possible to show that `studied_in` and `reported_for` are both kinds of
  `related` — an edge drawn as a line can never be the endpoint of an is-a link,
  so the framework's own viewer cannot show that either. Drag to place (written
  to `views/topology`); shift-drag node→node to invent a relationship, or
  node→relationship to wire that endpoint. Slot counts ride inside the shape,
  problem badges beside it.
  - Templates are deliberately **not** on this canvas. A template reaches no
    blueprint, so the framework's own metagraph contains none; they are listed
    in a library strip with their contributing slot count and how many
    components mix them in, which is also how an unused one becomes visible.
    They edit in the same inspector — except for endpoints, which the generator
    ignores for that tier, so offering them would be a control that changes
    nothing.
  - The layout is a view, not data: it recomputes only when the vertex/link
    *set* changes, so editing a description never moves the graph, and only a
    deliberate drag is persisted. "Reset layout" re-settles from the structure
    alone and persists the result.
- **Bindings** — an expression is a vertical **stack** of blocks: a source block
  (table/projection + field path), then navigation blocks (`pick`, `expand`,
  `map_items`), then effect blocks (`where_present`, `keep_if`, `default_to`), then
  calculation blocks (`prepend`, `add`, `split_after`, `sorted`, `join`, …). Each
  block only offers operations valid for the type its predecessor produced, and each
  shows its resulting type on the seam. That validity filter is the whole point of
  the stack, and it comes from `ir.index` + `ir.infer` on the backend, so the UI can
  never compose something the framework would reject.
- **Contracts** — a field table with type-drag targets and nested struct drill-in,
  not JSON editing.
- **Sources / Modules** — pickers over discovered data files and the framework's
  registered modules.
- **Plan** — §4.

State: one Zustand store per bounded context (`document`, `selection`, `diagnostics`,
`plan`, `connection`), with the document store applying patches optimistically and
reconciling against the backend revision. Every mutation is an IR patch, so the
document can also be edited by hand or by script and the UI follows it.

## 6. Process model

`studio serve --project <dir> [--frontend-dev]` starts:

1. the IR store + workspace (single writer, revision-numbered),
2. the file watcher on `project.ir.json` and `data/`,
3. the pyright language server,
4. FastAPI on `:8700` (REST `/api/…`, `/ws` for events).

The Next.js dev server runs separately on `:3000` in development and is a static
export served by the backend in production mode. WS carries
`document`, `generated`, `diagnostics`, `blueprint`, `plan` and `log` events; the
client resyncs by revision on reconnect, so a dropped socket cannot desync state.

## 7. Framework impact

None. No file under `kg_build_system/` changes. Studio depends on it as a library
and on two of its guarantees: the authoring API is a stable surface (it is the
render target), and `compile(namespace_path=…)` works on an arbitrary importable
project (verified against `reference_project`).
