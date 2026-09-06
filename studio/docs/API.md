# Studio HTTP + WebSocket contract

One backend origin (default `http://127.0.0.1:8700`), CORS open to the Next dev
server. Everything is JSON. The frontend never reads files; the backend never
trusts a client-computed type.

## Concurrency model

The IR document is edited as a whole. A client `PUT`s the complete document with
the revision it last saw; the backend validates, bumps the revision, writes it, and
queues regeneration. A stale revision is rejected with `409` and the current
document, which the client adopts. Other clients learn about the change over the
WebSocket. This trades merge sophistication for a single unambiguous source of
truth — the document plus its revision.

## Endpoints

| method | path | request | response |
| --- | --- | --- | --- |
| GET | `/api/state` | — | `{document, revision, status, project_root}` |
| PUT | `/api/document` | `{revision, document}` | `200 {revision, document, problems:[document-tier only]}` · `409 {revision, document, reason}` · `422 {reason, errors:[{loc, msg}]}` |
| GET | `/api/document` | — | `{revision, document}` |
| GET | `/api/catalog` | — | `{modules:[ModuleEntry], units:[…], operators:[…], vocabulary:{…}}` |
| GET | `/api/index` | — | `AuthoringIndex` (below) |
| GET | `/api/diagnostics` | — | `{problems:[Problem], pyright:{state}}` |
| GET | `/api/plan` | `?refresh=1` | `{plan:Plan, errors:[Problem], fingerprint}` |
| GET | `/api/blueprint` | `?refresh=1` | `{blueprint, summary:{tables, components, bindings, …}, errors:[Problem]}` |
| POST | `/api/build` | `{}` | `{ok, report, artifacts, problems}` |
| GET | `/api/source` | `?ref=component:site` | `{ref, path, text, line}` — the generated code a ref produced |
| POST | `/api/names/suggest` | `{section, label}` | `{id, declaration_name, python_name, taken:bool}` |
| GET | `/api/data/files` | — | `[{location, name, format, size_bytes}]` |
| POST | `/api/infer` | `{location, mode, table?, layout?}` | `{tables:[Table], structs:[Struct], notes:[str]}` — wraps the framework's inference provider so imported shapes enter the document, not the filesystem |
| POST | `/api/workspace` | `{package, name, project_root?}` | `{revision, document}` — start a project from empty; a `project_root` that is not the served one is refused |
| WS | `/ws` | `{type:"subscribe"}` | event stream (below) |

`ProjectDocument` JSON is exactly `studio_backend.ir.document.ProjectDocument`'s
`model_dump(mode="json")`; the TypeScript mirror in `src/lib/ir.ts` must stay
field-for-field identical, and `tests/test_document.py::test_whole_project_round_trips_through_json`
is the canonical example payload.

## Authoring index (`GET /api/index`)

Everything a visual editor needs to offer only valid choices. Computed server-side
from the document, so availability and types can never disagree with the generator.

```jsonc
{
  "selectable": [                       // what an expression stack may start from
    {"kind": "table", "id": "sites", "name": "sites", "declaration_name": "SitesTable",
     "group": null,
     "paths": [                         // flattened, including nested struct members
       {"path": ["site_id"],  "logical_type": {...}, "nullable": true,  "description": null},
       {"path": ["premises","contact","location","city"], "logical_type": {...}, "nullable": true}
     ]}
  ],
  "components": [
    {"id": "site", "kind": "node", "tier": "concrete",
     "resolved_properties": [           // own + inherited, with the declaring component
       {"name": "summary", "logical_type": {...}, "optional": false, "declared_by": "documented"}
     ],
     "endpoint_is_category": {"source": false, "target": false}}
  ],
  "operators": [                         // the block palette for the stack composer
    {"operator": "where_present", "label": "Keep rows where present",
     "requires": {"shape": "nullable", "arguments": [], "parameters": []},
     "arity": 1, "group": "effect", "produces": "non_null_unwrapped",
     "produces_type_rule": "unwrap_nullable", "produces_description": "…",
     "render": "where_present", "docs": "…"}
  ]
}
```

Operators are the backend's `OPERATION_CATALOGUE` verbatim, so the palette the UI
renders cannot drift from what inference accepts. `requires` also carries the argument
and parameter shapes, and `produces_type_rule` names the rule that produced the result
type.

`operators[].requires.shape` is one of `any | nullable | non_nullable | array |
array_of_struct | struct | unit:str | unit:int | unit:float | unit:bool |
array_of_non_null_str`, and `produces` describes the resulting shape so the composer
can chain. The palette the UI renders is this array filtered against the current
stack tip — never a hardcoded list in the frontend.

## Problem model

One shape for every tier, so the UI has a single problems component.

```jsonc
{
  "id": "sha1 of tier+file+code+message",
  "tier": "types" | "blueprint" | "build" | "document",
  "severity": "error" | "warning" | "info",
  "message": "SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')",
  "code": "reportArgumentType",          // pyright rule, or framework error class
  "file": "kg_project/bindings/site/__init__.py",   // project-relative; null for tier=build
  "line": 24, "column": 18, "end_line": 24, "end_column": 41,
  "ref": "binding:site_binding.property.city",        // null when unmappable
  "ref_trusted": "anchor" | "name" | null,            // anchor = position hit, name = matched by declaration name
  "hint": "Property 'city' is declared str on component SiteNode."
}
```

`ref` resolution order: anchor index by position (`anchor`) → declaration-name lookup
in the derived index (`name`) → `null`. The UI must render `null`-ref problems in the
problems panel without pretending they belong to a component.

## Plan payload (`GET /api/plan`)

Projected from `WorkflowContractIR`, which already carries `steps`, `connections`,
`modules` and per-step `payload`. `studio_backend/plan.py` adds the presentation data
the contract deliberately does not carry: a human label, the IR reference a step
belongs to, a kind for node styling, and the payload fields worth showing inline.

```jsonc
{
  "fingerprint": "sha256…",                    // also inside plan, for convenience
  "errors": [Problem…],                        // present when the compile failed
  "plan": {
    "fingerprint": "sha256…",
    "modules": [{"id": "core", "label": "Core", "role": "core|operator|target",
                 "implementation_version": "3", "runtime_fields": ["password"]}],
    "nodes": [
      {"id": "core::aggregate.site", "module_id": "core", "order": 12,
       "label": "site", "kind": "…", "component": "component:site",
       "inputs":  [{"slot_id": "core::aggregate.site.input", "role": "core.binding.…"}],
       "outputs": [{"slot_id": "core::aggregate.site.output", "role": "core.graph.node.site"}],
       "action": "aggregate", "relation": "kg_graph_site",
       "sql": "SELECT …" | null,
       "columns": [{"name": "site_id", "logical_type": {…}}] | null,   // source steps
       "format": "json" | null, "location": "…/data/sites.json" | null,
       "target_path": "relationships/has_unit-fe3e5b7c.parquet" | null, // export steps
       "notes": ["materialized", "→ graph.jsonl"],
       "payload_keys": ["action", "relation"]}
    ],
    "edges": [{"id": "…", "from_step": "…", "from_slot": "…",
               "to_step": "…", "to_slot": "…", "role": "core.graph.node.site"}]
  }
}
```

`kind` is one of `source | table | projection | binding | aggregate | operator |
export | publish | document | script | step`, derived from the framework's step-id
grammar (`core::table.<name>`, `core::binding.<n>`, `core::aggregate.<component>`,
`<module>::export.node.<component>-<hash>`, `file::write`, `meta_graph::document`) and
from artifact roles. `component` is the IR reference a step belongs to — recovered from
the artifact role for binding steps, whose step ids are positional — and is what lets a
plan node be selected, badged and filtered like the declaration it came from. Input
slots carry no role in the contract (only outputs declare roles), so an input socket is
labelled from its slot name and its edge is coloured by the producer's role.

`sql` is present when the step payload carries lowered SQL; the plan view shows it
verbatim because inspecting lowered SQL is a primary use of the view.

## WebSocket events

```jsonc
{"type": "hello",       "revision": 12, "status": {...}}
{"type": "document",    "revision": 13, "document": {...}, "origin": "remote" | "self"}
{"type": "generation",  "state": "running" | "done" | "failed", "changed": ["kg_project/topology/site/__init__.py"], "error": null, "elapsed_ms": 240}
{"type": "diagnostics", "problems": [Problem…], "pyright": {"state": "ready", "files_open": 18}}
{"type": "blueprint",   "ok": true, "errors": [Problem…], "summary": {"nodes": 7, "edges": 6, "bindings": 12, "tables": 5}}
{"type": "plan",        "plan": {...}}
{"type": "build",       "state": "running" | "done" | "failed", "ok": true, "artifacts": ["build/graph.jsonl"], "problems": [Problem…]}
{"type": "log",         "level": "info", "text": "…"}
```

The client resyncs by calling `GET /api/state` after any reconnect, so a dropped
socket can never leave the UI editing a stale revision.

### Who may write which tier

Four producers feed one problem list, so each owns exactly one tier and replaces that
tier wholesale — clearing it when its pass comes back clean:

| producer | owns | delivered by |
| --- | --- | --- |
| pyright, through the anchor index | `types` | `diagnostics` |
| the framework's `create_blueprint` | `blueprint` | `blueprint` |
| the last executed build | `build` | `build` |
| IR validation and generator gaps | `document` | `diagnostics`, and the `PUT /api/document` ack |

`diagnostics` carries the complete set across all four tiers and is the authoritative
snapshot; the per-tier events exist so feedback does not wait for the next snapshot.
The save ack deliberately narrows itself to the `document` tier: generation, blueprint
and pyright for the new revision are still being computed on the pipeline thread, so a
whole-set snapshot there would be the previous revision's, and a client adopting it
would erase the error its event had just delivered.

## Status model (`GET /api/state → status`)

```jsonc
{
  "revision": 12,
  "generation": {"state": "clean", "at": "…", "changed": [], "error": null},
  "blueprint":  {"ok": false, "errors": 2},
  "types":      {"errors": 1, "warnings": 0, "state": "ready"},
  "build":      {"state": "never"},
  "project_root": "/abs/path/studio_test_project"
}
```

The header's status light is derived from this alone: any `errors > 0` or
`state != clean` is visible without opening a panel.
