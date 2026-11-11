---
title: Failures
summary: Error messages by stage, their cause, and the first page to open when a build refuses.
section: reference
order: 40
status: normative
verified: 2026-11-10
sources:
  - docs/book/part-3/04-quality-and-failure.md
  - kg_build_system/distribution/interpreter/
  - kg_build_system/distribution/languages/
  - kg_build_system/distribution/modules/
  - kg_build_system/kernel/service/_private/
subject: verification
perspective: reference
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions">Review</a></div>
<!-- END GENERATED:views -->

Every refusal belongs to a stage. The stage tells you whether to change a declaration, a reference, a planner composition or input data. Rows quote the source message where one exists; `<...>` marks a value the source substitutes.

## Surface

| Stage | Typical refusal | What it means |
| --- | --- | --- |
| Authoring | `TypeError` | A declaration value, expression, binding or projection is malformed. |
| Linking | `ValueError` | Declarations do not index, resolve or order into a blueprint. |
| Blueprint validation | `ValueError` from `create_blueprint` | Names, references or cross-layer targets disagree. |
| Document decoding | `ValueError` | A stored document has a missing or malformed member. |
| Compile/assembly | `AssemblyError`, a `ValueError` | Planner contributions cannot be wired into a plan. |
| Execution | unsuccessful `WorkflowReport` | Data, runtime configuration or an executor check failed. |

Read the report first. `execute` returns a `WorkflowReport`; `report.succeeded` is false exactly when `unresolved_failures` is non-empty. Each failure names a `step_id` and an `exception_type`. The same rows are in `build/build_report.json`, and `build/workflow_plan.json` exists even when the run fails. The full investigation is on [Debug](/book/part-3/04-quality-and-failure).

## Details

**Authoring.** These are raised while a declaration, expression, binding or projection is written.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `<key> must be non-nullable` | A build key is nullable; `<key>` is `build_key`, `source_build_key` or `target_build_key`. | [Values](/book/part-2/04-values-and-nullability) |
| `<key> must be scalar` | A build key is an array or struct. | [Values](/book/part-2/04-values-and-nullability) |
| `target must be a concrete <kind> component, not <name>` | A binding names an abstract category or the wrong component kind. | [Bindings](/book/part-2/06-binding) |
| `<side>_node must name the declared endpoint category <category>: pass endpoint(...) for that side` | An abstract edge endpoint has no concrete node token. | [Topology](/book/part-2/02-topology) |
| `<side>_node <node> must equal or descend from the declared endpoint category <category>` | The concrete endpoint is outside the declared category. | [Bindings](/book/part-2/06-binding) |
| `<target> has no declared property <names>` | A property value names a property the target does not declare. | [Bindings](/book/part-2/06-binding) |
| `<target>.<attribute> must be assigned a value selection or expression` | A declared property, including an inherited one, has no value. | [Bindings](/book/part-2/06-binding) |
| `<target>.<attribute> expects <type>, but the selection resolves to <type>` | A property value has an incompatible logical type. | [Values](/book/part-2/04-values-and-nullability) |
| `projections must declare at least one computed_field` | A projection has no output field. | [Projections](/book/part-2/05-grain-and-projections) |
| `Projection(source) requires a row source; declare outputs on a named subclass` | A projection class is not pinned to a row source. | [Projections](/book/part-2/05-grain-and-projections) |
| `a relational product requires one driving source; additional sources must be introduced by an explicit lookup` | A projection reads two unrelated relations. | [Projections](/book/part-2/05-grain-and-projections) |
| `join key expressions must have the same logical type` | The two join keys differ in base type. Nullability may differ; base type may not. | [Grain](/book/part-2/05-grain-and-projections) |
| `join keys must be scalar expressions` | A join key is an array or struct. | [Grain](/book/part-2/05-grain-and-projections) |
| `join on must return a (left key, right key) pair` | The join callable returns another shape. | [Grain](/book/part-2/05-grain-and-projections) |
| `union row sources must have the same shape` | The union sides differ in external names, logical types or nullability. | [Data](/book/part-2/03-source-and-rows) |
| `group_by keys must be scalar expressions` | A grouping key is an array or struct. | [Grain](/book/part-2/05-grain-and-projections) |
| `group_by key names must be Python identifiers` | A display label is used as a grouping key name. | [Grain](/book/part-2/05-grain-and-projections) |
| `group_by key names must be unique` | Two grouping keys share a name. | [Grain](/book/part-2/05-grain-and-projections) |
| `where predicates must return a Selection[bool]` | A filter predicate returns another type. | [Values](/book/part-2/04-values-and-nullability) |
| `unnest requires a present or nullable array field` | An unnest selector reads a non-array field. | [Values](/book/part-2/04-values-and-nullability) |
| `a final Table may not inherit from another final Table` | A final table is used as a base class. | [Data](/book/part-2/03-source-and-rows) |
| `a final Projection may not inherit from another final Projection` | A final projection is used as a base class. | [Projections](/book/part-2/05-grain-and-projections) |
| `a final TableGroup may not inherit from another final TableGroup` | A final table group is used as a base class. | [Assets](/book/part-2/03-source-and-rows) |
| `<class> cannot inherit from concrete graph component <component>` | A concrete node or edge is treated as a category. | [Topology](/book/part-2/02-topology) |
| `<class> has more than one abstract category parent: <names>` | A declaration names several category parents. | [Topology](/book/part-2/02-topology) |
| `table groups must declare at least one member` | A table group is empty. | [Assets](/book/part-2/03-source-and-rows) |
| `<owner> fields '<x>' and '<y>' share external name '<name>'` | Two fields map to one external column name. | [Data](/book/part-2/03-source-and-rows) |
| `<component> properties '<x>' and '<y>' share external name '<name>'` | Two properties map to one external property name. | [Topology](/book/part-2/02-topology) |

**Linking.** The linker indexes declarations, selects roots and resolves the reference closure. Only reachable declarations become symbols.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `relation names must be unique` | Two tables share a logical name. | [Data](/book/part-2/03-source-and-rows) |
| `projection names must be unique` | Two projections share a logical name. | [Projections](/book/part-2/05-grain-and-projections) |
| `relation and projection names must be unique` | A table and a projection share a logical name. | [Data](/book/part-2/03-source-and-rows) |
| `topology component names must be unique` | A topology part repeats a node or edge name. | [Topology](/book/part-2/02-topology) |
| `unknown symbol reference <reference>` | A typed reference names no indexed declaration. | [Link](/book/part-3/01-linking-and-blueprint) |
| `symbol reference cycle at <reference>` | Declarations depend on each other in a cycle. | [Link](/book/part-3/01-linking-and-blueprint) |
| `language '<language>' declares key <key> twice` | Two declarations in one language share a key. | [Link](/book/part-3/01-linking-and-blueprint) |
| `duplicate language name '<name>'` | Two languages register under one name. | [Link](/book/part-3/01-linking-and-blueprint) |
| `unknown root language(s): <names>` | The root policy names a language that is not supplied. | [Link](/book/part-3/01-linking-and-blueprint) |
| `more than one language claims value identity: <references>` | Two languages claim the same authoring value. | [Link](/book/part-3/01-linking-and-blueprint) |
| `projection row source reads unknown logical source <name>` | A projection scans a table or projection that is not in the blueprint. | [Link](/book/part-3/01-linking-and-blueprint) |
| `row-source plan reads unknown logical source '<key>'` | A row-source scan names a missing logical relation. | [Link](/book/part-3/01-linking-and-blueprint) |
| `binding reads unknown logical source(s): <names>` | A binding's row source reads a relation outside the reached set. | [Link](/book/part-3/01-linking-and-blueprint) |
| `the blueprint carries more than one graph declaration` | Two graph roots are reached in one namespace. | [Link](/book/part-3/01-linking-and-blueprint) |

**Blueprint validation.** `create_blueprint` checks names and cross-layer references after assembly.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `component names must be unique` | Two nodes or edges share a name. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| `asset names must be unique` | Two assets share a name. | [Assets](/book/part-2/03-source-and-rows) |
| `edge '<edge>' has an unknown endpoint '<node>'` | An edge endpoint names a node absent from topology. | [Topology](/book/part-2/02-topology) |
| `component '<component>' has an unknown parent '<parent>'` | A parent reference names an absent component. | [Topology](/book/part-2/02-topology) |
| `relation '<relation>' must name its logical asset` | A relation has no asset reference. | [Data](/book/part-2/03-source-and-rows) |
| `relation '<relation>' names an unknown asset '<asset>'` | A relation names an asset outside the blueprint. | [Assets](/book/part-2/03-source-and-rows) |
| `relation '<relation>' column '<column>' does not carry <ref>` | A relation column's reference is not its own field identity. | [Data](/book/part-2/03-source-and-rows) |
| `projection '<projection>' column '<column>' does not carry <ref>` | A projection column's reference is not its own field identity. | [Projections](/book/part-2/05-grain-and-projections) |
| `component '<component>' property '<property>' does not carry <ref>` | A property's reference is not its own property identity. | [Topology](/book/part-2/02-topology) |
| `binding targets an unknown component '<component>'` | A binding target is absent from topology. | [Bindings](/book/part-2/06-binding) |
| `node binding targets an unknown node '<component>'` | A node binding names an edge or a missing node. | [Bindings](/book/part-2/06-binding) |
| `edge binding targets an unknown edge '<component>'` | An edge binding names a node or a missing edge. | [Bindings](/book/part-2/06-binding) |
| `edge binding targets an unknown endpoint '<node>'` | A bound endpoint is absent from topology. | [Bindings](/book/part-2/06-binding) |
| `the graph declaration requires GraphSemantics semantics` | The graph root lacks graph semantics. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| `the graph declaration requires a purpose` | Graph semantics has no purpose. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| `the graph declaration purpose must be non-empty` | The purpose text is empty. | [Blueprint](/book/part-3/01-linking-and-blueprint) |
| `bindings require a node or edge reference` | A binding target is neither a node nor an edge. | [Bindings](/book/part-2/06-binding) |
| `bindings require a target component name` | A binding has an empty component name. | [Bindings](/book/part-2/06-binding) |
| `graph components, relations and assets require a name` | A layer object has no usable name. | [Blueprint](/book/part-3/01-linking-and-blueprint) |

**Document decoding.** The codecs check document shape, not model invariants. See [Documents](/appendix/reference/documents) for the canonical members.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `a step id document must have exactly two segments` | A plan step id is not `[component, name]`. | [Documents](/appendix/reference/documents) |
| `an opening document needs a component, a step, a direction and a name` | A connection opening has fewer than four segments. | [Documents](/appendix/reference/documents) |
| `an opening direction must be 'input' or 'output', not <value>` | An opening direction is not `input` or `output`. | [Documents](/appendix/reference/documents) |
| `an instruction kind document must have exactly two segments` | An instruction kind is not `[operation, engine]`. | [Documents](/appendix/reference/documents) |
| `unknown row plan kind <kind>` | A binding rows plan uses an unknown kind. | [Documents](/appendix/reference/documents) |
| `unknown row-source plan kind <kind>` | A data row plan uses an unknown kind. | [Documents](/appendix/reference/documents) |
| `unknown join mode <mode>` | A join `how` is outside `inner`, `left`, `right`, `full`. | [Documents](/appendix/reference/documents) |
| `'<key>' must be a non-empty string` | A required text member is missing or empty. | [Documents](/appendix/reference/documents) |
| `'<key>' must be null or a non-empty string` | An optional text member is empty or not text. | [Documents](/appendix/reference/documents) |
| `<context> must be an object` | A member that must be an object is another JSON type. | [Documents](/appendix/reference/documents) |
| `<context> must be an array` | A member that must be an array is another JSON type. | [Documents](/appendix/reference/documents) |
| `a node binding 'node' must be a node reference` | A node binding's target ref has the wrong role. | [Documents](/appendix/reference/documents) |
| `a relation 'asset' must be an asset reference` | A relation's asset ref has the wrong role. | [Documents](/appendix/reference/documents) |
| `unknown asset authority <value>` | A profile authority is outside the enum. | [Documents](/appendix/reference/documents) |
| `'profile' must be an object` | An asset has no object profile. | [Documents](/appendix/reference/documents) |
| `a graph declaration requires semantics` | A graph declaration document has no semantics member. | [Documents](/appendix/reference/documents) |
| `a graph semantics document requires a purpose` | Graph semantics has no purpose member. | [Documents](/appendix/reference/documents) |
| `annotation field '<key>' must be a non-empty string` | An annotation namespace or id is empty. | [Documents](/appendix/reference/documents) |
| `unknown unit logical type <name>` | A logical type names an unknown canonical unit. | [Documents](/appendix/reference/documents) |
| `canonical nullable types may not be nested` | A nullable type wraps another nullable type. | [Documents](/appendix/reference/documents) |

**Compile and assembly.** A plan is wired from planner contributions; a successful compile does not read data.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `workflow cannot be assembled:` | No wiring feeds every input and reads every required output. The following lines name the ports. | [Plan](/book/part-3/02-planning) |
| `<port> takes <type>, which no other step writes` | No planner emits the input's artifact type. | [Plan](/book/part-3/02-planning) |
| `<port> would loop back to every writer of <type>: <writers>` | Every candidate producer closes a cycle. | [Plan](/book/part-3/02-planning) |
| `<port> waits on whether <writers> takes or only writes <type>` | A producer's role is still ambiguous. | [Plan](/book/part-3/02-planning) |
| `<port> could be fed by <writers>, which differ by nothing the declaration states` | Two producers are indistinguishable. | [Plan](/book/part-3/02-planning) |
| `<port> has no writer of <type> that runs before it` | The only producer is ranked after the consumer. | [Plan](/book/part-3/02-planning) |
| `nothing reads <outputs>` | An ordinary output has no consumer. | [Plan](/book/part-3/02-planning) |
| `workflow component IDs must be unique` | Two contributions publish the same component id. | [Plan](/book/part-3/02-planning) |
| `duplicate step id <id>` | Two steps share a component and name. | [Plan](/book/part-3/02-planning) |
| `step '<name>' belongs to '<component>', not '<component>'` | A planner emitted a step for the wrong component. | [Plan](/book/part-3/02-planning) |
| `step <id> gives out <name> twice` | A step declares one output name twice. | [Plan](/book/part-3/02-planning) |
| `step <id> takes <name> twice; a step names each opening it takes once` | A step declares one input opening twice. | [Plan](/book/part-3/02-planning) |
| `<port> is already fed by <feeder>` | Two connections target one input opening. | [Plan](/book/part-3/02-planning) |
| `planners for component '<id>' disagree on version: <a> and <b>` | Planners sharing a component report different versions. | [Plan](/book/part-3/02-planning) |
| `planners for component '<id>' disagree on runtime_fields` | Planners sharing a component report different fields. | [Plan](/book/part-3/02-planning) |
| `unknown planner component configuration: <names>` | Runtime configuration names a component no planner produced. | [Plan](/book/part-3/02-planning) |
| `namespace_path cannot be combined with bindings` | `create_blueprint` received both selection forms. | [API surface](/appendix/reference/api) |
| `blueprint cannot be combined with namespace_path or bindings` | `compile` received a blueprint and a second source. | [API surface](/appendix/reference/api) |

**Execution.** An unsuccessful report carries the failing step and the exception text. `no executor` is raised before the runtime starts.

| Message or refusal | Cause | First place to look |
| --- | --- | --- |
| `report.succeeded` is false | `unresolved_failures` is not empty. Read the first failure's `step_id`. | [Debug](/book/part-3/04-quality-and-failure) |
| `no executor for instruction kind(s): <kinds>` | The plan contains a kind no supplied executor owns. | [Execute](/book/part-3/03-execution-and-outputs) |
| `workflow has a dependency cycle` | No pending step becomes ready. | [Execute](/book/part-3/03-execution-and-outputs) |
| `step <id> names unknown component '<component>'` | A step names a component absent from the plan. | [Execute](/book/part-3/03-execution-and-outputs) |
| `connection input <opening> is not declared by a step` | A connection names an input no step declares. | [Execute](/book/part-3/03-execution-and-outputs) |
| `connection output <opening> is not declared by a step` | A connection names an output no step declares. | [Execute](/book/part-3/03-execution-and-outputs) |
| `duplicate input opening <opening>` | One input opening is declared twice. | [Execute](/book/part-3/03-execution-and-outputs) |
| `duplicate output opening <opening>` | One output opening is declared twice. | [Execute](/book/part-3/03-execution-and-outputs) |
| `step <id> returned output <name> twice` | An executor outcome returns one output name twice. | [Execute](/book/part-3/03-execution-and-outputs) |
| `step <id> returned an artifact for an undeclared output` | An executor returned an extra artifact. | [Execute](/book/part-3/03-execution-and-outputs) |
| `step <id> returned an artifact type its output does not declare` | An executor returned the wrong artifact type. | [Execute](/book/part-3/03-execution-and-outputs) |
| `resource <module.qualname> was not provided to this executor` | An executor asked for a resource it did not declare. | [Execute](/book/part-3/03-execution-and-outputs) |
| `unknown runtime configuration for <component>: <keys>` | A runtime setting is not declared by the component. | [Debug](/book/part-3/04-quality-and-failure) |
| `missing runtime configuration for <component>: <keys>` | A required runtime field has no value. | [Debug](/book/part-3/04-quality-and-failure) |
| `invalid runtime configuration for <component>: <keys>` | A runtime value has the wrong scalar type. | [Debug](/book/part-3/04-quality-and-failure) |
| `instruction kind <kind> requires an object payload` | A step payload is not a JSON object. | [Execute](/book/part-3/03-execution-and-outputs) |
| `runtime file output path must be a string` | The file output override is not text. | [Debug](/book/part-3/04-quality-and-failure) |
| `runtime Neo4j output directory must be a string` | The Neo4j directory override is not text. | [Debug](/book/part-3/04-quality-and-failure) |
| `duckdb threads must be a positive integer` | A DuckDB provider setting is not a positive integer. | [Debug](/book/part-3/04-quality-and-failure) |
| `edge component '<edge>' requires bound source and target node components` | The Neo4j export has no binding for an endpoint node. | [Bindings](/book/part-2/06-binding) |
| `graph property of type <type> has no canonical form in the file target` | A property value cannot be written by the file target. | [Execute](/book/part-3/03-execution-and-outputs) |
| `validation found <n> conflicting non-null value(s)` | Conflict validation found contradictions and `fail_on_error` is on. | [Debug](/book/part-3/04-quality-and-failure) |

For row-grain and fan-out symptoms that produce no message, use [Debug](/book/part-3/04-quality-and-failure). For the model behind the messages, use [Documents](/appendix/reference/documents) and [Plan](/book/part-3/02-planning).
