---
title: Project notebook and console
summary: The kbs notebook, its catalog, findings, proposals and revisions, and the separate console that embeds the design viewer by URL.
section: reference
perspective: reference
order: 181
status: normative
verified: 2026-11-18
sources:
  - kg_build_system/notebook/cli.py
  - kg_build_system/notebook/config.py
  - kg_build_system/notebook/relations.py
  - kg_build_system/notebook/console.py
  - kg_build_system/notebook/console/index.html
---

> [!lede]
> `kbs notebook` records the project's findings, proposals, change designs,
> revisions and captured views, and reads the catalog. It is not the graph
> language and it is not the design viewer. `kbs console` is a separate page; it
> embeds the design viewer as an external page through the viewer URL and the
> embed bridge.

## Surface

| Command | Job |
| --- | --- |
| `kbs init` | Create an empty project and its notebook; `--fixture` copies the conformance example. |
| `kbs notebook repair` | Create the notebook directory, config and records if missing. |
| `kbs notebook status` | Show the project and notebook state. |
| `kbs notebook relations` | Print the catalog and iteration timeline. |
| `kbs notebook snapshot` | Import a viewer snapshot or a compiled workflow/blueprint. |
| `kbs notebook findings add` / `list` | Append or read findings. |
| `kbs notebook propose` / `proposal` / `decide` | Record, read and resolve a proposal. |
| `kbs notebook revisions record` / `list` | Record or list revision pins. |
| `kbs notebook compare --before … --after …` | Compare two revisions. |
| `kbs notebook validate` / `build` / `audit` / `eval` | Run the project-owned commands from `notebook/config.json`. |
| `kbs console` | Serve the project console on its own port. |

Every notebook command takes `--project <dir>` (default `.`) and `--json`.
Human output is key/value text; `--json` prints the same result as JSON. A
failed command writes `error: …` to stderr and exits non-zero.

The notebook is `notebook/records/`: revisions, events, findings, proposals, change
designs, documents and captured views. The package owns `records/`; the project
owns `notebook/ops/` and `notebook/eval/`.

## The catalog

The catalog has seven kinds:

```text
revision -> evaluation_run -> result -> finding -> change_design -> revision
```

An `evaluation_design` describes a mode; a `proposal` is referenced by a change
design.

A finding states an observation, its evidence and the decision it motivates. A
proposal is advice, not a decision; accepting it makes it available as a change
design. A revision records the manifest, revision fingerprint, build counts and
evaluation summary, and names the design that produced it. Events form a chain
through `prev`; captured views are attached to a revision by the snapshot
sidecar.

## Details

The console is deliberately separate from the design viewer:

- `kbs console` serves `kg_build_system/notebook/console/index.html` and its assets
  on the console port; it is not another copy of the design viewer.
- The Viewer tab embeds the URL in `notebook/config.json` (`viewer_url`) or the
  `--viewer-url` flag. `kbs view --embed` is the usual source of that page.
- The console sends the latest compilation, or a captured revision snapshot, to the
  embedded viewer over the message bridge. The viewer keeps its own rendering,
  selection and document model.
- The console owns the relational catalog, revision timeline and subject lookup.
  The design viewer remains the place where a graph is read.

A project command is a JSON contract: it runs from the project root with the
workspace on `PYTHONPATH`, and it prints one JSON object. A missing command
returns `ok: false` with the reason, so the console can render it instead of
failing the page.

The `kg_build_system.notebook` package has no runtime dependency on the graph
language or the viewer implementation. It can read a compiled blueprint, workflow
plan or viewer snapshot without importing the design system.
