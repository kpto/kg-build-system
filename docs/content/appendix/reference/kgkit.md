---
title: Project notebook and console
summary: The kgkit project surface, its notebook, and the separate console that embeds the design viewer by URL.
section: reference
perspective: reference
order: 181
status: normative
verified: 2026-11-18
sources:
  - kg_build_system/kgkit/cli.py
  - kg_build_system/kgkit/config.py
  - kg_build_system/kgkit/relations.py
  - kg_build_system/kgkit/console.py
  - kg_build_system/kgkit/console/index.html
---

> [!lede]
> `kgkit` is the project operation and notebook surface. It is not the graph language and it is not the design viewer. The console is a separate page; it embeds the design viewer as an external page through the viewer URL and the embed bridge.

## Surface

| Command | Job |
| --- | --- |
| `kbs notebook init` | Create `kgkit/`, its config and the `records/` notebook. |
| `kbs notebook status` | Show the project, workspace and object counts. |
| `kbs notebook relations list` | Print the relational catalog and iteration timeline. |
| `kbs notebook snapshot` | Import a viewer snapshot or a compiled workflow/blueprint. |
| `kbs console` | Serve the standalone project console on its own port. |
| `kbs notebook validate` / `build` / `audit` / `eval` | Run the project-owned commands from `kgkit/config.json`. |
| `kbs notebook findings add/list` | Append or read notebook findings. |
| `kbs notebook revisions record/list` | Record or list revision pins. |
| `kbs notebook compare --before … --after …` | Compare two revisions. |

The notebook is `kgkit/records/`: revisions, events, findings, proposals, change
designs, documents and captured views. `kgkit` owns `records/`; the project owns
`kgkit/ops/` and `kgkit/eval/`.

## Details

The console is deliberately separate from the design viewer:

- `kbs console` serves `kgkit/console/index.html` and its assets on the
  console port; it is not another copy of the design viewer.
- The Viewer tab embeds the URL in `kgkit/config.json` (`viewer_url`) or the
  `--viewer-url` flag. `kbs view --embed` is the usual source of that page.
- The console sends the current snapshot, or a captured revision snapshot, to the
  embedded viewer over the message bridge. The viewer keeps its own rendering,
  selection and document model.
- The console owns the relational catalog, revision timeline and subject lookup.
  The design viewer remains the place where a graph is read.

A project command is a JSON contract: it runs from the project root with the
workspace on `PYTHONPATH`, and it prints one JSON object. A missing command
returns `ok: false` with the reason, so the console can render it instead of
failing the page.

The `kg_build_system.kgkit` package has no runtime dependency on the graph language or the
viewer implementation. It can read a compiled blueprint, workflow plan or viewer
snapshot without importing the design system.
