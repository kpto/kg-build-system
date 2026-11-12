# Survey: `kg_build_system.kernel` and `kg_build_system.distribution.model`

Read-only survey of `/home/paul/Repos/kg-build-system`. Scope:
`kg_build_system/kernel/**`, `kg_build_system/__init__.py`,
`kg_build_system/api.py`, `kg_build_system/distribution/model/**`. Nothing was
modified or executed. Concrete graph-linker behaviour is out of scope but is cited
where the kernel delegates to it.

---

## 1. File/package map

### Kernel root

| File | Responsibility |
| --- | --- |
| `kernel/__init__.py` | Re-exports the public model and service; literal `__all__` (8-124). |
| `kernel/model/__init__.py`, `kernel/service/__init__.py` | Empty facades (1-4 each); the service docstring is stale (see §7). |

### `kernel/model/public`

| File | Responsibility |
| --- | --- |
| `key.py` | `Key`: hierarchical immutable identity; prefix/glob/document helpers. |
| `symbol.py` | `Declaration`, `Symbol`, `SymbolContext`, `SymbolRef`. |
| `language.py` | `Language`, `Namespace`, `ReferenceResolver`, `RenderContext`, `SourceFragment`. |
| `workflow.py` | Plan values: identities, artifact types/patterns, instructions, ports, `Step`, `Connection`, `Component`, `WorkflowPlan`. |
| `runtime.py` | Execution values: configuration, resource view, statuses, outcomes, contexts, publication, report. |
| `events.py` | `ResourceRegistry`, six pipeline events, `PipelineEvent`, `Listener`, `EventBus`. |
| `types/model.py` | Canonical logical types (`UnitType`, `CustomType`, `StructType`, `ArrayType`, `NullableType`) and unit names. |
| `types/markers.py` | Authoring markers/aliases: `CustomDataType`, `Shape`, `Struct`, `Array`, `Nullable`, `Date`, `Time`, `Timestamp`, `Uuid`. |
| `types/__init__.py`, `public/__init__.py` | Re-export the model. |

### `kernel/model/internal` and `_private`

| File | Responsibility |
| --- | --- |
| `internal/json.py` | `FrozenJson`, `FrozenObject`, `freeze_json`, `thaw_json`. |
| `internal/types/dto.py` | DTO twins of canonical types; `LogicalTypeDTO`, `NonNullableLogicalTypeDTO`. |
| `internal/__init__.py`, `internal/types/__init__.py` | Re-export DTOs. |
| `_private/types/normalization.py` | `normalize_type`: Python annotation -> canonical type. |
| `_private/types/codec.py` | `type_to_dto`, `type_from_dto`, `type_to_document`, `type_from_document`. |
| `_private/types/validation.py` | Nullability/array/scalar/graph-property predicates. |
| `_private/types/values.py` | `canonical_value_text`. |
| `_private/**/__init__.py` | Empty “not an import surface” facades. |

### `kernel/service/public` and `internal`

| File | Responsibility |
| --- | --- |
| `service/public/pipeline.py` | `Linker`, `PlanContext`, `Planner`, `Executor`, `StepExecutor`, `Resource`, `ResourceProvider`, `Runtime`, `Toolchain`. |
| `service/public/runtime.py` | `WorkflowRuntime`: thin wrapper over the private scheduler. |
| `service/public/__init__.py` | Re-exports the protocols and `WorkflowRuntime`. |
| `service/internal/pipeline.py` | `build_model`, `compile_model`, `execute_plan` wrappers with function-local private imports. |
| `service/internal/workflow_codec.py` | Plan document wrappers. |
| `service/internal/report_codec.py` | Report document wrapper. |
| `service/internal/types/functions.py` | Twelve type functions (codecs, normalization, predicates, canonical text). |
| `service/internal/{__init__,types/__init__}.py` | Re-exports. |

### `kernel/service/_private`

| File | Responsibility |
| --- | --- |
| `_private/pipeline.py` | Actual build (delegate to linker), compile (group planners, assemble), execute (kind map/coverage, default config). |
| `_private/assembly.py` | Port expansion, rank policy, wiring, cycle/ambiguity refusal, `WorkflowPlan` construction; `AssemblyError`. |
| `_private/runtime.py` | Scheduler, resource views, input classification, wave execution, outcome validation, failure classification, report, `WorkflowRuntime`, `succeeded`, `skipped`. |
| `_private/workflow_codec.py` | Plan encode/decode using `Key` arrays. |
| `_private/report_codec.py` | Report encode only. |

### `distribution/model`

| File | Responsibility |
| --- | --- |
| `public/refs.py` | Role-typed `SymbolRef` wrappers: `Ref`, `NodeRef`, `EdgeRef`, `RelationRef`, `AssetRef`, `FieldRef`, `PropertyRef`, `OperationRef`, document helpers. |
| `public/artifacts.py` | `CoreArtifactTypes`, `GraphRecordArtifact`, `graph_record_artifact`. |
| `public/asset_tables.py` | `AssetColumn`, `AssetTable` planning values. |
| `public/paths.py` | `validate_relative_path`. |
| `public/runtime.py` | `BuildRuntime` and `to_configuration()`. |
| `public/__init__.py` | Re-exports refs/artifacts/asset tables/`BuildRuntime`; not paths. |
| `internal/canonical_types.py` | `ARRAY_CANONICAL`, `STRUCT_CANONICAL`, `CanonicalTypeName`. |
| `_private/refs.py` | Reference document codec: `ROLES`, `role_types`, `split_document`, `encode_ref`, `decode_ref`. |
| `model/__init__.py`, `internal/__init__.py`, `_private/__init__.py` | Facades. |

### Package root

| File | Responsibility |
| --- | --- |
| `kg_build_system/__init__.py` | Lazy facade over authoring APIs, languages, `BuildRuntime`, `WorkflowPlan`, `WorkflowReport`, canonical types; `_GROUPS` + `__getattr__`. |
| `kg_build_system/api.py` | Composition root: `DEFAULT_LANGUAGES`, `DEFAULT_EXECUTORS`, `default_toolchain`, `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile`, `execute`. |

---

## 2. Public vocabulary

### 2.1 Identity / frontend

| Name | Signature | Behaviour |
| --- | --- | --- |
| `Key` | `Key(segments: tuple[str,...])`; `child`, `starts_with`, `matches`, `to_document`, `from_document`, `__str__` | Immutable/hashable; empty key is root; `str` joins with `/`; document is a string array (`key.py:14-115`). |
| `Namespace` | `values() -> Sequence[object]` | Caller-supplied authoring values; kernel does not inspect them (`language.py:20-48`). |
| `RenderContext` | empty protocol | Opaque renderer context (`language.py:51-64`). |
| `ReferenceResolver` | `get_identity(value) -> SymbolRef \| None` | Resolves authoring value to symbol; supplied by linker (`language.py:67-90`). |
| `Language` | `name`; `discover_declarations`, `compute_key`, `get_kind`, `get_identity`, `get_references`, `transcribe`, `render` | Frontend. `name` is written into every `SymbolRef`; `transcribe` is the required per-declaration path (`language.py:93-232`). |
| `Declaration` | `Declaration(value: Any)` | One authoring object; carries no key (`symbol.py:40-56`). |
| `Symbol` | `Symbol(key: Key, kind: str, value: Any, references: tuple[SymbolRef,...]=())` | Linked unit; value is the language's frozen representation (`symbol.py:59-79`). |
| `SymbolRef` | `SymbolRef(language: str, key: Key)`; `__str__ = "language:key"` | Typed symbol identity (`symbol.py:17-37`). |
| `SymbolContext` | `SymbolContext(symbols: Mapping[SymbolRef, Symbol]={})`; `get_symbol`, `get_value` | Copies input and wraps in `MappingProxyType`; unknown reference raises `KeyError` (`symbol.py:82-130`). |
| `SourceFragment` | `SourceFragment(kind: Literal["inline","declaration"], body, imports=())` | Rendered source; `kind` not runtime-validated (`language.py:235-254`). |

### 2.2 Plan vocabulary

| Name | Signature | Behaviour |
| --- | --- | --- |
| `JsonValue` | recursive scalar/list/dict alias | Payload type, no runtime validation (`workflow.py:18-20`). |
| `OpeningDirection` | `StrEnum`: `INPUT`, `OUTPUT` | Direction is part of opening identity (`workflow.py:23-38`). |
| `StepId` | `StepId(component, name)`; `.key` | Non-empty slash-free strings; dots allowed in `name`; `version` is not part of identity (`workflow.py:41-76`). |
| `OpeningId` | `OpeningId(step, direction, name: Key \| str)`; `.key` | Type/emptiness/slash checks; string name becomes one segment; direction distinguishes otherwise equal names (`workflow.py:79-135`). |
| `ArtifactType` | `ArtifactType(key: Key)`; `of(namespace,*name)`; `.namespace`, `.name` | Concrete: >=2 segments, no wildcards/slashes; dotted `name` is display only (`workflow.py:138-200`). |
| `ArtifactPattern` | `ArtifactPattern(key: Key)`; `of`, `.is_pattern`, `.matches(type)`, `.exact()` | Pattern key; final `**` only; `exact()` refuses wildcard (`workflow.py:203-295`). |
| `InstructionKind` | `InstructionKind(operation, engine)`; `.key` | Exactly two segments; exact comparison (`workflow.py:298-333`). |
| `Instruction` | `Instruction(kind, payload: JsonValue)` | Opaque payload read by the matching executor (`workflow.py:336-353`). |
| `Input` | `Input(type: ArtifactPattern, opening_name: Key \| None = None, declared_name: str = "")` | `opening_name` nullable until assembly; `declared_name` is the executor map key (`workflow.py:356-376`). |
| `Output` / `Publication` | `(type: ArtifactType, opening_name: Key \| None = None)` | Output is produced; publication is also a report artifact and remains addressable downstream (`workflow.py:379-411`). |
| `Given` | `Output \| Publication` | Union alias (`workflow.py:414`). |
| `Step` | `Step(component, name, inputs, outputs, instruction, assembly_preference="eager")`; `.id` | Scheduled instruction plus ports; preference is `"eager"`/`"deferred"` (`workflow.py:417-453`). |
| `step_id`, `input_opening`, `output_opening` | `Step -> StepId`, `(Step, Input) -> OpeningId`, `(Step, Output\|Publication) -> OpeningId` | Opening helpers raise `ValueError` when the opening is unresolved (`workflow.py:456-498`). |
| `Connection` | `Connection(input: OpeningId, output: OpeningId)` | Requires input direction INPUT and output direction OUTPUT (`workflow.py:501-526`). |
| `RuntimeField` | `RuntimeField(key, description, required=True, value_type="string", secret=False)` | Operator-supplied component value (`workflow.py:529-546`). |
| `Component` | `Component(id, version, runtime_fields=())` | Planner group identity; version/fields published once (`workflow.py:549-566`). |
| `WorkflowPlan` | `WorkflowPlan(components, steps, connections=(), provenance: JsonValue\|None=None)` | Assembled DAG; constructor does no validation (`workflow.py:569-588`). |

### 2.3 Runtime vocabulary

| Name | Signature | Behaviour |
| --- | --- | --- |
| `RuntimeConfiguration` | `(output_directory, working_directory, temporary_directory=None, credentials={}, component_configuration={}, provider_configuration={})` | Per-run settings; provider config is keyed by provider id, not plan component (`runtime.py:27-60`). |
| `ResourceView` | `(resources: Mapping[type, Any])`; `get(resource: type[T]) -> T` | Exact-type lookup; undeclared type raises `KeyError` (`runtime.py:63-95`). |
| `StepStatus` | `StrEnum`: `SUCCEEDED`, `WARNING`, `FAILED`, `SKIPPED` | First two continue; last two disrupt (`runtime.py:98-115`). |
| `Failure` | `(message, step_id, exception_type=None)` | Why a step failed (`runtime.py:118-133`). |
| `Artifact` | `(output_name: Key, type: ArtifactType, value)`; `opening(step)` | Stores no step; derives output opening (`runtime.py:136-168`). |
| `StepOutcome` | `(step_id, status, artifacts=(), failure=None)`; `opening(artifact)` | One step result (`runtime.py:171-204`). |
| `ContinuableInput` | `(output_id, status: Literal[SUCCEEDED,WARNING], artifact)` | Consumable upstream result; literal not enforced (`runtime.py:207-229`). |
| `DisruptingInput` | `(output_id, status: Literal[FAILED,SKIPPED], artifact, failure)` | Blocking upstream result; literal not enforced (`runtime.py:232-255`). |
| `ExecutionContext` | `(step, runtime_configuration, inputs: Mapping[str, tuple[ContinuableInput,...]], resources, logger)`; `.step_id`, `.component` | Normal step context; `runtime_configuration` is only the component's mapping (`runtime.py:258-294`). |
| `DisruptedExecutionContext` | same plus `disruptions: tuple[DisruptingInput,...]`; inputs may mix both | Context for a disrupted step (`runtime.py:297-335`). |
| `PublishedArtifact` | `(opening: OpeningId, type: ArtifactType, value)` | Final workflow artifact (`runtime.py:338-363`). |
| `WorkflowReport` | `(published_artifacts, recovered_failures, unresolved_failures, provenance)`; `.succeeded` | `succeeded == not unresolved_failures` (`runtime.py:366-394`). |

### 2.4 Events / resources / service

| Name | Signature | Behaviour |
| --- | --- | --- |
| `ResourceRegistry` | `add(type, value)`, `get(type)`, `snapshot()` | Exact-type live resources; duplicate type raises (`events.py:21-82`). |
| `PipelineStarted` | `(plan, configuration, resources)` | Providers add resources here (`events.py:85-100`). |
| `StepStarted` / `StepFinished` | `(step_id, detail="")` / `(outcome, detail="")` | Step lifecycle (`events.py:103-134`). |
| `StepLogged` | `(step_id, level, message)` | Per-step log event (`events.py:137-152`). |
| `PipelineFinished` / `PipelineHalted` | `(report)` / `(error: BaseException)` | Terminal events (`events.py:155-184`). |
| `PipelineEvent`, `Listener` | union alias; `Callable[[PipelineEvent], None]` | Event taxonomy; alias ignores `on_event` objects (`events.py:187-194`). |
| `EventBus` | `.failure`, `subscribe(listener)`, `emit(event)` | Subscription-order delivery; first listener error recorded and re-raised (`events.py:197-259`). |
| `Linker[ModelT]` | `link(languages, namespace) -> ModelT` | Sole build hook; owns roots/closure/order/transcription/assembly (`pipeline.py:37-63`). |
| `PlanContext` | `(runtime_configuration={}, shared: MutableMapping={})` | Frozen wrapper with mutable per-compile scratch space (`pipeline.py:66-88`). |
| `Planner[ModelT]` | `component_id`, `version`, `runtime_fields`, `plan(model, context) -> Sequence[Step]` | Emits steps for a component; groups may share a component (`pipeline.py:91-125`). |
| `Executor` | `kinds`, `execute(context, instruction) -> StepOutcome` | Executes one exact kind (`pipeline.py:128-159`). |
| `StepExecutor` | `Executor` + `resources: tuple[type,...]=()` | Declares exact resource types (`pipeline.py:162-181`). |
| `Resource` | `close()` | Live capability; provider owns disposal (`pipeline.py:184-209`). |
| `ResourceProvider` | `on_event(event)` | Opens on start, disposes on finish/halt (`pipeline.py:212-239`). |
| `Runtime` | `execute(plan, executors: Mapping[InstructionKind, StepExecutor], *, configuration, listeners=())` | Schedule/dispatch (`pipeline.py:242-272`). |
| `Toolchain[ModelT]` | `languages`, `linker`, `runtime=None`, `planners=()`, `executors=()`; `build`, `compile`, `execute`, `with_planners`, `with_executors` | Kernel composition surface (`pipeline.py:275-392`). |
| `WorkflowRuntime` | `(providers=())`; `execute(...)` | Default `Runtime`; fresh private implementation per call (`service/public/runtime.py:16-60`). |

### 2.5 Canonical types

`UnitType(name)`, `CustomType(module, qualname)`, `StructType(module, qualname)`,
`ArrayType(item)`, `NullableType(value)`; aliases `LogicalType`,
`NonNullableLogicalType`; constants `BOOL`/`INT`/`FLOAT`/`STR`/`DATE`/`TIME`/
`TIMESTAMP`/`UUID`; names `UnitTypeName`/`CANONICAL_UNIT_NAMES`/
`TEXT_CANONICAL_UNIT_NAMES`; predicate `is_canonical_unit_name`
(`types/model.py:21-150`). Markers: `CustomDataType`, `Shape`, `Struct`,
`Array[T]`, `Nullable[T]`, `Date`, `Time`, `Timestamp`, `Uuid`
(`types/markers.py:22-93`). DTOs: `UnitTypeDTO`, `CustomTypeDTO`, `StructTypeDTO`,
`ArrayTypeDTO`, `NullableTypeDTO` (`internal/types/dto.py:21-101`).

Rules: units must be canonical; custom/struct need non-empty module+qualname;
nullables cannot nest. Functions: `type_to_dto`, `type_from_dto`,
`type_to_document`, `type_from_document`, `normalize_type`, `is_nullable`,
`non_nullable`, `array_item`, `require_non_nullable`, `require_scalar`,
`require_graph_property`, `canonical_value_text`
(`types/model.py:60-136`; `service/internal/types/functions.py:16-218`).

### 2.6 Distribution model

| Name | Signature | Behaviour |
| --- | --- | --- |
| `Ref` | `Ref(language: str \| SymbolRef, key: Key \| None = None)`; `.symbol`, `.role`, `.key`, `.language`, `.name`, `to_document`, `from_document` | Role wrapper over `SymbolRef`; equality/hash use only the symbol (`refs.py:32-142`). |
| `NodeRef`, `EdgeRef`, `RelationRef`, `AssetRef`, `FieldRef`, `PropertyRef`, `OperationRef` | subclasses; roles `node`, `edge`, `relation`, `asset`, `field`, `property`, `operation` | One role per blueprint declaration kind (`refs.py:145-315`). |
| `FieldRef.owner/.relation/.field`; `PropertyRef.component/.property` | properties | Split final key segment at last dot (`refs.py:229-299`). |
| `ref_to_document`, `ref_from_document` | `(Ref) -> list[str]`, `(Any) -> Ref` | Document `[language, role, *key]` (`refs.py:318-351`). |
| `GraphRecordArtifact` | `(kind: Literal["node","edge"], component)` | Decoded core graph record; kind not runtime-validated (`artifacts.py:16-28`). |
| `CoreArtifactTypes` | `graph_records`, `binding`, `table`, `projection`, `row_source` | Builders under `core/graph/...`, `core/binding/...`, `core/data/...` (`artifacts.py:31-107`). |
| `graph_record_artifact` | `(ArtifactType) -> GraphRecordArtifact \| None` | Exactly four segments, prefix `core/graph`, kind node/edge (`artifacts.py:110-133`). |
| `AssetColumn`; `AssetTable` | `(name, logical_type)`; `(asset, relation, relation_name, columns)` | Planning values for asset-backed relations (`asset_tables.py:17-50`). |
| `validate_relative_path` | `(value, *, context) -> None` | Rejects empty, absolute and `..` paths (`paths.py:7-15`). |
| `BuildRuntime` | fields: credentials, component/provider configuration, output/working/temporary dirs, DuckDB storage/threads/memory/compression; `to_configuration()` | Author build settings; resolves relative working dir under output at construction; always emits a `duckdb` provider entry (`distribution/model/public/runtime.py:15-108`). |
| `ARRAY_CANONICAL`, `STRUCT_CANONICAL`, `CanonicalTypeName` | `"array"`, `"struct"`, `UnitTypeName \| Literal["array","struct"]` | Distribution container names (`internal/canonical_types.py:14-19`). |

### 2.7 Package root / API

`__getattr__` lazily imports from `_GROUPS` and caches (`kg_build_system/__init__.py:246-256`).
`default_toolchain(*, planners=(), executors=None, engine=None)`,
`DEFAULT_TOOLCHAIN`, `create_blueprint(*, namespace_path=None, bindings=(), languages=None)`,
`compile(*, blueprint=None, namespace_path=None, bindings=None, planners=(), toolchain=None, engine=None)`,
`execute(plan, *, output_directory, runtime=None, toolchain=None, monitor=None)`
(`api.py:76-284`). The root exports authoring names, languages, `GraphBlueprint`,
`BuildRuntime`, `WorkflowPlan`, `WorkflowReport`, canonical types; it does **not**
export kernel protocols (`kg_build_system/__init__.py:150-243`).

### 2.8 `Extension`

No `Extension` class, protocol, alias or export exists in the scope. A search of
the kernel package finds nothing; `kernel/__init__.py:103-124` does not list it.
`ARCHITECTURE.md:29-30` still lists `Extension` in `service/public/pipeline.py`.
Treat it as stale documentation; the real extension points are the protocols in
§2.4/§5. Whether it is removed or reserved is `unclear`.

---

## 3. Lifecycle: build -> link -> transcribe -> plan -> execute

`Toolchain` exposes three non-overlapping verbs (`pipeline.py:302-368`).

**1. Compose.** `api.compile`/`execute` choose `DEFAULT_TOOLCHAIN` or a supplied
toolchain; supplied planners are appended with
`toolchain.with_planners((*toolchain.planners, *planners))` (`api.py:211-221`).
`default_toolchain` composes default languages, `BlueprintLinker`, optional
`DuckDbSourcePlanner`, four core planners (unless a planner claims `"core"`),
default executors, and `WorkflowRuntime(providers=(RuntimeResources(),
DuckDbResourceProvider()))` (`api.py:62-121`).

**2. `build(namespace) -> ModelT`.** `Toolchain.build` calls
`build_model(languages, linker, namespace)`; the private function is exactly
`linker.link(tuple(languages), namespace)` (`pipeline.py:302-315`;
`_private/pipeline.py:24-28`). The kernel performs no ordering, duplicate check,
closure, transcription or assembly; its docstring assigns those to the linker
(`pipeline.py:303-307`). The model is opaque (`ModelT` unconstrained).

**3. Link/transcribe (concrete graph path, out of scope).** `BlueprintLinker` ->
`link_blueprint`:

1. Refuse duplicate language names, missing required languages, unknown roots
   (`link.py:175-192`).
2. Index each language's `discover_declarations` + `compute_key`; duplicate key
   within a language refused (`link.py:66-80`, `194-199`).
3. Build `_LanguageResolver`: ask each language `get_identity(value)`; more than
   one claimant raises (`link.py:46-64`, `200-202`).
4. Resolve direct edges with `language.get_references(declaration.value,
   resolver)`; unknown reference refused (`link.py:203-217`).
5. Select roots (`None` = every language) and walk the reachable closure
   (`link.py:219-232`).
6. Order dependencies-first by DFS; a `state == 1` revisit is a reference cycle
   (`link.py:234-250`).
7. Transcribe only reachable declarations, in order:
   `language.transcribe(declaration, SymbolContext(symbols))`; require
   `symbol.key == reference.key`; replace `references` with the resolved direct
   edges (`link.py:252-265`).
8. Assemble the graph model from DTO-typed symbols and validate it
   (`link.py:108-156`).

Fields carried: `Declaration.value`; `Symbol.key/kind/value/references`;
`SymbolContext.symbols`; `SymbolRef.language/key`; `Language.name`.

**4. `compile(model) -> WorkflowPlan`.** `Toolchain.compile` calls
`compile_model(planners, model, PlanContext())` (`pipeline.py:317-333`).
`compile_model` (`_private/pipeline.py:31-75`):

- group planners by `component_id` in first-seen order;
- publish one `Component(id, first.version, tuple(first.runtime_fields))`;
- refuse disagreement on `version` or `runtime_fields`;
- call `planner.plan(model, context)` and overwrite `step.component` with the
  group id;
- refuse `PlanContext.runtime_configuration` keys not matching a group;
- call `assemble_plan(contributions)`.

Assembly phases (`assembly.py`):

| Phase | Functions | Rule |
| --- | --- | --- |
| Components | `_validate_components` (170-175) | Component ids unique. |
| Steps | `_declare_steps` (178-202) | `StepId(component.id, name)`; empty name -> `step{N}`; duplicate id refused. |
| Rank | `derive_ranks` (308-326) | component order, eager before deferred, declaration position, key segments; `rank = total-index`, so greater runs earlier. |
| Outputs | `_build_outputs` (205-241) | name defaults to `output`; duplicate names within a step refused; `must_read` only for `Output`. |
| Inputs | `_build_inputs` (244-284) | `declared_name or "input"`; open pattern expands per matching available type to `Key((declared_name, *type.segments))`; exact pattern gets `Key((declared_name,))`; duplicate names refused. |
| Index | `_index_ports` (287-305) | by exact type; scan order `(-rank, sequence)`. |
| Wire | `_next_unavoidable` (476-491), `_next_justified` (494-503) | connect sole writer/reader first, then the first justified port in scan order. |
| Justify | `_conclude` (430-473) | refuse no writer/all-cyclic/UNKNOWN role; choose highest-rank earlier endofunctor; else sole producer; refuse multiple producers. |
| Complete | `_complete` (506-513) | every input fed, every `Output` read. |
| Define | `_define` (541-579) | resolved steps/connections; inputs become exact `ArtifactPattern` + resolved opening; provenance passed through. |

`_Wiring.connect` refuses an already-fed port and maintains transitive
reachability for `closes_cycle` (`assembly.py:112-156`). `_takes_type` classifies an
output’s producing step as `ENDOFUNCTOR` (a downstream step takes the same type),
`PRODUCER` (nothing upstream takes it), or `UNKNOWN` (an upstream input is unfed)
(`assembly.py:357-394`). Refusals are `AssemblyError(ValueError)` with a
multi-line explanation (`assembly.py:40-41`, `516-530`).

Fields carried: `Planner.component_id/version/runtime_fields`, `PlanContext.shared`,
`Step.*`, `WorkflowPlan.components/steps/connections/provenance`.

**5. `execute(...)`.** `Toolchain.execute` refuses `runtime is None`
(`pipeline.py:335-368`) and calls `execute_plan`
(`_private/pipeline.py:78-119`):

1. Build `Mapping[InstructionKind, StepExecutor]`; duplicate kind refused.
2. Refuse a plan instruction kind with no executor, before any step.
3. Use the supplied `RuntimeConfiguration`, else construct one from
   `output_directory` with working directory `output_directory/_workdir`.
4. Call `runtime.execute(...)`.

`WorkflowRuntime.execute` (`_private/runtime.py:624-674`):

- fresh `EventBus` + `ResourceRegistry`; subscribe providers **before** listeners;
- emit `PipelineStarted(plan, configuration, resources)`;
- build one `ResourceView` per distinct executor from `resources.snapshot()`,
  refusing a missing declared type (`93-113`);
- validate/index the plan with `schedule(plan)` (`184-233`);
- refuse unknown `component_configuration` keys;
- `_execute` (`515-545`) runs waves of steps whose connected producers completed;
  no ready step with work left -> `RuntimeError("workflow has a dependency cycle")`;
- `_classify` (`591-600`) and `_report` (`603-621`) build the report;
- emit `PipelineFinished(report)` or, on any `BaseException`, `PipelineHalted(error)`
  and re-raise.

Per-step (`_execute_step`, `404-476`): emit `StepStarted`; `_gather_inputs`
(`308-352`) follows each input’s connected sources and classifies producer status as
`ContinuableInput` or `DisruptingInput`, keyed by `declared_name`; validate the
component’s runtime configuration (`236-283`); choose
`ExecutionContext`/`DisruptedExecutionContext`; call the executor; convert an
ordinary exception to a `FAILED` outcome with `Failure(str(error), id,
type(error).__name__)`; validate the outcome (`355-401`); record artifacts under
`artifact.opening(step_id)`, outcomes, and active failures (`479-504`); emit
`StepFinished`.

Failure/record semantics: `FAILED` -> inherited failures ∪ own; `SKIPPED` ->
inherited; `SUCCEEDED`/`WARNING` -> empty (`492-501`). Publications are the output
openings of every `Publication` in plan order (`216-225`). `unresolved` is the
union of active failures at publishing steps; `recovered` is every other recorded
failure; `WorkflowReport.succeeded == not unresolved_failures` (`548-600`).

**6. Report writing (composition root only).** `api.execute` creates the output
directory, replaces `BuildRuntime.output_directory` with it, converts to
`RuntimeConfiguration`, writes `workflow_plan.json` before execution, resolves the
monitor, calls `toolchain.execute`, then writes `build_report.json`
(`api.py:249-284`). The kernel itself touches no filesystem path.

---

## 4. Invariants and rules

**Identity**

- Key segments are chosen by the language; the kernel compares/descends only
  (`key.py:1-6`).
- `starts_with` treats the empty key as a prefix of every key (`key.py:45-59`).
- `matches` uses `fnmatchcase` per segment; final `**` matches zero or more
  remaining; without `**`, lengths must match (`key.py:61-81`).
- `StepId` excludes `Component.version`; component/name cannot contain `/`, dots
  stay inside one segment (`workflow.py:41-76`).
- `OpeningId` includes direction, so equal input/output names are distinct; name
  segments cannot be empty or contain `/` (`workflow.py:79-135`).
- `ArtifactType` is concrete (>=2 segments, no `*?[`); `ArtifactPattern` may be
  exact or wildcarded with `**` final only (`workflow.py:138-295`).
- `InstructionKind` is exactly two segments and exact-comparison only
  (`workflow.py:298-333`).
- Every identity crossing a planner/executor/runtime/codec boundary is a role type
  over `Key`; formatted strings are display only (`workflow.py:1-9`).

**Declarations / linking**

- `Declaration` has no key; `Language.compute_key` assigns it
  (`symbol.py:40-56`; `language.py:148-157`).
- Keys are unique within one language; the concrete linker refuses duplicates
  (`link.py:66-80`).
- `get_identity` may return `None`; the concrete resolver refuses multiple
  claimants (`language.py:169-181`; `link.py:46-64`).
- `get_references` returns direct edges only; closure is the linker’s job
  (`language.py:183-198`).
- `transcribe` receives dependencies-first symbols and only reachable declarations;
  the produced key must equal the indexed key (`language.py:200-218`;
  `link.py:252-262`).
- Duplicate language names, duplicate declaration keys, unknown references and
  cycles are linker responsibilities, not kernel checks (`pipeline.py:303-307`;
  `link.py:175-192`, `66-80`, `203-217`, `234-250`).
- `SymbolContext` is read-only after construction; unknown refs raise `KeyError`
  (`symbol.py:101-130`).
- `render` is not called by the linker (`language.py:220-232`; `link.py` has no
  render call).

**Planning / assembly**

- Planners sharing a component must agree on `version` and `runtime_fields`; the
  first planner supplies the published values (`_private/pipeline.py:44-62`).
- Every step gets the group’s `component_id`; the planner’s field is replaced
  (`_private/pipeline.py:63-67`).
- Compile-time config keys must name real groups (`_private/pipeline.py:68-74`).
- Component ids unique; duplicate step ids refused; empty names resolve before the
  duplicate check, so assembly is the single authority (`assembly.py:170-202`).
- Per step, output names and input opening names are unique
  (`assembly.py:215-233`, `252-269`).
- An open input creates one port per matching available type; the port name is the
  declared name followed by the full type segments (`assembly.py:254-279`).
- Every input must be fed and every `Output` (not `Publication`) read
  (`assembly.py:506-513`).
- A cycle is never wired; a fed port cannot be fed twice
  (`assembly.py:120-127`, `146-147`, `397-414`).
- Wiring order is deterministic: forced unique writer/reader, then first justified
  port (`assembly.py:476-503`, `597-600`).
- Multiple producers of one type are refused; an unresolved role also blocks
  assembly (`assembly.py:443-473`).
- `assembly_preference` orders eager before deferred; greater rank runs earlier
  (`assembly.py:308-326`).
- Assembly rewrites inputs to exact patterns/resolved openings, discarding the
  declared wildcard (`assembly.py:541-569`).
- `WorkflowPlan` construction does not validate; resolution is a precondition
  (`workflow.py:569-588`).

**Execution**

- Executor map keyed by exact kind; duplicate kind refused; every plan kind must
  have an executor (`_private/pipeline.py:88-104`).
- `schedule` refuses duplicate component/step ids, absent component, unresolved
  opening, duplicate output name, and undeclared connection endpoints
  (`_private/runtime.py:184-233`).
- All producers of a step must complete before it is ready; a wave with no ready
  step is a cycle (`_private/runtime.py:131-137`, `515-545`).
- Each executor receives exactly its declared resource types; missing declared
  resources are refused before steps; undeclared lookup raises `KeyError`
  (`_private/runtime.py:93-113`; `runtime.py:63-95`).
- Duplicate exact resource type is refused (`events.py:41-58`).
- Providers publish on start, dispose on finish/halt; a provider that never saw
  start does nothing (`pipeline.py:212-239`).
- A listener error is a pipeline failure; `PipelineHalted` precedes re-raise
  (`events.py:239-259`; `_private/runtime.py:669-674`).
- Outcome validation: correct step id; `FAILED` has a failure; failure step id
  matches; artifact names unique/declared/correctly typed
  (`_private/runtime.py:355-401`).
- An ordinary executor exception becomes a `FAILED` outcome, not an aborted run
  (`_private/runtime.py:461-470`).
- Runtime config is validated for unknown, missing required, and scalar shape;
  `integer`/`number` exclude `bool`; `json` only checks serializability
  (`_private/runtime.py:236-283`).
- `SUCCEEDED`/`WARNING` are continuable; `FAILED`/`SKIPPED` disrupt
  (`runtime.py:207-255`).
- A normal step receives `ExecutionContext`; any disruption selects
  `DisruptedExecutionContext` (`_private/runtime.py:436-459`).
- Active failures propagate as described in §3; `succeeded` is exactly
  `not unresolved_failures` (`runtime.py:384-394`).

**Codecs / canonical types**

- Plan documents use `Key` arrays; field names state the role, so no role token is
  written; provenance and payload are verbatim
  (`_private/workflow_codec.py:1-6`, `169-180`, `214-236`).
- Plan step ids must be exactly two segments; openings need at least four with a
  valid direction token (`_private/workflow_codec.py:58-80`).
- Decoder defaults: `declared_name=""`, `runtime_fields=()`,
  `assembly_preference="eager"`, empty lists/tuples, `provenance=None`; no unknown
  field rejection or preference validation (`102-113`, `145-150`, `193-211`,
  `239-265`).
- Report codec is encode-only, with `dataclasses.asdict`-style recursive value
  conversion (`_private/report_codec.py:1-76`).
- Canonical units must be known; custom/struct need non-empty module/qualname;
  nullables cannot nest (`types/model.py:46-136`).
- `normalize_type` accepts `X | None` only with one non-`None` arm, `Nullable[X]`
  and `Array[X]` with exactly one item; a non-`Struct` `Shape` is refused; unknown
  annotations raise (`normalization.py:23-62`).
- Type documents use `kind` discriminators `unit`, `custom`, `struct`, `array`,
  `nullable`; nested nullable decoding is refused (`codec.py:89-156`).
- `require_scalar` allows a nullable scalar; `require_graph_property` refuses
  nested records and arrays of arrays/structs (`validation.py:38-55`).
- Reference documents are `[language, role, *key]`; role makes the document
  self-describing (`distribution/model/_private/refs.py:1-6`, `81-95`).
- `Ref` equality/hash use the wrapped `SymbolRef` only, ignoring role
  (`refs.py:133-139`).
- `FieldRef`/`PropertyRef` split the final key segment at its last dot; no dot is
  required (`refs.py:229-260`, `279-299`).
- `validate_relative_path` rejects absolute paths and `..` parts (`paths.py:7-15`).

---

## 5. Extension points

| Point | Substitute | Contract/limit |
| --- | --- | --- |
| `Language` | any eight-member structural object | Frontend for one syntax/model; `name` is the `SymbolRef` language. |
| `Linker` | any `link(languages, namespace)`; model type free | Owns roots, closure, order, transcription, assembly, and duplicate/cycle/missing-reference errors. |
| `Planner` | any `component_id`/`version`/`runtime_fields`/`plan(model, context)` | Multiple planners may share a component; `PlanContext.shared` is the inter-planner scratch space. |
| `StepExecutor` | any `kinds`/`resources`/`execute(context, instruction)` | Dispatch by exact kind. `Executor` lacks `resources`, so it is not type-compatible with `Toolchain.executors`; the runtime tolerates a missing attribute via `getattr`. |
| `Resource` | any `close()` | Kernel never inspects it; the provider, not registry, closes it. |
| `ResourceProvider` | any `on_event(event)` | Publishes via `event.resources.add` on start; disposes on finish/halt. |
| `Runtime` | any `execute(plan, executors, *, configuration, listeners=())` | `Toolchain.runtime` optional; missing runtime refuses execution. |
| Toolchain composition | `with_planners`, `with_executors`, `dataclasses.replace` | `with_*` replace tuples; `api.compile` appends explicitly. |
| Listeners / presentation | callable or `on_event` object | Monitor is a listener; listener error is a pipeline failure. |
| Plan/report codecs | `kernel.service.internal.{workflow_codec,report_codec}` | Plan round-trips; report encode-only. |
| Canonical types | not substitutable per language | One ontology for every language, blueprint and plan (`types/model.py:1-6`; `AGENTS.md`). |
| Composition root | `default_toolchain(planners, executors, engine)`, `compile(toolchain=...)`, `execute(runtime=BuildRuntime(...), monitor=...)` | Replace planners/executors/engine/providers/presentation without editing the kernel. |

No planner/executor registry, no resource lookup by name, no `Extension` object.
`compile_model` iterates its planner sequence; `execute_plan` iterates executors;
resources are exact Python types (`_private/pipeline.py:40-104`;
`_private/runtime.py:93-113`).

---

## 6. Evidence index

| Topic | Primary files/lines |
| --- | --- |
| Exports/root | `kernel/__init__.py:1-124`; `kg_build_system/__init__.py:1-261`; `api.py:1-296` |
| Key/symbols/language | `key.py`, `symbol.py`, `language.py`; tests `tests/kernel/test_kernel.py:117-167` |
| Plan/runtime/events | `workflow.py`, `runtime.py`, `events.py`; tests `test_pipeline_identity.py:43-157`, `test_runtime_events.py:119-303` |
| Canonical types | `types/model.py`, `types/markers.py`, `model/internal`, `model/_private` |
| Protocols/Toolchain | `service/public/pipeline.py:1-399`; `service/public/runtime.py:1-63` |
| Private flow/assembly/scheduler | `_private/pipeline.py:1-122`; `_private/assembly.py:1-606`; `_private/runtime.py:1-707` |
| Codecs | `_private/workflow_codec.py:1-268`; `_private/report_codec.py:1-79` |
| Distribution model | `distribution/model/public/{refs,artifacts,asset_tables,runtime,paths}.py`; `_private/refs.py`; `internal/canonical_types.py` |
| Concrete linker (out of scope) | `distribution/interpreter/service/_private/link.py:42-266`; `adapters/kernel_linker.py:12-48` |
| Kernel tests | `test_toolchain_flow.py`, `test_runtime_resources.py`, `test_runtime_events.py`, `test_extension_bundle.py`, `test_import_isolation.py` |

---

## 7. Surprises, ambiguities, inconsistencies

**Documented but absent/stale**

- `Extension` is listed in `ARCHITECTURE.md:29-30` but absent from code and from
  `docs/developer/system-design.md`. `unclear` whether removed or reserved.
- `kernel/service/__init__.py:1-4` says “language, module and capability protocols
  plus registry”; the module defines nothing.
- Private type modules cite “`kernel.internal.types.*`” (`normalization.py:3`,
  `validation.py:3`, `values.py:3`, `codec.py:3`); the real interface is
  `kernel.service.internal.types.*` (`functions.py:1-6`). `codec.py`’s example uses
  the correct path.
- `BlueprintLinker`’s docstring names only “expression, data, topology and binding”
  (`kernel_linker.py:13-17`), while it requires `expressions, asset, data,
  topology, binding, graph` (`link.py:42`) and `DEFAULT_LANGUAGES` includes asset
  and graph (`api.py:62-65`).

**Domain leakage in the kernel**

- `require_graph_property` is defined in
  `kernel/model/_private/types/validation.py:46-55` and exported by
  `kernel/service/internal/types/functions.py:185-200`, despite the kernel’s
  domain-agnostic claim (`model/public/__init__.py:1-7`; `AGENTS.md`).
- `types/markers.py:1-5` says “A graph author writes these names directly” in a
  kernel module.
- `distribution/model/internal/canonical_types.py:1-19` says the distribution
  “adds” `array`/`struct`, although the kernel already has `ArrayType`/`StructType`;
  `unclear` which layer owns container naming.

**Caller-facing behaviour**

- A supplied `RuntimeConfiguration` makes `Toolchain.execute(output_directory=...)`
  ineffective; `output_directory` remains required
  (`_private/pipeline.py:106-118`).
- `Toolchain.compile` always passes `PlanContext()`, so compile-time
  `runtime_configuration` cannot be supplied through the public API
  (`pipeline.py:331-333`; `_private/pipeline.py:68-74`).
- `ExecutionContext.runtime_configuration` is only the component’s mapping, not the
  full run configuration (`_private/runtime.py:424-426`).
- A hand-built plan with an unconnected input still runs: `is_ready` waits only on
  producers named by connections; nothing re-checks completeness
  (`_private/runtime.py:127-137`).
- An open input pattern matching no available type creates **no port** and is
  silently dropped, unlike an exact input which is later refused for having no
  writer (`assembly.py:159-167`, `254-279`).
- Assembly replaces each input’s declared pattern with the concrete matched type,
  so the serialized plan loses the original wildcard (`assembly.py:555-561`).
- `WorkflowReport.succeeded` can be true after every step failed if no step
  publishes: `unresolved` is empty, so all failures are “recovered”
  (`_private/runtime.py:563-588`; `runtime.py:384-394`). A failed step that no
  publisher depends on is likewise recovered.
- `WARNING` clears inherited failures, so it can recover an upstream failure
  (`_private/runtime.py:492-501`).
- `Plan.provenance` is called opaque, but the report converts a non-dict to
  `{"plan": value}` and copies a dict (`_private/runtime.py:603-621`;
  `workflow.py:573-574`; `runtime.py:382`).
- Runtime builds resource views and checks missing resources **before**
  `schedule(plan)` and the unknown-component check; a bad component + missing
  resource reports the resource first (`_private/runtime.py:645-656`).
- Unused registered executors are still resource-validated
  (`_private/runtime.py:93-113`).
- `assembly_preference` is not validated: exactly `"eager"` is eager, everything
  else is treated as deferred (`assembly.py:317`; `workflow.py:449`;
  `workflow_codec.py:207-210`).
- `Step`/`WorkflowPlan` are inert values; validation is split across assembly,
  `schedule` and `_validate_outcome` with different messages/timing.
- A `Publication` may feed downstream; only `Output` carries `must_read`
  (`workflow.py:395-400`; `assembly.py:235`).
- `ContinuableInput`/`DisruptingInput` status literals are annotations only; a
  hand-built value can hold any status (`runtime.py:228`, `253`).
- `ResourceView.resources` is not made read-only, unlike `SymbolContext.symbols`
  (`runtime.py:63-95` vs `symbol.py:101-106`); `RuntimeConfiguration` mappings are
  also stored by reference.
- `_validate_outcome` does not require every declared output to be returned; a
  missing publication is simply absent from the report (`_private/runtime.py:374-401`,
  `548-560`).
- Public `WorkflowRuntime` creates a fresh private implementation per `execute`
  and holds only the provider tuple (`service/public/runtime.py:33-60`).

**Reference-document ambiguities**

- `Ref.from_document` accepts a role token or omits it (`refs.py:115-131`);
  `ref_from_document` -> `decode_ref` requires `value[1]` to be a role and refuses
  role-less documents (`_private/refs.py:98-119`). Inconsistent.
- Plain `Ref.from_document` cannot accept an explicit token because `Ref.role` is
  `""`, so `split_document(..., role="")` raises on a token (`refs.py:51`,
  `115-131`; `_private/refs.py:67-72`). The method is effectively subclass-only.
- A key whose first segment equals a role name is ambiguous without a token:
  `split_document` treats `segments[0] in ROLES` as the role
  (`_private/refs.py:66-73`). `encode_ref` always writes the role, so round-trips
  are safe, but hand-written `["topology","node"]` means “node role, missing key”.
- `Ref` equality ignores role, so `NodeRef` and `PropertyRef` with the same
  language/key compare equal (`refs.py:133-139`), making role-typed dictionaries
  unsafe when roles must remain distinct.
- `Ref.name` is only the last key segment (`refs.py:90-100`); `FieldRef` then splits
  that segment on a dot, so a multi-segment field key is `unclear`.
- `SymbolRef` permits `Key(())`, but `NodeRef("topology", Key(()))` encodes as
  `["topology","node"]` and cannot decode because `split_document` requires a
  non-empty key (`refs.py:53-66`; `_private/refs.py:74-77`).
- `AssetTable.relation` vs `relation_name` is undocumented; both are strings and
  neither is identified as key vs display/physical name (`asset_tables.py:35-50`).

**`BuildRuntime` / composition root**

- `api.execute` replaces `output_directory` after construction, so a relative
  `working_directory` has already been resolved under the *old* default output
  directory and is not rebased (`distribution/model/public/runtime.py:63-69`;
  `api.py:252-253`).
- `to_configuration` spreads existing `provider_configuration["duckdb"]` then
  unconditionally overwrites `storage`, `threads`, `memory_limit`, `compression`,
  so a caller’s `threads` is lost when `duckdb_threads is None`
  (`runtime.py:90-100`).
- A `duckdb` provider entry is always emitted even without a DuckDB provider
  (`runtime.py:94-100`).
- `BuildRuntime`’s maps are plain mutable dicts inside a frozen dataclass; they are
  copied only in `to_configuration` (`runtime.py:48-57`, `86-93`).
- `create_blueprint` infers the namespace from the call stack and raises
  `RuntimeError("cannot determine the calling file")` when it cannot
  (`api.py:127-141`, `169-171`).
- `default_toolchain` suppresses **all** core/source defaults if any supplied
  planner claims `"core"`/`"duckdb"`; a partial set is not detected
  (`api.py:100-112`).
- `api.execute` writes `workflow_plan.json` before validation/execution, so a bad
  plan still leaves a document; `build_report.json` is absent on halt
  (`api.py:255-283`).

**Smaller typing/ordering notes**

- A raw `Key` pattern may contain non-final `**`; `Key.matches` returns `False` for
  it rather than raising, while `ArtifactPattern` rejects it
  (`key.py:61-81`; `workflow.py:222-234`).
- `Toolchain.executors` is typed `Sequence[StepExecutor]`, but `Executor` is also
  exported and the runtime tolerates a missing `resources` attribute
  (`pipeline.py:128-181`, `300`).
- `Listener` is a callable alias, but the bus and docs accept `on_event` objects
  (`events.py:193-194`, `229-259`).

---

## 8. Lifecycle cheat sheet

```text
Namespace -> Toolchain.build -> linker.link(languages, namespace)
  [discover/compute_key -> get_identity -> get_references -> closure/order
   -> transcribe -> Symbol] -> opaque ModelT
ModelT -> Toolchain.compile -> compile_model(planners, model, PlanContext())
  [group by component -> planner.plan -> assemble_plan -> WorkflowPlan]
WorkflowPlan -> Toolchain.execute(plan, output_directory=..., configuration=...)
  [execute_plan -> kind map/coverage -> Runtime.execute -> EventBus/Registry
   -> PipelineStarted -> per-executor ResourceView -> schedule -> waves
   -> ExecutionContext | DisruptedExecutionContext -> Executor.execute
   -> StepOutcome -> validate/record -> WorkflowReport -> PipelineFinished|Halted]
report.succeeded == (unresolved_failures == ())
```

All names above are defined in §2; the kernel only delegates to the linker, runs the private assembler/scheduler and exposes the protocols.

---

## 9. Open questions (`unclear`)

1. Is `Extension` removed, planned, or documentation-only? No code artefact exists.
2. Which layer owns canonical container naming (`ArrayType`/`StructType` vs `"array"`/`"struct"`)?
3. Should `require_graph_property` move to the distribution?
4. Should `Toolchain.compile` accept a `PlanContext` for compile-time configuration?
5. Should `Toolchain.execute` derive config from `output_directory` when one is supplied?
6. Should `schedule` require every declared input to be connected? It does not.
7. Should `Ref` role participate in equality? It does not.
8. What distinguishes `AssetTable.relation` from `relation_name`?
9. Should `BuildRuntime` rebase `working_directory` after `api.execute` replaces output?
10. Is `{"plan": provenance}` intended as a stable report contract?
