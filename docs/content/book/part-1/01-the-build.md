---
title: "1. The build"
summary: "A build turns typed declarations into a checked blueprint, a plan and a report."
section: book
perspective: book
part: I
chapter: 1
order: 11
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/api.py
  - kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
  - kg_build_system/kernel/model/public/workflow.py
  - reference_project/manifest.py
  - docs/content/book/part-3/01-linking-and-blueprint.md
---

A build can be made to look like a file. Read two JSON files, join them on a site identifier, write one line per site and one line per unit. The script is short, the output is correct, and the only explanation of why a record exists is the script itself. Change a column name and the explanation changes; change the person who maintains it and the explanation is gone.

The framework starts from a different question: what would have to be true for the output to be explainable without reading the code that produced it? The answer is not a better script. It is a build that carries the decisions that produced the records: what a record is, how it is identified, which source supplied it, what work produced it and what happened when that work ran.

## A build is a claim about records, not a script that writes them

The monitored estate is the running example. The source is a directory of JSON members: sites with a nested premises address, equipment with a site identifier, surveys with nested defects and observations, and two logger feeds. The source describes what arrived. It does not say that a site is an entity, that a unit is installed at a site, or that the relationship runs from the site to the unit rather than the other way round.

Those statements are declarations. A source relation states which source fields exist and what value type each field has. A node states which properties a record carries. An edge states its two endpoint kinds and therefore its direction. A binding states which rows become which records, and which expression supplies each property. The declarations are ordinary Python values; the type checker reads them like any other Python.

```python
from kg_build_system import (
    Field, Node, NodeValues, PropertySlot, SourceRelation, field, node_binding,
    property,
)
from reference_project.asset.estate import Estate


class SitesSourceRelation(SourceRelation[Estate]):
    site_id: Field[str] = field()
    site_name: Field[str] = field()


class Site(Node):
    name: PropertySlot[str] = property()


site_binding = node_binding(
    target=Site,
    rows=SitesSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=Site(name=row.site_name.default_to("Unnamed site")),
    ),
)
```

The snippet contains four different kinds of statement. `SourceRelation[Estate]` says the rows come from the estate asset. The two fields say the relation exposes an identifier and a display name, each with a value type. `Site` says a published site record has a name. The binding says the identifier is the build key and the name is a property, with an explicit fallback for a missing display value. The identity, the source contract and the mapping are all visible without a query.

The split matters when something changes. If the source renames a column, the source relation changes and the node can stay. If the graph needs a new property, the node and binding change and the source contract can stay. A script fuses those decisions into one expression; declarations keep them separable. That is the practical meaning of designing the record before choosing the rows that supply it.

It also makes refusal possible. A build key is a present scalar: an identifier cannot be missing, because a record with no identity is not a record. The `drop_null()` in the example is not decoration. It states that rows without an identifier are excluded before the binding sees them. A display name has a different rule: `default_to("Unnamed site")` states that a missing name is acceptable and gives it a value. The declarations distinguish an unacceptable absence from an acceptable one.

## Three artifacts answer three different questions

A build produces three artifacts, and each answers a question the others cannot. The blueprint answers what the graph is. The workflow plan answers what work produces it. The report answers what happened when that work ran.

| Artifact | Question | Holds |
| --- | --- | --- |
| `GraphBlueprint` | What is the graph? | Graph records, relations, assets, bindings and an optional graph declaration |
| `WorkflowPlan` | What work produces it? | Components, steps, typed connections and provenance |
| `WorkflowReport` | What happened? | Published artifacts, failures, provenance and success |

The blueprint is the semantic model. `GraphBlueprint` has five fields: `graph` for nodes and edges, `data` for structs, source relations and derived relations, `assets` for the logical source units those relations name, `bindings` for the fulfilment between a relation and a record, and `graph_declaration` for project-level purpose and claims. The last field is optional; a project may carry zero graph declarations. Topology objects carry names, labels, endpoints, properties, annotations, an abstract flag and a parent. Cross-symbol fields are typed references such as `NodeRef`, `FieldRef` and `AssetRef`, not bare strings.

The blueprint contains no components, no steps, no runtime settings and no source data. It is what the graph means, separated from how the graph is produced. The linker's symbol graph is working state behind it; the blueprint is the deliverable.

The workflow plan is the work. `WorkflowPlan` has components, steps, connections and provenance. A component groups the planners that share an identity and runtime fields. A step owns its typed inputs and outputs and exactly one instruction. The instruction kind is an exact two-part name such as `("sql", "duckdb")` or `("source_relation", "duckdb")`; there is no prefix matching and no shared `"sql"` kind. A connection joins one resolved output opening to one resolved input opening. A plan is one planner composition, not a universal recipe.

The report is the outcome. `WorkflowReport` has `published_artifacts`, `recovered_failures`, `unresolved_failures`, `provenance` and `succeeded`. Only publications appear in `published_artifacts`; the ordinary outputs exchanged between steps stay inside the run. Each failure exposes a message, a typed step identifier and an exception type. `succeeded` is true exactly when no unresolved failure remains at a publishing step.

Three artifacts exist because the questions have different lifetimes. A blueprint can be inspected without data. A plan can be inspected without executing it. A report can be audited without re-running the build. If one object carried all three, a change to a planner would look like a change to the meaning of the graph, and a data failure would look like a design failure. The separation is what keeps each review local.

## Authoring, compilation and execution are separate moments

The three artifacts are produced across three moments, and only the last one opens data.

Authoring is the moment of declaration. Source relations, derived relations, nodes, edges and bindings are Python values. The type checker catches a property assigned the wrong logical type and a binding that names an undeclared property. A nullable build key is refused when the binding is constructed. None of that needs a source file. Authoring failures are ordinary `TypeError` and `ValueError` exceptions raised while the declaration is constructed.

Building the blueprint is the moment of linking. Discovery imports the project's modules and collects the public values they expose. The linker indexes every declaration by key, selects roots, walks the references from those roots, orders the reachable declarations dependencies-first and transcribes each one. Only the reachable closure enters the blueprint. A source relation no binding reads contributes nothing, even if it is defined in the project. The linker then assembles the semantic model and validates it: names are unique, endpoints exist, references point at known declarations and every relation names an asset.

Compilation is the moment of planning. `compile` consumes the blueprint and a planner composition and emits components, steps and connections. It reads no data and writes no files. It checks everything that does not need data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every selection names a known field of a source or derived relation;
- every build key is a non-null scalar;
- every edge endpoint exists, is concrete and descends from the declared category;
- every relation names an asset present in the blueprint;
- every planner's compile-time configuration is valid;
- the wiring can feed every input and read every ordinary output.

The estate build compiles to six components, sixty steps and ninety connections before a source file is opened. Those numbers describe the plan, not the data. They are decided entirely by the declarations and the planner composition. A property mapped twice, an endpoint outside its declared category or a wiring ambiguity fails before execution, with no partial output.

Execution is the only moment that opens resources. `execute` builds a map from exact instruction kinds to executors and refuses a plan with a kind it cannot run before any step starts. It opens the runtime, runs the steps in dependency waves and dispatches each step by the exact kind in its instruction. A failure inside a step becomes a report entry; a failure before execution raises. The plan is written to the output directory before execution starts and the report is written after the run finishes.

This ordering is the reason most mistakes are cheap. A declaration error fails before data is touched. A plan error fails before a query runs. Only the failures that genuinely depend on the source, the runtime or the executor appear late. When a build does fail late, the report names the step, and the plan still exists to explain what that step was supposed to do.

## The estate keeps its meaning at every handoff

Meaning survives because each handoff carries it forward, not because a later stage remembers it.

The first handoff is from declarations to blueprint. The blueprint is built from the declarations, not from a summary of them. The round-trip contract states the strength of that claim: render the blueprint back to authoring source, rebuild it, and compare the canonical documents. The second blueprint must equal the first. The original text, class names and module layout are not preserved; the model is.

The second handoff is from blueprint to plan. `compile` records the source blueprint document at `plan.provenance["blueprint"]`. A serialized plan therefore carries the model that produced it and can be read without a second artifact. Provenance is opaque to the planning stage; the composition root attaches the blueprint document.

The third handoff is from plan to report. The report copies the plan provenance, so an output directory contains the plan, the report and, inside both, the blueprint document. A consumer with the directory can reconstruct the chain that produced each published artifact without the Python source.

The estate uses that chain concretely. A published record carries a `_kg_binding_symbol` that names the binding which produced it. Every node carries a `source_version` stamp, and every recorded relation carries `stage` and `as_at` properties. The meta graph states each component's label, description, annotations, properties and record count. The asset states its profile: subject, coverage, authority and basis. A reader can move from a record to its binding, from the binding to its node and relation, from the relation to the estate asset and from the asset to the source release.

What survives is identity, direction, value types, nullability decisions, defaults, annotations, purpose and the plan's wiring. Round-trip equivalence is canonical document equality: it compares the model, not the original source text, class names, module layout or callable bodies. Runtime configuration is an execution input, not part of the plan. Data values survive only where a publication writes them.

There is one limit worth stating plainly: the framework preserves the meaning that is declared, and it does not invent the meaning that is missing. A project can declare a node that copies a source row column for column. That graph is valid, compiles, binds and publishes. It simply does not state anything a consumer could use beyond the columns. The reference estate declares six concrete node types, six concrete edge types, fourteen bindings and one graph declaration that carries the project's root purpose. Zero graph declarations remain legal, but then the project has no stated reason for the graph it builds. The build is only as meaningful as its declarations.

## Separation costs something, and the cost is the point

The separation is not free.

A build is whole-plan, not incremental. Running it again rewrites the selected artifacts; there is no change detection at the level of a single record. The framework has no schema versions, no compatibility negotiation and no migration path. A plan runs only where an executor exists for every exact instruction kind it names; change a planner and the plan must be compiled again. `report.succeeded` means no unresolved failure remains at a publishing step, not that every step succeeded. Recovered failures can be present in a successful report, and a failure in a branch that reaches no publication is classified as recovered.

Execution is also not parallel. Steps run in dependency waves, and the steps in one wave run one at a time. The plan states order and dependency; it does not state a throughput target.

These costs buy specific properties. A declaration change stays local: join semantics belong to the row-source algebra, source access belongs to the source relation, record shape belongs to the node and mapping belongs to the binding. A planner or executor can be replaced without rewriting declarations, because the plan names exact instruction kinds rather than an engine. The meaning can be reviewed before any data is read. The outcome can be reviewed without trusting a log.

The output file is a snapshot. The chain of artifacts is the product. A build that writes the same records as a script, but also states what they are and how they were produced, is a different kind of object: one that a consumer can rely on after the author has moved on.

## Next

[2. A first build](/book/part-1/02-a-first-build) — run the reference estate build and read what it writes.
