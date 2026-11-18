---
title: Project notebook and console
summary: The kbs notebook, its design gate, the iteration event chain, and the separate console that embeds the design viewer by URL.
section: reference
perspective: reference
order: 181
status: normative
verified: 2026-11-18
sources:
  - kg_build_system/kgkit/cli.py
  - kg_build_system/kgkit/relations.py
  - kg_build_system/kgkit/revisions.py
  - kg_build_system/kgkit/designs.py
  - kg_build_system/kgkit/console.py
---

> [!lede]
> The notebook is the project's argument history. A change to the graph is
> proposed as a design, resolved, and then closed by a revision. The console is a
> separate page; it embeds the design viewer as an external page through the
> viewer URL and the embed bridge.

## Surface

| Command | Job |
| --- | --- |
| `kbs notebook init` | Create `kgkit/`, its config and the `records/` notebook. |
| `kbs notebook status` | Show the project, workspace and object counts. |
| `kbs notebook relations list` | Print the relational catalog and iteration timeline. |
| `kbs notebook findings add` / `list` | Append or read a finding. |
| `kbs notebook design new` | Propose a change design. |
| `kbs notebook design adopt` / `supersede` / `abandon` | Resolve a design. |
| `kbs notebook design link` | Link one design to another as `supersedes` or `related`. |
| `kbs notebook evaluations add` / `list` | Record or read an evaluation. |
| `kbs notebook revisions record` | Close a resolved design set as a revision. |
| `kbs notebook compare --before … --after …` | Compare two revisions. |
| `kbs notebook snapshot` | Import the latest compilation as the current view. |
| `kbs console` | Serve the separate notebook console. |

The notebook is `kgkit/records/`: revisions, events, findings, change designs,
evaluations, documents and views. The package owns `records/`; the project owns
`kgkit/ops/` and `kgkit/eval/`.

## The iteration model

An event is one fact and may reference several entities:

```json
{
  "id": "evt-0042",
  "prev": ["evt-0041"],
  "kind": "revision_added",
  "at": "2026-11-18T10:00:00+00:00",
  "refs": [
    {"kind": "revision", "id": "KG-abc123"},
    {"kind": "change_design", "id": "CD-0001"},
    {"kind": "change_design", "id": "CD-0002"},
    {"kind": "evaluation", "id": "EV-0001"}
  ],
  "payload": {"revision": {"...": "..."}}
}
```

The event kinds are `finding_added`, `design_proposed`, `design_adopted`,
`design_superseded`, `design_abandoned`, `evaluation_added` and
`revision_added`. There is no finding decision event, no proposal entity and no
snapshot event. The object files are projections of the facts the events carry.

The catalog has four kinds:

```text
revision -> evaluation -> finding -> change design -> revision
```

| Link | Stored on | Written by |
| --- | --- | --- |
| `revision.designs[]` → design, role `adopted` / `superseded` / `abandoned` | revision | `revision_facts` |
| `revision.evaluations[]` → evaluation | revision | `revision_facts`, else the latest evaluation |
| `design.findings[]` → finding, role `motivated_by` / `evidence` | design | `design new --finding` |
| `design.design_links[]` → design, role `supersedes` / `related` | design | `design new --supersedes`, `design link` |

A supersedes link is stored once, on the superseding design. The catalog derives
`superseded_by` and a design's `revision_links` from the stored direction.

A revision can link several adopted designs; their coverage of the blueprint diff
is the union. `produced_by` remains an optional legacy alias for one adopted
design and is never authoritative when more than one is adopted.

## The revise gate

`kbs notebook revisions record` refuses unless every design in the notebook is
resolved, at least one is adopted, each design named by `revision_facts.designs`
exists and its notebook state equals the named role, and a compiled view can be
captured. The project's `revision_facts` command supplies the revision
fingerprint, manifest, counts and design set:

```json
{
  "revision": "abc123",
  "manifest": "deadbeef",
  "counts": {"nodes": 537, "edges": 1182},
  "evaluations": ["EV-0001"],
  "designs": [
    {"design_id": "CD-0001", "role": "adopted"},
    {"design_id": "CD-0002", "role": "superseded"}
  ],
  "produced_by_change_design_id": "CD-0001"
}
```

A design linked to a revision is immutable; a later change is a new design, not
an edit of the old record. A resolved design that is not named by the revision
facts is still a gate error only when it is unresolved; naming the designs a
revision closes is the project's statement, and the package records it.

## Viewing

- `current.snapshot.json` is the latest compilation and is what the viewer opens
  by default.
- A revision capture is written with the revision and named by the revision
  record; it is never created independently.
- The console's viewer timeline lists the current compilation and every past
  revision snapshot. Selecting the current entry clears the revision selection;
  selecting a revision posts that revision's capture to the embedded viewer.
- A snapshot import replaces the current view and never adds a catalog row.

## Details

The console is deliberately separate from the design viewer:

- `kbs console` serves `kg_build_system/kgkit/console/index.html` and its assets
  on the console port; it is not another copy of the design viewer.
- The Viewer tab embeds the URL in `kgkit/config.json` (`viewer_url`) or the
  `--viewer-url` flag. `kbs view --embed` is the usual source of that page.
- The console sends the latest compilation, or a revision capture, to the embedded
  viewer over the message bridge. The viewer keeps its own rendering, selection
  and document model.
- The console owns the relational catalog, the design states and the iteration
  timeline. The design viewer remains the place where a graph is read.

A project command is a JSON contract: it runs from the project root with the
workspace on `PYTHONPATH`, and it prints one JSON object. A missing command
returns `ok: false` with the reason, so the console renders it instead of failing
the page. The package does not judge whether a design is honest; it enforces that
a change carries a resolved design and records which one.
