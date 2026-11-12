# Survey: core, deduplication, merging, conflict validation, file, meta-graph
Source root: `/home/paul/Repos/kg-build-system` (read-only). Scope:
`kg_build_system/distribution/modules/{core,deduplication,merging,conflict_validation,file,meta_graph}/**`.
Survey date: 2026-11-09. Paths relative to source root. "Module" means a feature
package under `distribution/modules/`, not a protocol or registry entry.
`component_id`/`version`/`runtime_fields`/kinds below are code facts. "Unclear"
marks a point the reviewed code/docs do not settle.

## 1. Module map

| Module | Planner(s) | Executor(s) in module | Resource provider | `component_id` | `version` | `runtime_fields` | Instruction kinds emitted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `core` | `RowSourcePlanner`, `ProjectionPlanner`, `BindingPlanner`, `RecordsPlanner` | none | none | `core` (all four) | `4` (all four) | `()` (all four) | row-source/projection/binding use injected `SqlEmitter.kind` (default `("sql","duckdb")`); aggregate uses `("aggregate","duckdb")` |
| `deduplication` | `DeduplicationPlanner` | none; `DuckDbExecutor` owns the kind | none | `deduplication` | `2` | `()` | `("deduplication","duckdb")` |
| `merging` | `MergingPlanner` | none; `DuckDbExecutor` owns the kind | none | `merging` | `2` | `()` | `("merging","duckdb")` |
| `conflict_validation` | `ConflictValidationPlanner` | `ConflictReportExecutor` | none | `conflict_validation` | `2` | `()` | `("conflict_findings","duckdb")`, `("conflict_report","default")` |
| `file` | `FilePlanner` | `FileExecutor` | none | `file` | `2` | `(RuntimeField("relative_path","Optional runtime replacement for the relative output path.",required=False),)` | `("file","default")` |
| `meta_graph` | `MetaGraphPlanner` | `MetaGraphExecutor` | none | `meta_graph` | `2` | `()` | `("meta_graph","default")` |
- The file runtime field uses default `value_type="string"`, `secret=False`.
- No in-scope module contributes a `ResourceProvider`. File/meta executors consume
  `RelationService` and `OutputStorage` from `duckdb`/`runtime`.
- `DuckDbExecutor` (outside scope) claims `source_relation`, `sql`, `aggregate`,
  `deduplication`, `merging`, `conflict_findings`; `resources=(DuckDbService,)`.
  Its three in-scope planner kinds are dedup, merge and conflict findings.
- Public models: `MergingConfiguration`; `ConflictValidationConfiguration`,
  `ConflictingNonNullValueFinding`, `ConflictingNonNullValuesReport`;
  `FileConfiguration`; `MetaGraphConfiguration`. Dedup has no model.
- Core constructors: `core_planners(*, engine: SqlEmitter) -> tuple[RowSourcePlanner, ProjectionPlanner, BindingPlanner, RecordsPlanner]`;
  each planner takes `(*, engine: SqlEmitter)`. `RecordsPlanner` stores but never
  uses `engine`.

## 2. Core planners
All four implement `component_id="core"`, `version="4"`,
`runtime_fields=()`, `plan(blueprint: GraphBlueprint, context: PlanContext) ->
Sequence[Step]`. All call `core_plan(blueprint, context)`; the first call
computes and caches `CorePlan` at `PlanContext.shared["core.plan"]`. A wrong
cached type raises `TypeError`.
`CorePlan` fields:

```python
projections: tuple[ProjectionDTO, ...]
row_source_plans: tuple[RowSourcePlanDTO, ...]
bindings: tuple[BindingDTO, ...]
shapes: Mapping[str, tuple[ShapeField, ...]]
table_relations: Mapping[str, str]
projection_relations: Mapping[str, str]
row_source_relations: Mapping[str, str]
row_source_fields: Mapping[str, tuple[ShapeField, ...]]
relations: Mapping[str, str]
```
`relations` merges table, projection and row-source mappings; later mappings
override on collision. Table relations are `kg_table_<n>`; projections
`kg_projection_<index>` in dependency order; derived row-sources
`kg_rowsource_<index>` child-first.

### 2.1 `RowSourcePlanner`
Consumes `CorePlan.row_source_plans` (every non-`RowScanDTO` reachable from
projection `row_source` and binding `rows`), their child plans, and
`projection_relations`, `row_source_relations`, `shapes`, `row_source_fields`,
`relations`.
Emits one `Step` named `rowsource.<row_source_key>` per derived plan. Inputs:
one per distinct direct child key in first-occurrence order, via `read_input`
(row-source, then projection, then table). Output:
`Output(CoreArtifactTypes.row_source(key))`. Payload:
`{"relation": relation, "sql": row_source_sql(...)}`. Kind: `engine.kind`.
Preconditions: `core_plan` succeeds; the injected emitter supports the
row-source DTO (DuckDB raises `TypeError` otherwise); `plan_fields` has a
declared source shape (unknown source -> `ValueError`); derived keys are stable;
children precede parents. No derived plans means no steps. Row-source cycles are
not explicitly checked (only projections have a cycle check).

### 2.2 `ProjectionPlanner`
Consumes `CorePlan.projections` in dependency order and
`projection_sources(projection)` (field refs, lookup targets, row-source scans),
plus `relations`, `shapes`, `row_source_fields`.
Emits one `projection.<name>` step. Inputs are one per source in
`sorted(projection_sources(...))` via `read_input`. Output is
`Output(CoreArtifactTypes.projection(name))`. Payload: `{"relation":
projection_relations[name], "sql": projection_sql(...)}`. Kind: `engine.kind`.
Preconditions/failures: `ordered_projections` raises
`ValueError("projection dependency graph contains a cycle")`; columns with
`expression is None` are dropped, so an all-None projection reaches
`product_sql` and raises `relational products require at least one output`;
`plan_product` raises on missing relation names, more than one field-source
relation, or wrong `expand`/filter arity. Dependency ordering uses relation
names, not artifact types.

### 2.3 `BindingPlanner`
Consumes all `CorePlan.bindings` in blueprint order; `binding_sources(binding)`
(relations read by build key, edge endpoint keys, properties and row plan);
`relations`, `shapes`, `row_source_fields`; and the target component's declared
property types from `graph.nodes + graph.edges` by name.
Emits one `binding.<index>` step per binding. Inputs: one per source in
`sorted(binding_sources(binding))` via `read_input`. Output:
`Output(CoreArtifactTypes.binding(component, index))`. Payload:
`{"relation": f"kg_binding_{index}", "sql": ...}` where SQL is wrapped as
`SELECT *, '<binding artifact key>' AS _kg_binding_symbol FROM (<binding_sql>)`.
Kind: `engine.kind`. The symbol is a display row value, not a pipeline identity.
Binding SQL: `binding_outputs` = `build_key` from `identity`, plus edge
`source_build_key`/`target_build_key`, then properties. `binding_sql` emits the
relational product, casts declared properties to canonical SQL types in a
`_kg_named` CTE using `_kg_raw_` names, then applies the guard projection: a
non-null declared output becomes `_kg_nn(<column>, <claim message>)`; nullable
outputs pass through. Build/endpoint keys are not cast because
`binding_property_types` only contains component properties.
Preconditions/failures: at least `build_key` always exists; duplicate property
names are rejected earlier by `validate_binding`; `plan_product` has the same
one-driving-source/missing-relation rules. `binding_property_types` returns
`{}` if the target component is absent; it does not raise. No reserved-name check
was found for `build_key`/`source_build_key`/`target_build_key`/`type`/`kind`/
`_kg_binding_symbol`; `binding_outputs` uses `dict.update`, so a property named
`build_key` overwrites the identity entry. Whether authoring forbids that is
`unclear`.

### 2.4 `RecordsPlanner`
Consumes `CorePlan.bindings` and `graph_record_components(blueprint)` — every
node/edge whose `name` appears in at least one binding's `component`, in graph
order (`nodes` then `edges`). Emits one `aggregate.<component>` step per bound
component. Inputs: one per binding index targeting it, declared
`binding.<index>`, type `CoreArtifactTypes.binding(component, index)`. Output:
`Output(CoreArtifactTypes.graph_records(kind, component))`.
`assembly_preference="deferred"`. Instruction:
`InstructionKind("aggregate","duckdb")`, payload
`{"relation": f"kg_graph_{component.name.lower()}"}`.
The executor unions all inputs with `UNION ALL` into a view; no duplicates are
removed. Multiple bindings to one component are unioned, not competing
producers. Abstract categories are not binding targets, so no aggregate step;
unbound components produce no records. Preconditions: at least one binding;
every binding artifact produced; the aggregate output must be read (otherwise
assembly fails `nothing reads ...`). `RecordsPlanner` ignores its `engine`.

### 2.5 Core artifact vocabulary

```python
CoreArtifactTypes.graph_records(kind, component)  # ("core","graph",kind,component)
CoreArtifactTypes.binding(component, index)       # ("core","binding",component,str(index))
CoreArtifactTypes.table(name)                     # ("core","data","table",name)
CoreArtifactTypes.projection(name)                # ("core","data","projection",name)
CoreArtifactTypes.row_source(key)                 # ("core","data","row_source",key)
graph_record_artifact(artifact_type) -> GraphRecordArtifact | None
```
`graph_record_artifact` accepts exactly 4 segments starting `("core","graph")`,
kind `node`/`edge`, non-empty component.

### 2.6 Core ordering
`core_planners` returns row-source, projection, binding, records. The default
toolchain puts `DuckDbSourcePlanner` before this group. Compilation ranks by
component order, eager before deferred, then declaration position; aggregates
are deferred, so they run after core eager steps.

## 3. Deduplication

### 3.1 Authoring surface
Two distinct surfaces share the word:
1. Planner: `DeduplicationPlanner()`; no constructor arguments, no config; applies
   to every bound record component.
2. Row-source: `RowSource.distinct()` and `union(..., all=False)` author
   `RowDistinctDTO`/`RowUnionDTO`; emitted inside a row-source step by DuckDB
   row-source emitters. This is not the `deduplication` module.

### 3.2 Plan shape
For each bound graph-record component: eager `Step(component="deduplication",
name=component.name, inputs=(Input(graph_records(kind, component), None,
"records"),), outputs=(Output(graph_records(kind, component),
Key(("distinct",))),), instruction=Instruction(
InstructionKind("deduplication","duckdb"),
{"relation": f"kg_distinct_{component.name.lower()}"}))`.

### 3.3 Key semantics
The executor runs `SELECT DISTINCT * FROM <input relation>`.
- Duplicate means identical in every received column: build key, all properties,
  edge endpoint keys, and `_kg_binding_symbol`.
- The binding symbol encodes the binding artifact key, so two bindings
  producing otherwise identical rows do not dedup against each other. Exact
  duplicates from one binding do collapse.
- SQL `DISTINCT` treats nulls as equal for duplicate elimination: same null
  pattern = duplicate; one null + one non-null = distinct.
- No key-based dedup. Same build key with differing values leaves both rows.
- No fuzzy matching, normalization, case folding or type coercion beyond SQL
  column equality.

### 3.4 Survivor selection and determinism
No survivor policy: identical rows are equivalent and SQL returns one
representative per distinct tuple; no provenance/binding preference. The
surviving set is deterministic for deterministic input. Physical row order is
not guaranteed (no `ORDER BY`). Relation names are
`kg_distinct_<component lower>`; case-only component names would collide
(`unclear` whether topology permits this).

### 3.5 Limits
Only exact full-row duplicates; same-key conflicting facts remain for merging
or a binding fix. One step per component, so no cross-component dedup. Cannot
remove duplicates hidden by a differing `_kg_binding_symbol`. No scope,
ordering key or survivor policy. Unread `distinct` output fails assembly.
If no input relation arrives, the executor returns success with no artifact;
whether that state is reachable is `unclear`.

## 4. Merging

### 4.1 Configuration

```python
MergingPlanner(configuration: MergingConfiguration)
MergingConfiguration(components: tuple[type[Any], ...] | None = None)
MergingConfiguration.to_json() -> {"components": None | [{"module": ..., "qualname": ...}]}
```
`components=None` = every bound record component; a tuple restricts scope.
`resolve_component` accepts a class, a `FrozenObject` (thawed), or a mapping
`{"module":..., "qualname":...}`. `resolve_components` requires a class whose
`_declaration` is `ComponentMetadata` with `kind in {"node","edge"}` and
`abstract is False`, else `TypeError("components must be concrete Node or Edge
classes")`. `component_name` reads `_component_name`; missing/empty raises
`TypeError("components must name a declared node or edge")`.

### 4.2 Plan shape
For each bound component in scope: eager `Step(component="merging",
name=component.name, inputs=(Input(graph_records(kind, component), None,
"records"),), outputs=(Output(graph_records(kind, component),
Key(("merged",))),), instruction=Instruction(InstructionKind("merging","duckdb"),
{"relation": f"kg_normalised_{component.name.lower()}", "select": select}))`.
A scope component not bound simply emits no step; not an error.

### 4.3 Node and edge merge
Node `fields` = every declared property. Edge `fields` =
`["source_build_key","target_build_key", *property_names]`. Payload `select` =
`"build_key", min("<field>") AS "<field>", ...`. Executor runs
`SELECT <select> FROM <input relation> GROUP BY "build_key"` and materializes
`kg_normalised_<component lower>`.
Consequences: endpoint keys are also minimized; a same-key edge with different
endpoints does not raise, it keeps the minimum endpoint. `_kg_binding_symbol`
is absent from `fields`, so merging drops it (matching the docs). Parallel edge
facts with the same key collapse; deliberately distinct edge families must stay
out of scope.

### 4.4 Conflict behavior
No conflict detection. Two non-null values for one property are resolved by SQL
`min`, not an error/report/latest rule. `min` ignores nulls; all-null yields null;
one value + null keeps the value. Conflicting edge endpoints are reduced by
`min`; conflict validation does not inspect endpoint keys, so that conflict is
not reported. Docs recommend validation before merging, because validation after
merging finds nothing.

### 4.5 Determinism and limits
`min` is deterministic for a total order; ties choose the same value. Numeric
`min` = smallest, string = lexicographic, temporal = earliest; this is SQL
`min`, not a domain rule. Null handling is SQL aggregate behavior. Arrays,
structs and other nested types are allowed by the type system, but the planner
does not preflight `min` support; a failure would be a runtime step failure, not
a plan error (`unclear` whether DuckDB `min` accepts every allowed nested type).
Output is one row per `build_key` group (a null group is included if present). No batching, memory bound or
type-specific merge. Output is an ordinary `Output` and must be read.
Lowercased relation names could collide (`unclear` if topology prevents).

## 5. Conflict validation

### 5.1 Configuration and values
`ConflictValidationConfiguration(fail_on_error: bool = True)` has no
`__post_init__`; a non-bool is accepted and used by truthiness in the executor.
The planner always writes `{"fail_on_error": ...}` into the report instruction.

```python
ConflictingNonNullValueFinding(component: str, build_key: str,
                               property_name: str, distinct_values: int)
ConflictingNonNullValuesReport(findings: tuple[ConflictingNonNullValueFinding, ...])
```
Both are frozen dataclasses; the report is the Python value published as an
artifact, not a JSON-specific model.

### 5.2 Planner
`ConflictValidationPlanner(configuration: ConflictValidationConfiguration)`.
Selects `graph_record_components(blueprint)` (every bound node/edge) and emits:
- One eager findings step per property of each selected component: name
  `<component>.<property>`; input graph-record artifact declared `records`;
  output `Output(ArtifactType.of("conflict_validation","findings",component,
  property), opening_name=Key(("findings",)))`; instruction
  `InstructionKind("conflict_findings","duckdb")`, payload
  `{"component": component.name, "field": prop.name}`.
- One deferred `report` step: inputs are an open findings pattern
  `ArtifactPattern.of("conflict_validation","findings","**")` declared
  `findings`, plus one exact graph-record input per selected component declared
  `<component>.records`; outputs are `Publication(ArtifactType.of(
  "conflict_validation","report"), Key(("report",)))` plus one `Output` per
  component with opening `Key(("validated", component.name))`;
  `assembly_preference="deferred"`; instruction
  `InstructionKind("conflict_report","default")`, payload
  `{"fail_on_error": configuration.fail_on_error}`.
A selected component with no properties contributes only its record input to the
report; no findings step.

### 5.3 What is checked
`DuckDbExecutor._conflict_findings` takes the first input artifact relation and
runs, per property:

```sql
SELECT "build_key", count(DISTINCT "<field>")
FROM <source>
GROUP BY "build_key"
HAVING count(DISTINCT "<field>") FILTER (WHERE "<field>" IS NOT NULL) > 1
```
Each row becomes `ConflictingNonNullValueFinding(component, build_key,
property_name, distinct_values)`. So: group by `build_key`; count distinct
**non-null** values of one property; report groups with count > 1; report the
count, not the values.

### 5.4 Report executor
`ConflictReportExecutor` has
`kinds=(InstructionKind("conflict_report","default"),)`, `resources=()`.
- Disrupted context -> `skipped(context)`.
- No findings -> `SUCCEEDED`; forwards each declared `Output` whose type appears
  in received record artifacts; publishes no report.
- Findings, `fail_on_error=False` -> `SUCCEEDED`; publishes
  `ConflictingNonNullValuesReport(findings)` under `report`; forwards records.
- Findings, `fail_on_error=True` -> `FAILED`, message `validation found N
  conflicting non-null value(s)`; publishes the report artifact only; does not
  forward records.
The report artifact is returned even on `FAILED`; the runtime records returned
artifacts before failure classification, so the report can appear in
`published_artifacts` on a failed run. Docs say a finding “fails the run” but do
not explicitly state that the report is still published. Record forwarding is
keyed by `ArtifactType`; multiple contributions of one type would let the last
win, though the planned report has one exact input per component.

### 5.5 What it cannot see
- Null-vs-value conflicts: nulls are filtered from the distinct count.
- All-null properties: no finding.
- Missing required values: enforced earlier by core `_kg_nn`, not here.
- Edge endpoint conflicts: `source_build_key`/`target_build_key` are not
  component properties, so no findings step; merging minimizes them.
- `_kg_binding_symbol` differences/conflicts: not a component property.
- Properties absent from the component DTO: only `component.properties` is
  iterated; extra relation columns are invisible.
- Unbound components/abstract categories: no selected component, no findings.
- Cross-component or cross-key conflicts: groups within one component/key.
- Records before or after its position: only the wired artifact relation is
  seen; after merging, values are already collapsed.
- Non-graph-record data: consumes `core.graph.*`, not source tables/projections.
- Duplicate build keys themselves: grouping by key is intentional; duplicates
  are not a finding.
Runtime failure modes: missing `build_key`/property column -> SQL error becomes
a failed step, not a finding; no input relation -> success with no artifact; a
failed findings step disrupts the deferred report, which becomes `SKIPPED`.

## 6. File target

### 6.1 Configuration
`FileConfiguration(relative_path: str)` validates with
`validate_relative_path(value, context="file output path")`: empty/non-string ->
`ValueError("file output path must be a non-empty relative path")`; absolute or
containing `..` -> `ValueError("file output path must be relative to the build
output directory")`.
`FilePlanner(configuration)` has `component_id="file"`, `version="2"` and
`runtime_fields=(RuntimeField("relative_path","Optional runtime replacement for
the relative output path.", required=False),)`.

### 6.2 Plan shape
One deferred step: `component="file"`, `name="write"`, input
`Input(ArtifactPattern.of("core","graph","**"), None, "records")`, output
`Publication(ArtifactType.of("file","write_result"), Key(("result",)))`,
instruction `InstructionKind("file","default")` with payload
`{"relative_path": configuration.relative_path}`. The open pattern expands to
all available `core.graph.*` types. The publication is exempt from the
must-be-read rule.

### 6.3 Executor
`FileExecutor(configuration: Any = None)`, kinds `(InstructionKind("file",
"default"),)`, `resources=(RelationService, OutputStorage)`.
- Disrupted -> `skipped`.
- Reads compiled `relative_path`; missing/non-string ->
  `RuntimeError("file instruction requires a compiled relative output path")`.
- Merges executor defaults with `context.runtime_configuration`; runtime wins
  when not `None`. An executor-level `relative_path` can override the compiled
  path even without a runtime value (docs only describe `BuildRuntime(...)`).
- Revalidates the final path; resolves through
  `OutputStorage.child(PurePosixPath(...))`; creates parents; opens `"w"`.
- For every `core.graph.*` contribution under `records`, runs
  `SELECT * FROM <relation>`, streams `fetchmany(1_000)`, builds a dict, then
  overwrites `build_key` with `str(_canonical_property_value(record["build_key"]))`
  and sets `type=component`, `kind="node"|"edge"`.
- Writes one JSON object per line with `sort_keys=True` and
  `default=_canonical_property_value`.
- Returns `{"nodes": n, "edges": m, "location": str(path)}` via
  `succeeded(context, summary)`.
Canonicalization: `None`/`bool`/`int`/`float`/`str` pass; `datetime`,
`date`, `time`, `UUID` become canonical text; `dict`/`list`/`tuple` recurse
(tuples become lists); any other type raises `TypeError("graph property of type
... has no canonical form in the file target")`. `_kg_binding_symbol` is
written if present (dedup keeps it; merging removes it).
Limits/ambiguities: row order is not sorted; JSON keys are sorted, but lines
follow relation/fetch order. `type`/`kind`/`build_key` are overwritten, so
same-named properties are silently replaced; no reserved-name check was found.
The executor requires `RelationService`/`OutputStorage` even for an empty input.
The summary is a plain dict, not a typed model.

## 7. Meta-graph target

### 7.1 Configuration

```python
MetaGraphConfiguration(relative_path: str = "meta_graph.json",
                       example_limit: int = 3,
                       include_html: bool = True,
                       html_relative_path: str = "meta_graph.html")
```
Validates `relative_path` (context `"meta-graph document path"`),
`html_relative_path` (context `"meta-graph HTML path"`, even if
`include_html=False`), and rejects `example_limit < 0` with
`ValueError("meta-graph example limit may not be negative")`.
`MetaGraphPlanner(configuration: MetaGraphConfiguration | None = None)` has
`component_id="meta_graph"`, `version="2"`, `runtime_fields=()`.

### 7.2 Plan shape
One deferred step: `component="meta_graph"`, `name="document"`, input
`Input(ArtifactPattern.of("core","graph","**"), None, "records")`, output
`Publication(ArtifactType.of("meta_graph","meta_graph_document"),
Key(("result",)))`, instruction `InstructionKind("meta_graph","default")` with
the encoded static document payload: `relative_path`, `example_limit`,
`include_html`, `html_relative_path`, `components`.
DTOs: `MetaGraphComponentDTO(name, kind, abstract, label, labels, description,
parent, children, depth, source, target, endpoints, bindings, properties,
annotations)`; `MetaGraphPropertyDTO(name, type, nullable, logical_type,
description, annotations)`; `MetaGraphBindingDTO(debug_name, source_node,
target_node)`; `MetaGraphDocumentDTO(relative_path, example_limit, include_html,
html_relative_path, components)`.

### 7.3 Effective topology
`effective_components` starts from every bound component, keeps all ancestors
(abstract or concrete) via `parent`, and for each kept edge keeps source/target
endpoints and their ancestors. Returns sorted by `(kind, name)` (`"edge"` before
`"node"` lexically).
`component_entries` builds `children` from parent relationships, computes `depth`
by walking parents through the full component index, resolves edge binding
endpoints (explicit `source_node`/`target_node`, then declared edge endpoints),
collects bindings per component, expands property types via `expand_type`
(resolving struct members from `blueprint.data.structs`), and includes
annotations/labels/description/endpoints.

### 7.4 Executor
`MetaGraphExecutor(module_version: str = "2")`, kinds
`(InstructionKind("meta_graph","default"),)`, resources
`(RelationService, OutputStorage)`.
- Disrupted -> `skipped`.
- Decodes payload (DTO, mapping, `FrozenObject`, object with `.payload`, nested
  `{"payload": {...}}`).
- Validates `relative_path`; resolves through `OutputStorage`; creates parents.
- `observed_components(context, instruction, resources)` measures every received
  `core.graph.*` artifact. Duplicate `(kind, component)` raises
  `RuntimeError("multiple graph-record artifacts for ...")`.
- If `example_limit > 0`, runs one query per relation:
  `COUNT(*)` plus `approx_top_k("<property>", limit)` per declared property. If
  `example_limit == 0`, only `COUNT(*)`.
- Example values are canonicalized (NaN/Infinity as strings, temporal/UUID as
  canonical text, dict/list recursive); unsupported values raise `TypeError`.
  They are sorted by `(json.dumps(canonical), repr(value))` and truncated. The
  selection is approximate top-k; emitted order is canonical text order, not
  frequency order.
- Abstract own records = 0; inclusive records = own zero + children, looked up
  as `(component.kind, child_name)` — only same-kind children are summed.
  Whether cross-kind hierarchy is possible is `unclear`; `children` itself can
  contain any kept component.
- Inclusive examples pool from descendants by property name, dedupe by canonical
  key, sort, truncate. Pooling mutates the observed value list when first used as
  a child; final results are deduped/limited, so normally benign but not purely
  functional.
- `build_document` returns `generated_by` (`module_id="meta_graph"`,
  `module_version`), `examples` (`method="approx_top_k"`, `limit`), `summary`
  (`node_components`, `edge_components`, `abstract_components`, `total_nodes`,
  `total_edges`, `location`, optional `html_location`), plus `nodes`/`edges`.
  Each component entry adds `counts` (`records`, `inclusive_records`,
  `bindings`, `declared_children`); each property gets `examples` only when
  `example_limit > 0`.
- Writes JSON with `sort_keys=True`, `indent=2`, `allow_nan=False`, final
  newline.
- If `include_html`, validates `html_relative_path`, sets
  `document["summary"]["html_location"]`, and writes `render(document)`.
- Returns `succeeded(context, dict(document["summary"]))`.
Rendering: `render` reads `service/_private/templates/meta_graph.html` and
`service/_private/static/d3.v7.min.js`, replaces `%%%D3%%%` and `%%DATA%%`,
embeds the document as JSON (`sort_keys`, `indent=2`, `allow_nan=False`), and
escapes `</` as `<\/`. Self-contained; no network.
Limits/ambiguities: static topology frozen at plan time; no runtime path
override (`runtime_fields=()`); executor `module_version` can differ from
planner `version` (default both `"2"`); `approx_top_k` set is sorted, not
frequency-ranked; counts are exact only for records reaching the executor;
path `..` detection is `Path`-based and platform-dependent (`unclear`
cross-platform).

## 8. Shared planning under `core/service/_private/planning`

### 8.1 `artifacts.py`

```python
ComponentDTO = NodeDTO | EdgeDTO
read_input(name, projection_relations, row_source_relations=None) -> Input
component_kind(component) -> Literal["node","edge"]
graph_components(blueprint) -> tuple[ComponentDTO, ...]
graph_record_components(blueprint) -> tuple[ComponentDTO, ...]
```
`read_input` precedence: row-source (declared `row_source.<name>`) > projection
(`projection.<name>`) > table (`table.<name>`). If a name is both projection and
row-source, row-source wins; whether that collision is possible is `unclear`.
`graph_components` = `(*graph.nodes, *graph.edges)`. `graph_record_components` =
those whose `name` is in the binding-component set, preserving graph order.

### 8.2 `plan.py`

```python
CORE_PLAN_KEY = "core.plan"
class CorePlan: ...  # fields in §2
ordered_projections(blueprint) -> tuple[ProjectionDTO, ...]
ordered_row_source_plans(blueprint) -> tuple[RowSourcePlanDTO, ...]
declaration_fields(blueprint) -> dict[str, tuple[ShapeField, ...]]
class CorePlanning:
    def plan(self, blueprint) -> CorePlan
def core_plan(blueprint, context) -> CorePlan
```
`ordered_projections` repeatedly picks the lexicographically smallest ready
projection whose sources do not intersect pending names; if none is ready it
raises `ValueError("projection dependency graph contains a cycle")`.
`ordered_row_source_plans` uses projection row sources then binding rows as
roots; DFS visits children before appending; skips `RowScanDTO`; deduplicates by
`row_source_key`.
`declaration_fields` maps each relation/projection to
`ShapeField(name, name, logical_type)`; row-source fields add
`plan_fields(plan, shapes)` and scanned shapes not already present.
`CorePlanning.plan` produces ordered projections, `table_relations`,
`kg_projection_<i>`, `kg_rowsource_<i>`, shapes, row-source fields, merged
relations and blueprint-order bindings. `core_plan` caches by `CORE_PLAN_KEY`
per `PlanContext`; it does not reset between planners.

### 8.3 `emission.py`

```python
sql_type_for(declared: LogicalTypeDTO) -> SqlType | None
sql_emitter(engine: SqlEmitter) -> SqlEmitter
instruction_emitter(engine: SqlEmitter) -> RelationSqlEmitter
expression_sources(expressions) -> set[str]
expression_field_sources(expressions) -> set[str]
projection_sources(projection) -> set[str]
binding_outputs(binding) -> dict[str, ExpressionDTO]
binding_sources(binding) -> set[str]
retarget_expression(expression, plan: RowSourcePlanDTO | None) -> ExpressionDTO
product_sql(outputs, relations, *, engine, shapes=None) -> str
expansion_scope(expression: OperationExpressionDTO) -> tuple[str, ...]
plan_product(outputs, relations, *, predicates=(), shapes=None) -> RelationPlan
```
`sql_type_for`: nullable -> recurse; unit -> its canonical name; array ->
`ArraySqlType(item)` or `None`; other -> `None`.
`projection_sources`: field refs from columns plus `_plan_sources(row_source)`
(scan sources, row-source key, plan expressions, recursive child plans).
`binding_sources`: all expressions from `binding_outputs` plus row-plan sources.
`retarget_expression`: no plan or shape source already equals the row-source key
-> unchanged; otherwise rewrite field refs from shape source to row-source key.
`product_sql`: calls `engine.emit(plan_product(...))`, requires an object
payload and non-empty string `sql`.
`plan_product`: errors on empty outputs; missing relation names -> `no
materialised relation for: ...`; more than one field-source relation ->
`a relational product requires one driving source; additional sources must be
introduced by an explicit lookup`; creates sorted `Scan(source, relation,
f"t{i}")`; walks expressions post-order; `expand` -> deduped `Expand(scope,
argument, f"expanded{n}")`; filters -> deduped `Filter(predicate,
"present"|"true")`; direct predicates appended last; returns
`RelationPlan(..., relations=dict(...), shapes=dict(...))`.
`expansion_scope`: only `expand` with one argument; field ref ->
`(relation, field, *path)`; `struct_field(expand)` with `name` -> recursive scope
+ name; else `("expression", sha256(canonical JSON).hexdigest())`.

### 8.4 Core SQL emitters
`projection_sql` drops `None` expressions, retargets to `projection.row_source`,
calls `product_sql`. `binding_sql` retargets `binding_outputs` to `binding.rows`,
emits product, wraps in `_kg_named` with `binding_rename_projection` (casts
declared property types), then `binding_guard_projection`. `row_source_sql` calls
`instruction_emitter(engine).emit_row_source(plan, relations, shapes)`.

## 9. Neutral relation plan and `SqlEmitter` contract
`distribution/service/internal/emission.py`.

```python
@dataclass(frozen=True, slots=True)
class Scan: source: str; relation: str; alias: str
@dataclass(frozen=True, slots=True)
class Expand: scope: tuple[str, ...]; expression: ExpressionDTO; alias: str
@dataclass(frozen=True, slots=True)
class Filter: expression: ExpressionDTO; mode: Literal["present","true"] = "present"
@dataclass(frozen=True, slots=True)
class RelationPlan:
    scans: tuple[Scan, ...]
    expands: tuple[Expand, ...]
    filters: tuple[Filter, ...]
    outputs: tuple[tuple[str, ExpressionDTO], ...]
    relations: Mapping[str, str] = {}
    shapes: Mapping[str, tuple[ShapeField, ...]] = {}
```
`Scan` reads one materialized relation under a plan-local alias; `Expand` fans
an array expression into rows under a stable scope; `Filter` keeps rows whose
expression is present or whose predicate is true; `relations` resolves lookup
targets without scanning; `shapes` gives top-level field shapes.

```python
@dataclass(frozen=True, slots=True)
class ArraySqlType: item: SqlType
@dataclass(frozen=True, slots=True)
class StructSqlType: members: tuple[tuple[str, SqlType], ...]
type SqlType = CanonicalTypeName | ArraySqlType | StructSqlType
```
`canonical_sql_type`: array -> `<item>[]`; struct -> `STRUCT(<name> <type>,...)`
(refuses empty members); unit -> `CANONICAL_SQL_TYPES[canonical]`; bare container
-> `ValueError`. Canonical SQL: `bool=BOOLEAN`, `int=BIGINT`, `float=DOUBLE`,
`str=VARCHAR`, `date=DATE`, `time=TIME`, `timestamp=TIMESTAMP`, `uuid=UUID`.
`NULL_GUARD_MACRO="_kg_nn"`.

```python
@runtime_checkable
class RelationSqlEmitter(Protocol):
    def relation_sql(self, plan: RelationPlan) -> str: ...
    def emit_row_source(self, plan: RowSourcePlanDTO,
                        relations: Mapping[str, str],
                        shapes: Mapping[str, tuple[ShapeField, ...]]) -> str: ...
@runtime_checkable
class SqlEmitter(Protocol):
    @property
    def kind(self) -> InstructionKind: ...
    @property
    def instruction_emitter(self) -> RelationSqlEmitter: ...
    def emit(self, plan: RelationPlan, context: Any = None) -> Instruction: ...
```
Contract: planner names no engine; it uses `engine.kind`. `product_sql` calls
`engine.emit` with no context and extracts `sql`; core adds `relation` separately.
Row-source SQL bypasses `emit` and uses `instruction_emitter.emit_row_source`.
`DuckDbSqlEmitter` implements the protocol with
`DEFAULT_SQL_KIND=InstructionKind("sql","duckdb")`; its payload is `{"sql":...}`
plus `relation` only when a context supplies one. Core imports
`distribution.service.internal.emission`, not DuckDB; guarded by
`tests/distribution/planners/test_planner_imports_no_pipeline.py`.

## 10. Execution

### 10.1 Instruction payload shapes

| Kind | Payload | Producer |
| --- | --- | --- |
| `("sql","duckdb")` (default) | `{"relation": str, "sql": str}` | row-source/projection/binding |
| `("aggregate","duckdb")` | `{"relation": str}` | records |
| `("deduplication","duckdb")` | `{"relation": str}` | dedup |
| `("merging","duckdb")` | `{"relation": str, "select": str}` | merging |
| `("conflict_findings","duckdb")` | `{"component": str, "field": str}` | conflict validation |
| `("conflict_report","default")` | `{"fail_on_error": bool}` | conflict validation |
| `("file","default")` | `{"relative_path": str}` | file |
| `("meta_graph","default")` | `{"relative_path", "example_limit", "include_html", "html_relative_path", "components"}` | meta-graph |
SQL kind is `engine.kind`, so a non-DuckDB emitter can change the first row.
`DuckDbExecutor` recognizes exactly its six kinds.

### 10.2 Claiming and dispatch
- Executor declares `kinds: tuple[InstructionKind, ...]`.
- `execute_plan` builds `by_kind`; duplicate kind ->
  `ValueError("duplicate executor for instruction kind ...")`; any plan kind
  missing -> `ValueError("no executor for instruction kind(s): ...")` before
  any step runs.
- Dispatch is exact equality on `step.instruction.kind`; no prefix/fallback.
- Executor declares `resources`; runtime builds a `ResourceView` with exactly
  those types. Missing resource -> error before execution; undeclared type ->
  `KeyError`.

### 10.3 Ordering
Compile/assembly: planners run in supplied tuple order; default toolchain inserts
DuckDB source before core and core before caller planners when unclaimed. Group
by `component_id`; one `Component` per group; group members must agree on
`version` and `runtime_fields`. Rank by component order, eager before deferred,
then declaration position (higher rank = earlier). Assemble open inputs to
outputs, refuse cycles, require every ordinary `Output` to be read; publications
exempt. Duplicate `StepId(component,name)` refused; empty names become
`step<position>` before identity check.
Runtime: fresh `EventBus`/`ResourceRegistry`, subscribe providers/listeners,
emit `PipelineStarted`; providers publish resources and executor views are built
from the snapshot. `_execute` runs waves: a step is ready when every producer of
every input opening completed. Ready steps run sequentially in plan order (no
parallelism). No ready step while pending -> `RuntimeError("workflow has a
dependency cycle")`. Each step gets `ExecutionContext` or
`DisruptedExecutionContext`; `SUCCEEDED`/`WARNING` feed downstream,
`FAILED`/`SKIPPED` disrupt; `skipped(context)` is the default disrupted policy.
Executor exceptions become failed outcomes with `exception_type`; listener errors
halt the pipeline.

### 10.4 Outcome/artifact rules
`succeeded(context,value)` emits only the first declared output.
`_validate_outcome` requires matching step id, a failure on `FAILED`, no duplicate
artifact names, no undeclared output, and exact artifact types.
`ConflictReportExecutor` builds custom outcomes and can emit a publication plus
forwarded outputs. `DuckDbExecutor` calls `service.engine.finish_step()` in
`finally`, even after an error. File/meta return `skipped` on disrupted context.

### 10.5 Idempotency
Step/component ids, relation names and file paths are deterministic for a fixed
blueprint/composition. A fresh run creates a fresh DuckDB engine in a new private
temp dir (`DuckDbResourceProvider`), so materialized names do not collide across
runs. Within one engine, `materialize` creates fixed-name table/view; re-running
the same step against the same engine would fail on the existing table. No retry,
upsert or step-level idempotency. File/meta overwrite (`"w"`/`write_text`), not
append; idempotent for same content/path across fresh runs. Row order is not
guaranteed, so byte-level idempotency is not promised. No dedup/merge state
between runs.

## 11. Tests

| Behavior | Path / representative tests |
| --- | --- |
| Core shares `core`/version 4/empty fields | `tests/distribution/planners/test_core_planner.py` / `test_core_planners_share_the_core_component` |
| Caller core planner replaces default group | same / `test_a_caller_supplied_core_planner_replaces_the_default_group` |
| Core emits source/projection/binding/aggregate | same / `test_the_core_planner_emits_every_step_shape` |
| Core assembled order preserved | same / `test_the_assembled_core_plan_keeps_the_step_order` |
| Source kind/payload keys/sorted | same / `test_source_steps_use_the_source_relation_instruction`, `test_source_steps_are_sorted_by_relation_name` |
| Projection/binding SQL kind/payload | same / `test_projection_and_binding_steps_use_sql` |
| Binding SQL has `_kg_binding_symbol` | same / `test_binding_sql_names_its_graph_symbol` |
| Aggregates deferred | same / `test_aggregate_steps_are_deferred` |
| Core uses injected emitter | `tests/distribution/planners/test_core_custom_emitter.py` / `test_core_planner_uses_the_supplied_instruction_emitter` |
| Dedup plan shape/input/output/payload | `tests/distribution/planners/test_dedup_merge_conflict_planners.py` / `DeduplicationPlannerTests` |
| Merge plan shape/payload/scope | same / `MergingPlannerTests` |
| Conflict findings/report shape/outputs | same / `ConflictValidationPlannerTests` |
| Unread dedup output refused | `tests/distribution/planners/test_plan_assembly.py` / `test_an_unread_deduplication_output_is_refused` |
| Dedup + file assembles | same / `test_a_consumer_lets_core_and_deduplication_assemble` |
| Component agreement/merge | `tests/distribution/planners/test_multi_planner_components.py` / both tests |
| DuckDB exact kinds | `tests/distribution/executors/test_duckdb_executor.py` / `test_kinds_are_the_exact_duckdb_instruction_set` |
| Dedup executor distinct | same / `test_deduplication_returns_distinct_rows` |
| Aggregate union | same / `test_aggregate_unions_every_input_relation` |
| Disrupted/unknown kind | same / `test_a_disrupted_context_is_skipped`, `test_an_unknown_kind_raises` |
| Conflict report cases | `tests/distribution/executors/targets/test_conflict_report.py` / three tests |
| File plan shape/publication | `tests/distribution/executors/targets/test_target_planners.py` / `FilePlannerTests.test_the_file_planner_emits_its_one_deferred_step` |
| File writes JSON Lines/summary | `tests/distribution/executors/targets/test_file_target.py` / `test_a_file_plan_writes_the_received_graph_records` |
| File path payload/runtime field | same / `test_the_runtime_path_replaces_the_compiled_path` (plan assertion only; no executed override) |
| Meta-graph plan shape | `tests/distribution/executors/targets/test_target_planners.py` / `MetaGraphPlannerTests.test_the_meta_graph_planner_emits_its_one_deferred_step` |
| Meta document counts/examples/HTML | `tests/distribution/executors/targets/test_meta_graph_target.py` / `test_the_meta_graph_document_contains_the_component_summary`, `test_disabling_html_writes_no_page` |
| Core no DuckDB import | `tests/distribution/planners/test_planner_imports_no_pipeline.py` / `test_the_core_module_does_not_import_duckdb` |
| No pipeline import in planners/targets/executors | three `test_*_imports_no_pipeline.py` files |
| Architecture/layout/blueprint readers | `tests/test_architecture.py` |
Coverage gaps: no direct execution test for `MergingPlanner` + `DuckDbExecutor`;
no direct `_conflict_findings` execution test (only report executor); file runtime
override test does not execute an override; no config error-path tests; no
projection-cycle or row-source ordering tests; no dedup/merge tests for arrays,
structs, nulls or `_kg_binding_symbol`.

## 12. Surprising/ambiguous/doc-code disagreements
1. **Edge endpoint conflicts are invisible to validation.** The planner iterates
   `component.properties` only; `source_build_key`/`target_build_key` are binding
   outputs, not properties. A same-key edge with different endpoints passes
   validation and merging minimizes the endpoint. Docs say validation checks
   “every property of every bound component” and do not mention endpoints
   (`docs/concepts/planners-and-executors.md`,
   `docs/reference/planners-and-executors.md`).
2. **Merging minimizes endpoint keys too.** `fields = ["source_build_key",
   "target_build_key", *props]` for edges. Docs say merging keeps the minimum
   “for every property”; they omit endpoint keys
   (`modules/merging/service/_private/planner.py`).
3. **Merging has no type preflight.** Arrays/structs are allowed but `min(...)`
   is emitted for every property; unsupported types would fail at runtime, not
   plan time. `docs/reference/types.md` says BLOB is refused because “merge and
   dedup cannot carry it,” implying type constraints, but the merge planner does
   not enforce them (`unclear` for every nested type).
4. **Dedup includes `_kg_binding_symbol`.** `SELECT DISTINCT *` includes the
   symbol, so two bindings with otherwise identical rows do not dedup against
   each other. Docs say dedup removes rows “identical in every column, including
   the build key and all properties” but do not call out the symbol
   (`docs/reference/planners-and-executors.md`;
   `modules/duckdb/service/_private/executor.py`).
5. **File target overwrites `type`/`kind`/`build_key`.** `record.update(...)`
   silently replaces same-named component properties. No reserved-name check was
   found (`modules/file/service/_private/executor.py`).
6. **Core `binding_outputs` has the same collision risk.** `{"build_key":
   identity}` then `update(dict(properties))`; a property named `build_key`
   replaces the identity expression. `validate_binding` checks only non-empty
   and unique names. Whether topology forbids it is `unclear`.
7. **Conflict validation can publish a report on a failed run.** `FAILED` with
   `fail_on_error=True` still returns the report artifact; the runtime records
   returned artifacts before failure classification. Docs say a finding “fails
   the run” but do not explicitly say the report remains published
   (`modules/conflict_validation/service/_private/executor.py`).
8. **Rewriting planner outputs must be consumed.** Dedup/merge/conflict produce
   ordinary `Output`s (`distinct`, `merged`, `validated`); with no later reader,
   assembly fails `nothing reads ...`. A “validator only” composition does not
   run without an output/rewriting planner. The dedup case is tested in
   `test_an_unread_deduplication_output_is_refused`.
9. **`RecordsPlanner` accepts an unused engine.** It stores `self._engine`, but
   `aggregation_steps` does not use it. Only three core planners emit SQL.
10. **`read_input` prefers row-source over projection.** If a name exists in both
    mappings, the row-source branch wins. The helper does not diagnose the
    collision; whether the blueprint prevents it is `unclear`.
11. **Lowercased relation names can collide.** Aggregate/dedup/merge use
    `.lower()` on component names; case-only names would share a relation name
    (`unclear` whether topology permits).
12. **Meta-graph examples are not emitted in frequency order.** The query uses
    `approx_top_k`, then sorts canonical values and truncates; the set is
    approximate top-k but the list is lexicographic. Docs say “most common values
    with `approx_top_k`,” which can be read as frequency order.
13. **Meta-graph inclusive counts assume same-kind children.** `_inclusive_records`
    looks up `(component.kind, child_name)`; cross-kind children are ignored though
    `children` includes them. Docs say categories sum own + descendants; if
    cross-kind hierarchy is possible, code undercounts (`unclear`).
14. **Module docstring says “five planners” for core.** `modules/__init__.py`
    says five; code/docs say four, the fifth being `DuckDbSourcePlanner` (`duckdb`).
15. **Conflict validation checks nullable properties too.** It counts non-null
    values for every declared property; a nullable property with two distinct
    non-null values can produce a finding. Docs say “every property,” but the
    finding name reads “only required/non-null.”