---
title: Documents
summary: Canonical blueprint, plan and report documents, omit-versus-null rules, and provenance.
section: reference
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/interpreter/service/_private/codec.py
  - kg_build_system/distribution/languages/
  - kg_build_system/kernel/service/_private/workflow_codec.py
  - kg_build_system/kernel/service/_private/report_codec.py
  - kg_build_system/kernel/model/public/runtime.py
subject: identity
perspective: reference
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Identity, references and documents</span><a href="/subjects/identity">Overview</a><a href="/reference/documents">Guide</a><a href="/spec/identity">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

A build has three canonical documents: the blueprint in memory, the workflow plan written as `workflow_plan.json`, and the report written as `build_report.json`. The codecs define their member names, order and optionality.

## Surface

| Artifact | Produced by | Top-level members |
| --- | --- | --- |
| Blueprint document | `create_blueprint`; the blueprint itself is not written by `execute`. | `graph`, `data`, `assets`, `bindings`, optional `graph_declaration`. |
| Workflow plan document | `compile`; `execute` writes it before the run starts. | `components`, `steps`, `connections`, `provenance`. |
| Report document | `execute`; written after the run. | `published_artifacts`, `recovered_failures`, `unresolved_failures`, `provenance`. |

The blueprint has `graph` and `data` as objects, and `assets` and `bindings` as arrays. Every typed reference is a `[language, role, *key segments]` array: a field is `["data", "field", "sites.site_name"]`, a node is `["topology", "node", "site"]`, an asset is `["asset", "asset", "estate"]`, and an operation is `["expressions", "operation", "default_to"]`.

## Details

**Blueprint.**

| Member | Shape |
| --- | --- |
| `graph` | Object with `nodes` and `edges` arrays. Each component carries `name`, `labels`, `abstract`, `properties` and `annotations`; an edge also carries `source` and `target`. |
| `data` | Object with `structs`, `relations` and `projections` arrays. Each declaration carries `name`, `columns` and `annotations`; a relation also carries `asset`; a projection also carries `row_source`. |
| `assets` | Array of asset objects: `name`, `website`, `version`, `layout`, `profile`, `governance`, `annotations`, optional `semantics`. |
| `bindings` | Array of node or edge bindings. A binding carries `kind`, its target ref, `identity`, `properties`, `rows`, `annotations` and `mode`. |
| `graph_declaration` | Optional object with `name`, optional `description`, and `semantics`. Omitted when the project has no graph declaration. |

```json
{
  "graph_declaration": {
    "name": "estate",
    "semantics": {"purpose": {"text": "Track survey observations."}}
  },
  "graph": {
    "nodes": [
      {
        "name": "site",
        "labels": ["Site"],
        "abstract": false,
        "properties": [],
        "annotations": []
      }
    ],
    "edges": []
  },
  "data": {
    "structs": [],
    "relations": [
      {
        "name": "sites",
        "columns": [
          {
            "name": "site_name",
            "logical_type": {"kind": "unit", "name": "str"},
            "ref": ["data", "field", "sites.site_name"],
            "annotations": []
          }
        ],
        "annotations": [],
        "asset": ["asset", "asset", "estate"]
      }
    ],
    "projections": []
  },
  "assets": [
    {
      "name": "estate",
      "website": null,
      "version": null,
      "layout": null,
      "profile": {
        "subject": "sites",
        "coverage": "one row per site",
        "authority": "primary",
        "basis": "survey",
        "title": null,
        "description": null
      },
      "governance": {"license": null, "owner": null, "metadata": {}},
      "annotations": []
    }
  ],
  "bindings": [
    {
      "kind": "node",
      "node": ["topology", "node", "site"],
      "identity": {
        "kind": "field",
        "field": ["data", "field", "sites.site_name"],
        "path": [],
        "logical_type": {"kind": "unit", "name": "str"}
      },
      "properties": {},
      "rows": null,
      "annotations": [],
      "mode": "declarative"
    }
  ]
}
```

**Workflow plan.**

| Member | Shape |
| --- | --- |
| `components` | Array of `{id, version, runtime_fields}` objects. |
| `steps` | Array of steps. A step carries `id`, `inputs`, `outputs`, `instruction` and `assembly_preference`. |
| `connections` | Array of `{input, output}` opening keys. |
| `provenance` | Preserved verbatim. `api.compile` stores the source blueprint at `provenance["blueprint"]`. |

A step owns one instruction: `{"kind": [operation, engine], "payload": ...}`. The executor registered for that exact kind reads the payload. An output row has `kind` `"output"` or `"publication"`, a concrete `type` key and an `opening_name`. `assembly_preference` is `"eager"` or `"deferred"`.

```json
{
  "components": [
    {"id": "file", "version": "2", "runtime_fields": []}
  ],
  "steps": [
    {
      "id": ["file", "write"],
      "inputs": [],
      "outputs": [
        {
          "kind": "publication",
          "type": ["file", "write_result"],
          "opening_name": ["result"]
        }
      ],
      "instruction": {
        "kind": ["file", "default"],
        "payload": {"relative_path": "graph.jsonl"}
      },
      "assembly_preference": "eager"
    }
  ],
  "connections": [],
  "provenance": {
    "blueprint": {
      "graph": {"nodes": [], "edges": []},
      "data": {"structs": [], "relations": [], "projections": []},
      "assets": [],
      "bindings": []
    }
  }
}
```

**Report.**

| Member | Shape |
| --- | --- |
| `published_artifacts` | Array of `{opening, type, value}` objects. `value` is executor-defined and may be any JSON-safe value. |
| `recovered_failures` | Array of `{message, step_id, exception_type}` rows for failures a later step handled. |
| `unresolved_failures` | Array of the same rows for failures that blocked a publication. |
| `provenance` | The plan's provenance, including `blueprint` when compilation went through `api.compile`. |

`step_id` is a two-segment `[component, name]` array. `exception_type` is the exception class name, or `null` when the failure has no exception. `report.succeeded` is true exactly when `unresolved_failures` is empty.

```json
{
  "published_artifacts": [
    {
      "opening": ["file", "write", "output", "result"],
      "type": ["file", "write_result"],
      "value": {"location": "build/graph.jsonl", "nodes": 21, "edges": 21}
    }
  ],
  "recovered_failures": [
    {
      "message": "source row was dropped",
      "step_id": ["core", "projection.defect"],
      "exception_type": "ValueError"
    }
  ],
  "unresolved_failures": [],
  "provenance": {
    "blueprint": {
      "graph": {"nodes": [], "edges": []},
      "data": {"structs": [], "relations": [], "projections": []},
      "assets": [],
      "bindings": []
    }
  }
}
```

**Omit versus null.**

The rule is not symmetric. Some absent values are omitted, some are written as explicit `null`, and some members are always written.

| Member | When absent |
| --- | --- |
| `graph_declaration` | Omitted from the blueprint. An explicit `null` decodes to no graph declaration and is omitted on the next encode. |
| Binding `rows` | Always written; an absent row plan is explicit `null`. |
| Binding `debug_name`, `python_ref`, `semantics` | Omitted. |
| Asset `website`, `version`, `layout` | Always written; an absent value is explicit `null`. |
| Asset `governance.license`, `governance.owner` | Always written; an absent value is explicit `null`. |
| Asset `profile.title`, `profile.description` | Always written; an absent value is explicit `null`. |
| Topology `parent`, `description`, `semantics` | Omitted. |
| Topology `labels`, `abstract`, `properties`, `annotations` | Always written. |
| Data column `description`, `expression`, `semantics` | Omitted. |
| Data declaration `description`, `semantics` | Omitted. |
| Semantics `claims`, `frames` | Omitted when empty; `purpose` is required on graph semantics. |

Decoding does not validate. The codecs check the document's own shape and required scalar forms, but a decoded blueprint is not re-linked or cross-validated; a decoded plan is not checked for executability. Run the model through the pipeline before trusting it.

A codec round trip is canonical-document equality, not original text. Key order, whitespace and omitted optional members can change, so compare the re-encoded document with the canonical document rather than the bytes you started with.

Continue with [Blueprint](/pipeline/blueprint) for how the blueprint is assembled, [Plan](/pipeline/plan) for plan assembly, and [Execute](/pipeline/execute) for the run and report. The public calls are listed on [API surface](/reference/api); the failure rows in this shape are catalogued on [Failures](/reference/failures).
