# KG Studio

A visual authoring environment for [kg_build_system](../README.md) knowledge graphs.
You edit one JSON **project document**; the studio generates a complete, readable
Python KG project from it, keeps it type-checked, and shows you exactly which part of
the document a type error or a failed compile belongs to.

```
┌─ browser ─────────────────────────────────────────────────────────────┐
│ tabs: topology · contracts · projections · bindings · sources ·        │
│       modules · plan          + inspector, problems panel, status      │
└──────────────────────────▲──────────────────────┬─────────────────────┘
                    REST + WebSocket         IR patches
┌──────────────────────────┴──────────────────────▼─────────────────────┐
│ FastAPI backend                                                        │
│  project.ir.json  ← the source of truth (committed, hand-editable)     │
│  ir/infer+index   ← derived types, valid operations, resolved slots    │
│  generate/        ← IR → whole Python project + anchor index           │
│  diagnostics/     ← pyright-langserver → errors → IR refs              │
│  compile_worker   ← create_blueprint / compile / build in a subprocess │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                       studio_test_project/   (fully generated)
```

## Running it

```bash
cd studio
./dev.sh                       # backend :8700, frontend :3000, project ../studio_test_project
./dev.sh /path/to/other/project
```

```powershell
cd studio
.\dev.ps1                      # backend :8700, frontend :3000, project ../studio_test_project
.\dev.ps1 C:\path\to\other\project
```

Then open <http://127.0.0.1:3000>. The first screen offers **Create project**, which
starts an empty document; **Import data shape** in the Contracts tab infers table
contracts from JSON/CSV/Parquet in the project's `data/` directory.

Two things worth knowing while you use it:

- **Generated files are not the source of truth.** `studio_test_project/**.py` is
  rewritten from the document; edits to it are detected and reported, not adopted.
  `project.ir.json` (in `<project>/.kg-studio/`) *is* editable — the studio notices
  and follows.
- **The UI cannot compose an illegal expression.** Operations are offered only where
  their input shape allows them, and result types are computed server-side by the
  same rules the framework uses, then verified against it on every compile.

Without a backend, <http://127.0.0.1:3000/?mock=1> runs the whole interface against a
built-in sample document — useful for UI work and demos.

### Where a problem comes from

The problems panel merges four independent producers, and each owns exactly one tier:

| tier | produced by | what it means |
| --- | --- | --- |
| `types` | pyright, through the anchor index | the generated Python does not type-check |
| `blueprint` | the framework's own `create_blueprint` | it type-checks but the declarations disagree |
| `build` | the last executed run of the plan | it compiles but did not execute |
| `document` | IR validation and generator gaps | the document itself is incomplete or inconsistent |

Every problem carries the IR reference it belongs to, so it badges the offending node,
slot or block in the tab that owns it and clicking it selects the thing to fix. Nothing
runs the build on its own: **run build** in the Plan tab is the one deliberate action,
because executing the workflow is the author's call.

## Tests and checks

```bash
cd studio/backend  && .venv/bin/python -m pytest -q          # document, inference,
                                                             # generation, LSP, API
cd studio/frontend && npm run test && npx tsc --noEmit       # UI logic and types
```

The backend suite includes a live `pyright-langserver` integration test
(`-m integration`) and a test that generates a project and compiles it with
`kg_build_system.create_blueprint` — the loop is only green when the framework accepts
what the studio emits.

## Layout

| path | what lives there |
| --- | --- |
| `DESIGN.md` | the architecture and the reasoning behind it |
| `docs/AUTHORING_IR_CONTRACT.md` | authoring DSL ⇄ expression IR, verified by execution |
| `docs/API.md` | the HTTP + WebSocket contract |
| `examples/` | complete example project documents |
| `backend/studio_backend/ir/` | document models, refs, inference, derived index, store |
| `backend/studio_backend/generate/` | one renderer per layer, manifest ownership, anchors |
| `backend/studio_backend/diagnostics/` | LSP client, position→IR mapping, blueprint errors |
| `frontend/src/` | `app/`, `components/`, `features/`, `stores/`, `lib/` |

## What it deliberately does not do

- **It does not modify `kg_build_system`.** The studio is a library consumer: it
  imports the authoring API, reuses the framework's type and expression IR codecs, and
  drives `create_blueprint`/`compile`/`build`. Generation is studio-owned rather than a
  framework code-generation provider because a provider returns one `GeneratedPackage`
  of `Table`/`Struct` declarations, and a studio project must also emit topology,
  bindings, sources and `build.py` across many packages with a single owner — see
  `DESIGN.md` §2. The framework's inference provider *is* reused for data-shape import.
- **It does not guess types.** `logical_type` on every expression node is computed by
  the backend; a value sent by a client is discarded. The schema still requires the key
  to be present on the wire, so a client sends a placeholder and the save overwrites it.
  Making the field genuinely optional is a known follow-up.
- **It does not weaken a declaration to make a project compile.** A binding that
  leaves a required slot unfilled, or fills a non-null slot with a nullable
  expression, is reported as a problem. Softening it would produce a project that
  compiles while permitting records with the property absent — the silent data loss
  the framework's nullability policy exists to prevent.
- **Custom scalar types are not authorable yet.** The document model has no `custom`
  logical type, though the framework supports one.
- **The topology canvas does not draw templates.** A template reaches no blueprint, so
  the metagraph the framework itself emits contains none; the canvas shows exactly what
  the framework considers part of the topology. Templates are edited from the library
  strip beside it, and their endpoints are not offered because the generator discards
  them for that tier.
