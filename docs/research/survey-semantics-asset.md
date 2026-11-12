# Survey: semantics, graph, asset, annotations, topology, binding, generation

Source: `/home/paul/Repos/kg-build-system` (read-only; not modified, not executed).
Scope: `kg_build_system/distribution/languages/{semantics,graph,asset,annotations,topology,binding}/**` and `kg_build_system/generation/**`.
Workspace output: `/home/paul/Repos/kg-build-kb/research/survey-semantics-asset.md`.

Conventions:

- Paths below are relative to `kg_build_system/` unless prefixed.
- "public" means exported by the language package; only some names are re-exported by top-level `kg_build_system/__init__.py`.
- Signatures are transcribed from the dataclass/function definitions. `Sequence`/`Mapping` are `collections.abc` types.
- "unclear" marks a point not settled by code, docs, or both.

---

## 1. File / package map

### semantics (17 modules)

- `distribution/languages/semantics/__init__.py` — re-exports the six authoring units.
- `.../semantics/model/__init__.py` — empty model package marker.
- `.../semantics/model/public/__init__.py` — re-exports units plus `require_declaration_semantics`.
- `.../semantics/model/public/units.py` — `Claim`, `Limitation`, `Frame`, `Purpose`, `Semantics`, `GraphSemantics`; unit invariants.
- `.../semantics/model/internal/__init__.py` — re-exports DTOs.
- `.../semantics/model/internal/dto/__init__.py` — DTO re-exports.
- `.../semantics/model/internal/dto/semantics_dto.py` — `ClaimDTO`, `LimitationDTO`, `FrameDTO`, `PurposeDTO`, `SemanticsDTO`, `GraphSemanticsDTO`.
- `.../semantics/service/__init__.py` — empty service marker.
- `.../semantics/service/internal/__init__.py` — re-exports codec, transcription, source functions.
- `.../semantics/service/internal/codec.py` — thin delegation to private codec.
- `.../semantics/service/internal/source.py` — thin delegation to private renderer.
- `.../semantics/service/internal/transcription.py` — thin delegation to private transcription.
- `.../semantics/service/_private/__init__.py` — private package marker.
- `.../semantics/service/_private/validation.py` — `required_text`, `unit_tuple`.
- `.../semantics/service/_private/codec.py` — canonical JSON codec for semantics and graph semantics.
- `.../semantics/service/_private/source.py` — source rendering of semantics expressions and fragments.
- `.../semantics/service/_private/transcription.py` — authoring units to DTOs.

### graph (20 modules)

- `distribution/languages/graph/__init__.py` — re-exports `Graph`, `GraphOptions`.
- `.../graph/model/__init__.py` — empty model marker.
- `.../graph/model/public/__init__.py` — re-exports declaration and options.
- `.../graph/model/public/declarations.py` — `Graph` base; `__init_subclass__` prepares the declaration.
- `.../graph/model/public/options.py` — `GraphOptions`.
- `.../graph/model/internal/__init__.py` — DTO re-export.
- `.../graph/model/internal/dto/__init__.py` — DTO re-export.
- `.../graph/model/internal/dto/graph_dto.py` — `GraphDeclarationDTO`.
- `.../graph/service/__init__.py` — empty service marker.
- `.../graph/service/internal/__init__.py` — re-exports adapter, codec, source.
- `.../graph/service/internal/adapters/__init__.py` — adapter re-export.
- `.../graph/service/internal/adapters/kernel_language.py` — `GraphLanguage`; at most one graph per namespace.
- `.../graph/service/internal/codec.py` — delegation to private codec.
- `.../graph/service/internal/source.py` — delegation to private renderer.
- `.../graph/service/_private/__init__.py` — private marker.
- `.../graph/service/_private/declarations.py` — prepare/validate a `Graph` subclass; identity helpers.
- `.../graph/service/_private/codec.py` — canonical JSON codec for `GraphDeclarationDTO`.
- `.../graph/service/_private/symbols.py` — graph declaration symbol and identity.
- `.../graph/service/_private/source.py` — renders class + `GraphOptions` + inline graph semantics.
- `.../graph/service/_private/transcription.py` — graph declaration to DTO.

### asset (23 modules)

- `distribution/languages/asset/__init__.py` — re-exports `Asset`, options, descriptor helpers.
- `.../asset/model/__init__.py` — empty model marker.
- `.../asset/model/public/__init__.py` — re-exports declarations, descriptor helpers, options.
- `.../asset/model/public/declarations.py` — `Asset` base; `__init_subclass__` prepares the declaration.
- `.../asset/model/public/descriptor.py` — `AssetDescriptor`, `asset_name`, `asset_reference`.
- `.../asset/model/public/options.py` — `AssetAuthority`, `AssetLicense`, `AssetGovernance`, `AssetProfile`, `AssetLayout`, `AssetOptions`.
- `.../asset/model/internal/__init__.py` — DTO re-exports.
- `.../asset/model/internal/dto/__init__.py` — DTO re-exports.
- `.../asset/model/internal/dto/asset_dto.py` — `AssetDTO`, `AssetPartDTO`, layout/license/governance/profile DTOs.
- `.../asset/service/__init__.py` — empty service marker.
- `.../asset/service/internal/__init__.py` — re-exports adapter, codec, source.
- `.../asset/service/internal/adapters/__init__.py` — adapter re-export.
- `.../asset/service/internal/adapters/kernel_language.py` — `AssetLanguage`.
- `.../asset/service/internal/codec.py` — delegation to private codec.
- `.../asset/service/internal/source.py` — delegation to private renderer.
- `.../asset/service/_private/__init__.py` — private marker.
- `.../asset/service/_private/declarations.py` — prepare/validate an `Asset` subclass.
- `.../asset/service/_private/options.py` — string/mapping normalisation and validation.
- `.../asset/service/_private/semantics.py` — bridge to semantics transcription/codec/renderer.
- `.../asset/service/_private/symbols.py` — asset symbol and identity.
- `.../asset/service/_private/transcription.py` — `AssetDTO`, `AssetPartDTO` construction.
- `.../asset/service/_private/codec.py` — canonical asset JSON codec, including legacy profile fallback.
- `.../asset/service/_private/source.py` — renders `Asset` class and `AssetOptions`.

### annotations (19 modules)

- `distribution/languages/annotations/__init__.py` — re-exports `Annotation`, `NodeLabel`, `EdgeLabel`.
- `.../annotations/model/__init__.py` — model marker.
- `.../annotations/model/public/__init__.py` — re-exports annotation types.
- `.../annotations/model/public/base.py` — frozen `Annotation` base with `namespace`/`annotation_id` ClassVars.
- `.../annotations/model/public/labels.py` — `NodeLabel`, `EdgeLabel`.
- `.../annotations/model/internal/__init__.py` — DTO re-export.
- `.../annotations/model/internal/dto/__init__.py` — DTO re-export.
- `.../annotations/model/internal/dto/blueprint_dto.py` — `AnnotationDTO`.
- `.../annotations/service/__init__.py` — service marker.
- `.../annotations/service/internal/__init__.py` — internal exports.
- `.../annotations/service/internal/functions.py` — payload/DTO/tuple helpers.
- `.../annotations/service/internal/dto/__init__.py` — codec re-export.
- `.../annotations/service/internal/dto/codec.py` — document codec delegation/implementation surface.
- `.../annotations/service/internal/service/__init__.py` — source-rendering surface.
- `.../annotations/service/internal/service/source.py` — `AnnotationSourceContext` and renderer.
- `.../annotations/service/_private/__init__.py` — private marker.
- `.../annotations/service/_private/validation.py` — `annotation_tuple`.
- `.../annotations/service/_private/payload.py` — `asdict` payload and DTO construction.
- `.../annotations/service/_private/codec.py` — canonical annotation document codec.
- `.../annotations/service/_private/source.py` — alternate inline annotation renderer.

### topology (33 modules)

- `distribution/languages/topology/__init__.py` — re-exports authoring roots, options, `property`, `endpoint`.
- `.../topology/model/__init__.py` — marker.
- `.../topology/model/public/__init__.py` — re-exports declarations, options, values.
- `.../topology/model/public/declarations.py` — `Node`, `AbstractNode`, `Edge`, `AbstractEdge`, templates, `Endpoint`, `property`, typevars.
- `.../topology/model/public/options.py` — `NodeOptions`, `EdgeOptions`, `NodeOptionsTemplate`, `EdgeOptionsTemplate`.
- `.../topology/model/public/values.py` — `GraphScalar`, `GraphArray`, `GraphValue`, `NonNullableGraphValue`, `PropertySlot`.
- `.../topology/model/internal/__init__.py` — re-exports DTOs/metadata.
- `.../topology/model/internal/dto/__init__.py` — DTO re-exports.
- `.../topology/model/internal/dto/blueprint_dto.py` — `PropertyDTO`, `NodeDTO`, `EdgeDTO`, `GraphPartDTO`.
- `.../topology/model/internal/model/__init__.py` — metadata re-exports.
- `.../topology/model/internal/model/metadata.py` — `PropertyDeclaration`, `ComponentMetadata`, `require_semantics`.
- `.../topology/model/_private/__init__.py` — private marker.
- `.../topology/model/_private/properties.py` — property descriptor, docstring recovery, MRO property resolution, naming.
- `.../topology/service/__init__.py` — service marker.
- `.../topology/service/public/__init__.py` — re-exports `property`, `endpoint`.
- `.../topology/service/public/declarations.py` — public `property`/`endpoint` wrappers.
- `.../topology/service/internal/__init__.py` — internal service exports.
- `.../topology/service/internal/adapters/__init__.py` — adapter re-export.
- `.../topology/service/internal/adapters/kernel_language.py` — `TopologyLanguage`.
- `.../topology/service/internal/codec.py` — codec delegation.
- `.../topology/service/internal/endpoints.py` — endpoint delegation.
- `.../topology/service/internal/metadata.py` — metadata accessors.
- `.../topology/service/internal/properties.py` — property descriptor construction.
- `.../topology/service/internal/source.py` — source rendering delegation.
- `.../topology/service/internal/transcription.py` — transcription/validation delegation.
- `.../topology/service/_private/__init__.py` — private marker.
- `.../topology/service/_private/class_creation.py` — one-pass class preparation, lineage/tier/options/properties/endpoints, `make_endpoint`.
- `.../topology/service/_private/codec.py` — canonical topology JSON codec.
- `.../topology/service/_private/metadata.py` — read frozen metadata/properties.
- `.../topology/service/_private/semantics.py` — bridge to semantics language.
- `.../topology/service/_private/source.py` — topology DTO to authoring source.
- `.../topology/service/_private/symbols.py` — node/edge/property symbols and references.
- `.../topology/service/_private/transcription.py` — components to DTO, labels, validation, reachability closure.
- `.../topology/service/_private/validation.py` — `validate_component`.

### binding (23 modules)

- `distribution/languages/binding/__init__.py` — re-exports values and factories.
- `.../binding/model/__init__.py` — marker.
- `.../binding/model/public/__init__.py` — re-exports values.
- `.../binding/model/public/values.py` — `BindingOptions`, `NodeBinding`, `EdgeBinding`, `NodeValues`, `EdgeValues`, `PropertyValues`, `PythonRef`, `BindingMode`.
- `.../binding/model/internal/__init__.py` — DTO re-export.
- `.../binding/model/internal/dto/__init__.py` — DTO re-exports.
- `.../binding/model/internal/dto/blueprint_dto.py` — `NodeBindingDTO`, `EdgeBindingDTO`, `PythonRefDTO`, `RowPlanDTO`.
- `.../binding/service/__init__.py` — service marker.
- `.../binding/service/public/__init__.py` — re-exports factories.
- `.../binding/service/public/builders.py` — public `node_binding`/`edge_binding` overloads.
- `.../binding/service/internal/__init__.py` — internal exports.
- `.../binding/service/internal/factories.py` — factory delegation.
- `.../binding/service/internal/codec.py` — codec delegation.
- `.../binding/service/internal/source.py` — source rendering and `bind_reference`.
- `.../binding/service/internal/transcription.py` — transcription delegation.
- `.../binding/service/internal/adapters/__init__.py` — adapter re-export.
- `.../binding/service/internal/adapters/kernel_language.py` — `BindingLanguage`.
- `.../binding/service/_private/__init__.py` — private marker.
- `.../binding/service/_private/factories.py` — validated factories: targets, keys, property map, row form, endpoints.
- `.../binding/service/_private/validation.py` — binding DTO invariants and semantics checks.
- `.../binding/service/_private/symbols.py` — binding identity, references, symbol transcription.
- `.../binding/service/_private/transcription.py` — binding DTOs, row-source validation, reference checks.
- `.../binding/service/_private/codec.py` — canonical binding/document codec including row plans.
- `.../binding/service/_private/source.py` — binding DTO to authoring source.

### generation (78 modules)

Public/build surface:

- `generation/__init__.py` — re-exports public generation names.
- `generation/code_generation/__init__.py` — re-exports `AssetContractOptions`, results, requests, sessions, factories.
- `.../code_generation/model/__init__.py` — model layer marker.
- `.../model/public/__init__.py` — public model exports.
- `.../model/public/contract.py` — `AssetContractOptions`.
- `.../model/public/errors.py` — `GenerationError(ValueError)`.
- `.../model/public/models.py` — compatibility re-export of public models.
- `.../model/public/requests.py` — `GenerationRequest`.
- `.../model/public/results.py` — `GenerationStatus`, `GenerationActionKind`, `GenerationAction`, `GenerationResult`.
- `.../model/public/values.py` — `StaticValue` type.
- `.../model/public/watch.py` — `FileChangeKind`, `FileChange`.
- `.../model/internal/__init__.py` — internal model exports.
- `.../model/internal/models.py` — `GenerationLocation`, `DiscoveredGeneration`, `GenerationManifest`.
- `.../model/internal/providers.py` — `Provider`, `ProviderAsset`, `ProviderContext`, `ProviderGenerationConfig`, `GeneratedDeclarations`.
- `.../model/_private/__init__.py` — private model marker.
- `.../model/_private/generated.py` — generated render tree and `Nullability`.
- `.../service/__init__.py` — service layer marker.
- `.../service/public/__init__.py` — public service exports.
- `.../service/public/contract.py` — `asset_contract` decorator.
- `.../service/public/run.py` — `discover`, `discover_file`, `generate`, `watch`.
- `.../service/public/session.py` — `GenerationSession`.

Generation internals:

- `.../service/internal/__init__.py` — internal provider loading/CLI registration.
- `.../service/internal/functions.py` — `add_generate_command`.
- `.../service/internal/adapters/__init__.py` — provider adapter export.
- `.../service/internal/adapters/provider.py` — `load_provider`, `resolve_provider_path` wrappers.
- `.../service/_private/__init__.py` — private generation package.
- `.../service/_private/adapters.py` — import/validate provider/config; load asset; path resolution.
- `.../service/_private/command.py` — argparse `kbs generate` integration.
- `.../service/_private/contract.py` — inert contract validation and application.
- `.../service/_private/discovery.py` — LibCST static discovery of `@asset_contract`.
- `.../service/_private/engine.py` — desired-state pass, ownership, install/prune, `GenerationSession` implementation.
- `.../service/_private/manifest.py` — `.kbs-generation.json` codec.
- `.../service/_private/watcher.py` — async file watching.
- `.../service/_private/rendering/__init__.py` — rendering exports.
- `.../rendering/constants.py` — header, directives, `FORMAT_VERSION = "6"`, type names.
- `.../rendering/fingerprint.py` — request fingerprint.
- `.../rendering/package.py` — validate/render whole package, path/import/collision rules, `__init__.py` injection.
- `.../rendering/declarations/__init__.py` — declaration render exports.
- `.../declarations/common.py` — class/field/member assembly.
- `.../declarations/plain.py` — declaration with no base.
- `.../declarations/registry.py` — kind-to-renderer registry.
- `.../declarations/struct.py` — `Struct` renderer.
- `.../declarations/table.py` — `Table` renderer.
- `.../declarations/table_group.py` — `TableGroup` renderer.
- `.../rendering/types/__init__.py` — type render exports.
- `.../types/array.py` — `Array[T]`.
- `.../types/nullable.py` — `T | None`.
- `.../types/registry.py` — type renderer registry and `field_annotation` (value type only).
- `.../types/scalar.py` — scalar/representative names.
- `.../types/struct.py` — struct reference name.
- `.../service/_private/builtins/__init__.py` — exports `ColumnOverride`, config, provider.
- `.../builtins/config.py` — `ColumnOverride`, `DataContractInferenceConfig`.
- `.../builtins/datasets.py` — logical table/group discovery from files/partitions.
- `.../builtins/formats.py` — suffix/trust-tier/remote-source classification.
- `.../builtins/mapping.py` — DuckDB type digest gate.
- `.../builtins/naming.py` — identifiers, class names, record names, path binding.
- `.../builtins/nullability.py` — tier-to-`Nullability` mapping.
- `.../builtins/observation.py` — DuckDB `DESCRIBE`, Parquet schema/footer statistics; no row reads.
- `.../builtins/overrides.py` — column override validation/application.
- `.../builtins/provenance.py` — schema facts, digest, nullability notes, pre-flight.
- `.../builtins/provider.py` — `InferDataContractProvider`.
- `.../builtins/schema_inference.py` — compatibility import path.
- `.../builtins/shapes.py` — described columns/Parquet trees to generated fields/structs.
- `.../builtins/state.py` — mutable per-inference state.
- `.../code_generation/builtins/__init__.py` — public wildcard re-export of private builtins.
- `.../builtins/config.py` — public wildcard re-export.
- `.../builtins/datasets.py` — public wildcard re-export.
- `.../builtins/formats.py` — public wildcard re-export.
- `.../builtins/mapping.py` — public wildcard re-export.
- `.../builtins/naming.py` — public wildcard re-export.
- `.../builtins/nullability.py` — public wildcard re-export.
- `.../builtins/observation.py` — public wildcard re-export.
- `.../builtins/overrides.py` — public wildcard re-export.
- `.../builtins/provenance.py` — public wildcard re-export.
- `.../builtins/provider.py` — public wildcard re-export.
- `.../builtins/schema_inference.py` — public wildcard re-export.
- `.../builtins/shapes.py` — public wildcard re-export.
- `.../builtins/state.py` — public wildcard re-export.

---

## 2. Public authoring surface (signatures)

### 2.1 Semantics

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `Claim` | `Claim(text: str)` | Frozen dataclass, slots. `required_text`. |
| `Limitation` | `Limitation(text: str)` | Frozen, slots; only meaningful under `Frame`. |
| `Frame` | `Frame(text: str, limitations: Sequence[Limitation] = ())` | Frozen, slots; normalises to tuple, type-checks members. |
| `Purpose` | `Purpose(text: str, frames: Sequence[Frame] = ())` | Frozen, slots; normalises to tuple. |
| `Semantics` | `Semantics(claims: Sequence[Claim] = (), frames: Sequence[Frame] = ())` | Requires at least one claim or frame. No purpose. |
| `GraphSemantics` | `GraphSemantics(claims: Sequence[Claim] = (), *, purpose: Purpose)` | `purpose` is keyword-only and required. |
| `require_declaration_semantics` | `require_declaration_semantics(value: object, *, context: str = "semantics") -> None` | Public helper; rejects `GraphSemantics` for declaration attachments. |

DTO mirrors exist: `ClaimDTO`, `LimitationDTO`, `FrameDTO`, `PurposeDTO`, `SemanticsDTO`, `GraphSemanticsDTO` (`semantics/model/internal/dto/semantics_dto.py`).

### 2.2 Graph

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `Graph` | `class Graph; options: ClassVar[GraphOptions]` | Subclassing triggers `prepare_graph_declaration`. |
| `GraphOptions` | `GraphOptions(*, name: str \| None = None, description: str \| None = None, semantics: GraphSemantics)` | Frozen, slots, `kw_only=True`. `semantics` required; must carry `Purpose`. |
| `GraphDeclarationDTO` | `GraphDeclarationDTO(name: str, description: str \| None, semantics: GraphSemanticsDTO)` | Internal blueprint shape. |

### 2.3 Asset

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `Asset` | `class Asset; options: ClassVar[AssetOptions]` | Terminal in practice: each subclass must declare its own options. |
| `AssetOptions` | `AssetOptions(profile: AssetProfile, semantics: Semantics \| None = None, name: str \| None = None, website: str \| None = None, version: str \| None = None, layout: AssetLayout \| None = None, governance: AssetGovernance = AssetGovernance(), annotations: Sequence[Annotation] = ())` | Not `kw_only`; examples use keywords. |
| `AssetProfile` | `AssetProfile(subject: str, coverage: str, authority: AssetAuthority, basis: str, title: str \| None = None, description: str \| None = None)` | First four required. |
| `AssetAuthority` | `StrEnum`: `PRIMARY="primary"`, `DERIVED="derived"`, `REFERENCE="reference"`, `INFERRED="inferred"` | `str(value)` yields the value. |
| `AssetLayout` | `AssetLayout(kind: str \| None = None, locator: str \| None = None, format: str \| None = None, selector: str \| None = None, partition_by: Sequence[str] = (), members: Mapping[str, str] = {}, properties: Mapping[str, str] = {})` | `partition_by` tuple; mappings sorted/read-only. |
| `AssetGovernance` | `AssetGovernance(license: AssetLicense \| None = None, owner: str \| None = None, metadata: Mapping[str, str] = {})` | `metadata` sorted/read-only. |
| `AssetLicense` | `AssetLicense(identifier: str, url: str \| None = None, attribution: str \| None = None)` | `identifier` required. |
| `AssetDescriptor` | `AssetDescriptor(name: str, website: str \| None, version: str \| None, layout: AssetLayout \| None, profile: AssetProfile, governance: AssetGovernance)` | Frozen; no semantics/annotations fields. |
| `asset_name` | `asset_name(value: type[Asset] \| AssetDescriptor \| AssetDTO) -> str` | Raises `TypeError` for anything else. |
| `asset_reference` | `asset_reference(value: type[Asset] \| AssetDescriptor \| AssetDTO) -> AssetRef` | `AssetRef("asset", Key((name,)))`. |

Top-level `kg_build_system` exports `Asset`, `AssetAuthority`, `AssetGovernance`, `AssetLayout`, `AssetLicense`, `AssetOptions`, `AssetProfile`; it does **not** export `AssetDescriptor`, `asset_name` or `asset_reference`. Those are exported by `kg_build_system.distribution.languages.asset`.

### 2.4 Annotations and labels

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `Annotation` | frozen dataclass; `namespace: ClassVar[str]`, `annotation_id: ClassVar[str]` | No payload fields on the base. |
| `NodeLabel` | `NodeLabel(label: str)`; namespace `kg_build_system.topology`, id `node_label` | `__post_init__` rejects falsy label only. |
| `EdgeLabel` | `EdgeLabel(label: str)`; namespace `kg_build_system.topology`, id `edge_label` | Same. |
| `AnnotationDTO` | `AnnotationDTO(namespace: str, id: str, arguments: JsonValue)` | Frozen, slots; non-empty namespace/id. |
| `annotation_tuple` | `annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]` | Rejects non-`Annotation`. |
| `annotation_payload` | `annotation_payload(annotation: Annotation) -> tuple[str, str, dict[str, Any]]` | Uses `dataclasses.asdict`. |
| `annotation_dtos` | `annotation_dtos(annotations: Sequence[Annotation]) -> tuple[AnnotationDTO, ...]` | Payload becomes `arguments`. |
| `render_annotation_source` | `render_annotation_source(dto: AnnotationDTO, context: AnnotationSourceContext) -> SourceFragment` | Separate renderer in annotations package. |

### 2.5 Topology

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `PropertySlot[T]` | `type PropertySlot[T: GraphValue] = Selection[T]` | Public slot type is the expression `Selection`; declaration metadata is separate. |
| `GraphScalar` | `bool \| int \| float \| str \| Date \| Time \| Timestamp \| Uuid \| CustomDataType` | Canonical scalar set. |
| `GraphArray` | `Array[GraphScalar]` | Flat, homogeneous, non-null items. |
| `GraphValue` | `GraphScalar \| GraphArray \| None` | |
| `NonNullableGraphValue` | `GraphScalar` | Used by binding keys. |
| `property` | `property[T: GraphValue](*, name: str \| None = None, description: str \| None = None, annotations: Sequence[Annotation] = (), semantics: Semantics \| None = None) -> PropertySlot[T]` | Assigned to a `PropertySlot[T]` attribute. |
| `Node` | `class Node(NodeSideBase)` | Concrete, terminal, bindable. |
| `AbstractNode` | `class AbstractNode(NodeSideBase)` | Graph-visible category; not bindable. |
| `Edge[S, D]` | `class Edge(AbstractEdge[S, D], Generic[S, D])` | Concrete, terminal, bindable; directed. |
| `AbstractEdge[S_co, D_co]` | `class AbstractEdge(TopologyDeclarationBase, Generic[S_co, D_co])` | Category edge. |
| `NodeTemplate` | `class NodeTemplate(TopologyDeclarationBase)`; `options: ClassVar[Any] = NodeOptionsTemplate()` | Inert mixin. |
| `EdgeTemplate` | `class EdgeTemplate(TopologyDeclarationBase)`; `options: ClassVar[Any] = EdgeOptionsTemplate()` | Inert mixin. |
| `NodeOptions` | `NodeOptions(name: str \| None = None, description: str \| None = None, annotations: Sequence[Annotation] = (), semantics: Semantics \| None = None)` | Frozen, slots. |
| `EdgeOptions` | same signature as `NodeOptions` | Frozen, slots. |
| `NodeOptionsTemplate` | `NodeOptionsTemplate(annotations: Sequence[Annotation] = (), semantics: Semantics \| None = None)` | No name/description. |
| `EdgeOptionsTemplate` | same signature as `NodeOptionsTemplate` | No name/description. |
| `Endpoint[N_co]` | `Endpoint(target: type[N_co])` | Frozen, slots; direct construction skips concrete-node check. |
| `endpoint` | `endpoint(target: type[N]) -> Endpoint[N]` | Validates concrete node. |
| Typevars | `N_co`, `S_co`, `D_co` bound `NodeSideBase`, covariant; `S`, `D` bound `NodeSideBase`, invariant | Endpoint category parameters are node-side only. |

Internal metadata: `PropertyDeclaration(attribute, name, logical_type, authoring_type=None, description=None, annotations=(), semantics=None)`; `ComponentMetadata(kind, name, properties=(), description=None, source=None, target=None, annotations=(), semantics=None, abstract=False, parent=None)`.

### 2.6 Binding

| Name | Signature / shape | Notes |
| --- | --- | --- |
| `BindingOptions` | `BindingOptions(annotations: Sequence[Annotation] = (), semantics: Semantics \| None = None)` | Frozen, slots. |
| `NodeBinding[N]` | `NodeBinding(debug_name, target, build_key, properties, annotations=(), rows=None, mode="declarative", python_ref=None, semantics=None)` | Frozen, slots. |
| `EdgeBinding[E]` | `EdgeBinding(debug_name, target, build_key, source_build_key, target_build_key, properties, annotations=(), source_node=None, target_node=None, rows=None, mode="declarative", python_ref=None, semantics=None)` | Frozen, slots. |
| `NodeValues[N, K]` | `NodeValues(build_key: Selection[K], properties: N)` | Returned by a `bind` callable. |
| `EdgeValues[E, K, SK, TK]` | `EdgeValues(build_key, source_build_key, target_build_key, properties)` | Four distinct type parameters. |
| `PropertyValues` | `tuple[tuple[str, Selection[Any]], ...]` | External property name + selection. |
| `PythonRef` | `PythonRef(module: str, qualname: str, signature: str)` | Stable callable reference; no live callable. |
| `BindingMode` | `Literal["declarative", "python"]` | |
| `node_binding` | `node_binding(*, target: type[N], build_key: Selection[Any] \| None = None, properties: N \| None = None, rows: RowSource \| None = None, bind: Callable[[S], NodeValues[N, Any]] \| None = None, debug_name: str \| None = None, options: BindingOptions = BindingOptions(), semantics: Semantics \| None = None) -> NodeBinding[N]` | Two overloads for direct/row forms. |
| `edge_binding` | `edge_binding(*, target: type[E], build_key=None, source_build_key=None, target_build_key=None, properties=None, rows=None, bind=None, debug_name=None, options=BindingOptions(), semantics=None, source_node: Endpoint[Any] \| None = None, target_node: Endpoint[Any] \| None = None) -> EdgeBinding[E]` | Five overloads cover concrete/abstract endpoint combinations. |

Internal blueprint shapes: `NodeBindingDTO(node, identity, properties, rows, annotations, mode, debug_name, python_ref, semantics)` and `EdgeBindingDTO(edge, identity, source_identity, target_identity, properties, rows, annotations, mode, debug_name, source_node, target_node, python_ref, semantics)`. `RowPlanDTO` aliases the data language's `RowSourcePlanDTO`.

### 2.7 Generation

Author surface:

| Name | Signature / shape |
| --- | --- |
| `AssetContractOptions` | `AssetContractOptions(provider: type[Provider[Any]], configuration: ConfigT, package: str)`; frozen, slots, generic over `ConfigT`. |
| `asset_contract` | `asset_contract(options: AssetContractOptions[Any]) -> Callable[[type[AssetT]], type[AssetT]]` |
| `GenerationRequest` | `GenerationRequest(provider_module, provider_qualname, config_module, config_qualname, configuration={}, package="", asset_module="", asset_qualname="", asset_digest="")` |
| `GenerationStatus` | `StrEnum`: `CURRENT="current"`, `CHANGED="changed"`, `STALE="stale"`. |
| `GenerationResult` | `GenerationResult(status, changed_paths=(), created_paths=(), updated_paths=(), deleted_paths=(), diagnostics=(), actions=())` |
| `GenerationAction` | `GenerationAction(kind, trigger_path, source_paths, declaration_id=None)` |
| `GenerationActionKind` | `DECLARATION_ADDED`, `DECLARATION_CHANGED`, `DECLARATION_DELETED`. |
| `FileChange` | `FileChange(kind: FileChangeKind, path: Path)` |
| `discover` | `discover(project_root: str \| Path) -> tuple[DiscoveredGeneration, ...]` |
| `discover_file` | `discover_file(project_root, source_path) -> tuple[DiscoveredGeneration, ...]` |
| `generate` | `async generate(project_root, *, check: bool = False, regenerate: bool = False) -> GenerationResult` |
| `watch` | `async watch(root, *, debounce=300, step=50, suffixes=(".py", ".json", ".toml", ".yaml", ".yml"), stop_event=None) -> AsyncIterator[tuple[FileChange, ...]]` |
| `GenerationSession` | `GenerationSession(project_root)`; `await start() -> GenerationResult`; `await handle(changed_paths, *, on_action=None) -> GenerationResult`. |
| `GenerationError` | `class GenerationError(ValueError)`. |

Provider contract:

- `ProviderGenerationConfig` — frozen Pydantic model, `extra="forbid"`, `strict=True`.
- `Provider[T]` — `ID: ClassVar[str]`, `VERSION: ClassVar[str]`, `CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]]`, `async classmethod generate(context: ProviderContext[T]) -> GeneratedDeclarations`.
- `ProviderContext(project_root: Path, request_path: Path, request_id: str, config: T, asset: ProviderAsset | None = None)`.
- `ProviderAsset(module: str, qualname: str, name: str, options: AssetOptions)`.
- `resolve_provider_path(context, value: str) -> Path` — separate internal function, not a `ProviderContext` method.
- `GeneratedPackage(files, nullability_notes=(), source_digest=None)`; `GeneratedFile(relative_path, declarations=(), exports=())`.
- `GeneratedClass(name, fields=(), members=(), description=None, base=None, declaration_name=None, asset=None)`; `GeneratedField(python_name, external_name, value_type, description=None, annotations=(), nullability=Nullability.DEFAULTED, schema_path="", logical_path="")`.
- `GeneratedAnnotation(import_module, class_name, arguments={})`; `GeneratedMember(python_name, declaration_name)`; `GeneratedAsset(module, qualname)`.
- Types: `GeneratedScalarType(name)`, `GeneratedStructType(declaration_name, in_file=None)`, `GeneratedArrayType(item)`, `GeneratedNullableType(value)`.
- `Nullability` = `DECLARED`, `ENFORCED`, `DEFAULTED`.

Built-in provider:

- `InferDataContractProvider.ID = "infer_data_contract"`, `VERSION = "8"` (code), `CONFIG_TYPE = DataContractInferenceConfig`.
- `DataContractInferenceConfig(source: str | None = None, relation: str | None = None, mode: Literal["table","table_group"]="table", layout: Literal["files","parquet_parts","hive_partitioned_parquet"]="files", anonymous: bool = False, override: dict[str, dict[str, Any]] = {})`.
- `ColumnOverride(type: str | None = None, nullable: bool | None = None)`; at least one must be set.

---

## 3. Semantics model as implemented

### 3.1 Unit hierarchy and ownership

| Unit | Owns | May appear under | Required members | Optional members |
| --- | --- | --- | --- | --- |
| `Claim` | nothing | `GraphSemantics`, `Semantics` | `text` non-empty | — |
| `Limitation` | nothing | `Frame.limitations` only by type | `text` non-empty | — |
| `Frame` | limitations | `Purpose.frames`, `Semantics.frames` | `text` non-empty | `limitations` tuple |
| `Purpose` | frames | `GraphSemantics.purpose` only | `text` non-empty | `frames` tuple |
| `Semantics` | claims, frames | declaration attachment | at least one claim or frame | both tuples |
| `GraphSemantics` | claims, one purpose | `GraphOptions.semantics` only | `purpose` | `claims` tuple |

The ownership rules are structural, not semantic validation: `Frame.limitations` only accepts `Limitation` instances, and `Purpose.frames` only accepts `Frame`; there is no type that would allow a claim under a frame or a limitation directly under a purpose.

### 3.2 Required, optional, invalid

- Required text: every `Claim`, `Limitation`, `Frame` and `Purpose` text must be a non-empty `str`. `required_text` rejects `""` and non-strings; it does **not** reject whitespace-only text.
- Required structure: `Semantics()` with no claim and no frame raises `ValueError: semantics requires at least one claim or frame`.
- `GraphSemantics` requires a `Purpose`; the field is keyword-only. A wrong type raises `TypeError: graph semantics purpose must be a Purpose`.
- `Semantics` has no purpose parameter; a declaration frame is implicitly read under the graph purpose.
- A declaration attachment rejects `GraphSemantics` (`require_declaration_semantics`); only `GraphOptions` carries the meaning root.
- Invalid: non-empty text violation, wrong unit type inside a tuple, missing graph purpose, `GraphSemantics` on a declaration, and an empty declaration fragment.
- Not validated: duplicate claims/frames/limitations, ordering, identical text, cross-unit consistency, truth, revisions, cuts, ownership, or references.
- No keys, owners or references exist on units; the attachment site is the only ownership.

### 3.3 Graph declaration

- `GraphOptions` is frozen/kw-only with required `semantics: GraphSemantics`. `name` defaults to the class name in snake case; `description` is optional non-empty prose.
- `Graph` stores prepared options in `_graph_options` and the name in `_graph_name`. A concrete graph must declare its own `options = GraphOptions(...)`; inherited options are refused.
- `GraphLanguage.discover_declarations` allows zero graph declarations and raises `ValueError: a namespace may declare at most one Graph; found ...` for two or more. This is per namespace; the linker separately rejects a blueprint carrying more than one graph declaration.
- The graph declaration has no references (`get_references` returns `()`).
- The graph semantics is the only place `Purpose` can be authored.

### 3.4 Document and source behaviour

Canonical documents omit empty `claims`/`frames`/`limitations`; graph semantics always writes `purpose`. A missing purpose is a `ValueError`. Source rendering uses `repr`; `render_semantics` embeds `semantics=Semantics(...)`, `render_graph_semantics` embeds `semantics=GraphSemantics(...)`, and `render_semantics_expression` returns only the expression.

---

## 4. Asset model as implemented

### 4.1 Logical model

- An asset is one logical unit of source data; one asset may back many tables. The asset package itself does not count or constrain tables; `Table[Asset]` is in the data language and each concrete table names exactly one asset.
- Identity is the logical name: `options.name` when set, else snake case of the class name. `AssetRef` is a role-typed reference serialised as `["asset", "asset", "<name>"]`.
- `asset_name` accepts an `Asset` subclass, `AssetDescriptor` or `AssetDTO`; `asset_reference` returns the typed `AssetRef`.
- Asset classes are effectively terminal: `prepare_asset_declaration` reads `vars(cls)["options"]`, so a subclass that inherits options but does not assign its own options raises `TypeError: asset '<X>' must declare options = AssetOptions(...)`.
- Discovery selects every concrete `Asset` subclass in a namespace; `AssetLanguage` creates one `asset` symbol per class. Asset declarations declare no references.
- `AssetPartDTO` requires unique asset names; the codec emits an array; the document reader accepts either a bare array or an object with `assets`.

### 4.2 Options and parts

| Value | Required | Optional | Role |
| --- | --- | --- | --- |
| `AssetProfile` | `subject`, `coverage`, `authority`, `basis` | `title`, `description` | Descriptive source-data metadata; carries no claims/limitations. |
| `AssetOptions.semantics` | no | `Semantics` fragment | Authored meaning and limits. |
| `AssetLayout` | no | all fields | Descriptive layout metadata, not an access contract. |
| `AssetGovernance` | no | license, owner, metadata | Portable ownership/licensing facts. |
| `AssetOptions.annotations` | no | `Sequence[Annotation]` | Portable metadata; normalised to tuple. |
| `website`/`version` | no | non-empty strings | Human reference / free-text release label; not resolved. |

Normalisation:

- `AssetLayout.partition_by` is a tuple of non-empty strings; a bare string is rejected as `TypeError: asset layout partition keys must be a sequence of strings`.
- `members` and `properties` become `MappingProxyType` sorted by key.
- `AssetGovernance.metadata` likewise becomes a sorted, read-only mapping.
- `AssetAuthority` must be an `AssetAuthority` instance; codec accepts the enum value string and rejects unknown values with `ValueError: unknown asset authority ...`.
- `AssetOptions` accepts only `Semantics` for `semantics`, only `AssetLayout` for `layout`, only `AssetGovernance` for `governance`; `annotations` are checked element by element.

### 4.3 Identity, descriptor and lossiness

- `AssetDescriptor` is a frozen, authoring-independent snapshot: `name`, `website`, `version`, `layout`, `profile`, `governance`. It deliberately has **no** semantics or annotations fields. The distribution service builds it from `AssetDTO` (`distribution/service/_private/asset_tables.py`), so it is lossy relative to the blueprint asset.
- `AssetDescriptor` is public at `kg_build_system.distribution.languages.asset` but absent from the top-level facade and from `docs/reference/assets.md`.
- `AssetDTO` has no `__post_init__`; validation is inherited from the authoring values and the codec. `AssetPartDTO` is the only DTO that checks cross-asset uniqueness.

### 4.4 Codec legacy behaviour

`asset/service/_private/codec.py` supports a legacy shape: if an asset document has no `profile`, `_profile_document` reads the `semantics` member as the profile object (it must still carry profile fields). `_asset_from_document` then sets `semantics=None` because `profile` was absent. This is intentional (covered by `tests/distribution/test_asset_language.py::test_a_legacy_semantics_key_decodes_as_the_profile`) and is not described in the docs.

### 4.5 Descriptive vs contractual

- `profile`, `layout`, `governance`, `website`, `version` and annotations are descriptive data published in the blueprint; they do not enforce access, resolve credentials, prove tables exist, or pin a release.
- The nearest thing to a contract is the `Table[Asset]` relationship in the data language: a concrete table must name one asset, and a relation must carry an `AssetRef` that exists in `GraphBlueprint.assets` (the latter validation is in the interpreter, not the asset package).
- Generation is the exception that blurs the line: `InferDataContractProvider` uses `AssetLayout.locator` as a fallback `source` when the contract omits `source=`; the docs acknowledge this fallback. Layout is still not an access contract in the asset language itself.

---

## 5. Topology and binding

### 5.1 Declaration preparation

`Graph` and `Asset` prepare in `__init_subclass__`; topology prepares in `TopologyDeclarationBase.__init_subclass__`, one pass at class creation: skip framework roots; reject non-framework bases; determine node/edge/template side and reject mixed lineage; resolve property slots over the MRO; for templates record the annotation/semantics contribution and return; for graph-visible components determine tier, validate options kind, find at most one direct abstract category parent, reject concrete ancestry, compute effective annotations/semantics/description/name, resolve edge endpoints, and store `ComponentMetadata` plus compatibility aliases.

### 5.2 Naming and descriptions

- Component name: explicit `options.name` wins; otherwise class name with one tier suffix removed (`AbstractNode`/`AbstractEdge` for abstract, `Node`/`Edge` for concrete), then snake case. Example: `DocumentedAbstractNode` → `documented`.
- Property external name: explicit `name=` wins; otherwise attribute snake case with one trailing underscore removed (`options_` → `options`).
- Component description: own `options.description` if not `None`, else the class `__doc__`. A category's description is not inherited.
- Property description: explicit `description=` wins, else the string literal directly below the assignment, recovered with `inspect.getsource` + `ast`. Unreadable source yields no description.
- Duplicate property external names are rejected: `<Class> properties '<a>' and '<b>' share external name '<name>'`.
- A property reassigned in a subclass replaces the inherited declaration in the resolved map; a subclass attribute that is not a property descriptor removes the inherited slot. No runtime check compares the inherited and new logical types; the docs treat a redeclaration at another type as a static type error.

### 5.3 Property slots and types

- `property()` returns a `_PropertyDeclaration` descriptor typed as `PropertySlot[T]`.
- At class creation, the attribute must be annotated with exactly one type argument; otherwise `TypeError: <Class>.<attr> must be annotated as PropertySlot[T]`.
- The authoring type is normalised with `normalize_type` and checked with `require_graph_property`: scalars, `T | None`, flat `Array[T]`, and `Array[T] | None`. Structs, nested arrays and nullable array items are rejected.
- Property annotations and semantics are stored on the `PropertyDeclaration`, which becomes a `PropertyDTO` with `name`, `logical_type`, `PropertyRef`, description, annotations, semantics.

### 5.4 Templates

- `NodeTemplate`/`EdgeTemplate` are inert: no name, no description, no `ComponentMetadata`, no symbol, no binding target, no endpoint.
- Their properties are inherited through the MRO and become required properties of the host.
- Template annotation flow: all template `_template_annotations` in reverse MRO order (base template before derived), then the host's own `options.annotations`.
- Label uniqueness is checked against the complete effective set, so a template can make a host carry two matching labels and fail.
- Template semantics: the closest template with `_template_semantics` wins; the host's own `options.semantics` overrides it. A category's semantics is not copied to a concrete child.
- Template options must be the matching `*OptionsTemplate`; passing `NodeOptions`/`EdgeOptions` raises a targeted `TypeError`. A template with no own `options` inherits the base default and records an empty contribution.

### 5.5 Categories and edge endpoints

- A concrete component is terminal: no ancestor may be a non-abstract component.
- At most one direct abstract category parent; more than one raises `TypeError: <Class> has more than one abstract category parent: ...`.
- The nearest category parent is recorded as `metadata.parent`; categories may chain, but only the direct parent reference is stored.
- Edge endpoints are resolved from generic bases:
  - A class's own `Edge[S, D]`/`AbstractEdge[S, D]` arguments are `own`.
  - Inherited generic specs are collected from the ancestry.
  - Every category must be a node declaration (`component_kind == "node"`); templates, edges and plain classes fail.
  - If the edge declares its own pair, each side must equal or descend from every inherited abstract pair; widening fails.
  - If it declares no pair, it inherits the parent edge's source/target; with no parent it fails with `must declare its edge endpoints`.
- `endpoint(target)` requires a concrete node; `Endpoint(target)` direct construction skips that check.
- `GraphPartDTO` requires unique component names across nodes and edges; `validate_graph_part` additionally requires parent references to exist and be abstract, edge source/target to be nodes in the part, and parent chains to be acyclic.

### 5.6 What a binding does

A binding maps one row context onto one concrete node or edge:

- Direct form: `build_key` + `properties=<Target>(...)`; edges also need `source_build_key`, `target_build_key`. Every key must be a present scalar `Selection`; nullable, array and struct keys are refused.
- Row form: `rows=<row-source value>` + `bind=<callable>`; the callable receives a typed row proxy from `shape_context(rows.shape)` and must return `NodeValues`/`EdgeValues`. `mode` becomes `"python"`; the callable's module/qualname/signature become a `PythonRef`.
- The two forms are exclusive; mixing or supplying half of either raises.
- `rows` must be a row-source value, not a `Table`/`Projection` class; `as_row_source` enforces this.
- `properties` must be an instance of the exact target class. Every declared property, including inherited/template properties, must be assigned; extra attributes are refused. Each supplied value is converted to a `Selection`; a bare literal is refused with `<Target>.<property> must be assigned a selection`.
- Type compatibility: declared property type must equal the selection type, or differ only by a nullable wrapper in either direction. This accepts a nullable source selection for a declared non-null property and a non-null selection for a nullable property.
- Property values are sorted by external name in the frozen binding value and DTO.

### 5.7 Endpoint rules in bindings

- `_declared_endpoints(target)` reads `metadata.source`/`metadata.target`, with fallback attributes `_source`/`_target` and `_component_source`/`_component_target`.
- A token is required exactly when the declared side is an abstract category; absent token raises `TypeError: source_node must name the declared endpoint category <Category>: pass endpoint(...) for that side`.
- A supplied token must be an `Endpoint`; its target must be a concrete node; it must equal or descend from the declared category.
- A concrete declared side needs no token; supplying one is allowed and is recorded as the binding's `source_node`/`target_node`.
- `EdgeBindingDTO` stores `source_node`/`target_node` only when a token was supplied.

### 5.8 Binding identity, references and transcription

- `binding_identity` hashes the canonical document with `debug_name` and `python_ref` removed, truncates to 16 hex chars, and prefixes `debug_name:` when present.
- The document includes `kind`, target ref, identity, source/target identities, properties, rows, annotations, mode** and semantics. Therefore annotations and semantics distinguish otherwise identical bindings.
- `value_references` names the target component, supplied endpoint nodes, row-source scans and every expression leaf.
- Transcription sorts DTOs by kind, component, debug name and canonical document.
- `validate_bindings` rejects a duplicate identity after removing `python_ref`; duplicate detection therefore includes annotations and semantics. `transcribe_bindings` itself does not call it for a batch; `BindingLanguage` keys and the linker's duplicate-key check provide the batch-level guard.
- `transcribe_binding_part` validates the target against the topology part and validates endpoint refs; `_validate_rows` rejects row scans naming unknown logical data sources (excluding `derived:` names).

### 5.9 Source rendering of bindings

Direct bindings render `node_binding(target=..., build_key=..., properties=Target(...))`; Python bindings render `rows=...` plus `bind_reference(lambda row: NodeValues(...), ...)` when a `PythonRef` exists. Endpoints render as `endpoint(<Node>)`; semantics render inline; annotations render via `BindingOptions`. Property assignment uses `member_name(external_name)` with no `name=` recovery (see §9 #12).

---

## 6. Annotations and labels

### 6.1 Authoring shape

- `Annotation` is a frozen dataclass base. A concrete annotation is expected to be a frozen dataclass with `namespace` and `annotation_id` ClassVars and payload fields.
- The framework stores no annotation class: `annotation_payload` calls `asdict(annotation)`, producing the payload dict; `AnnotationDTO` stores `namespace`, `id`, `arguments`.
- `NodeLabel` and `EdgeLabel` are ordinary annotations with framework-defined identity.
- `annotation_tuple` normalises every `annotations=` sequence to a tuple and rejects non-annotations.
- Attachments in scope: `NodeOptions`, `EdgeOptions`, `NodeOptionsTemplate`, `EdgeOptionsTemplate`, `property()`, `AssetOptions`, `BindingOptions` (and generation `GeneratedField.annotations`).
- Not in this scope but referenced by docs: `TableOptions`, `field()`, `computed_field()`, `ProjectionOptions`, `StructOptionsTemplate`.

### 6.2 Labels

- `NodeLabel` namespace/id: `("kg_build_system.topology", "node_label")`.
- `EdgeLabel`: `("kg_build_system.topology", "edge_label")`.
- Topology transcription separates labels from other annotations:
  - A matching node/edge label's payload must contain a non-empty string `label`; it becomes an entry in `NodeDTO.labels`/`EdgeDTO.labels` and is removed from the annotation list.
  - The opposite kind's label raises `ValueError: a <kind> component cannot carry a <OtherLabel> annotation`.
  - Any other annotation is preserved as `AnnotationDTO(namespace, id, arguments)`.
- At most one matching label per component; the class-creation check and transcription both enforce it. Without a label, the target-facing label defaults to the logical name downstream (not stored in the DTO).
- Labels of the wrong kind are not converted; they remain ordinary annotations until a target reads labels, at which point docs say the target rejects them.

### 6.3 Path to outputs

- Blueprint: every reached declaration's annotations are carried as `AnnotationDTO`; topology labels are carried in the separate `labels` field; property annotations are carried on `PropertyDTO`; asset and binding annotations are carried on their DTOs.
- Source round trip: asset/topology/binding renderers use the shared `render_annotation` in `distribution/service/_private/rendering.py`, which resolves the loaded `Annotation` subclass by `(namespace, id)`, imports its module, and renders `Class(**payload)`. Labels render as `NodeLabel("...")`/`EdgeLabel("...")`.
- Final target outputs (`meta_graph.json`, Neo4j labels/types) are downstream consumers; this scope only produces the blueprint/DTO metadata.

---

## 7. Generation

### 7.1 `@asset_contract`

- `asset_contract` is an inert class decorator. It validates:
  - the argument is `AssetContractOptions`;
  - `provider` is a `Provider` subclass;
  - `configuration` is an instance of that provider's exact `CONFIG_TYPE`;
  - `package` is a non-empty dotted identifier;
  - the decorated class is an `Asset` subclass.
- It stores the options as `_asset_contract` and does no I/O, import, provider call or source read.
- `AssetContractOptions` has exactly `provider`, `configuration`, `package`.
- Static discovery does not import the project. It parses `.py` files containing the text `asset_contract` with LibCST and requires:
  - a module-level class;
  - exactly one non-starred base resolving to `Asset`;
  - exactly one inline `AssetContractOptions(...)`;
  - keyword-only options with exactly the three fields;
  - provider and configuration types statically imported (direct, qualified or aliased);
  - configuration constructed inline with keyword args and static literal values (str/int/float/bool/None/list/tuple/dict with string keys; no unpacking, stars or duplicates).
- A dynamically constructed configuration, a function/class-nested decorated class, a star import or a duplicate field is a `GenerationError` located at the source file and line.
- The asset's name (`AssetOptions.name` or snake-case class name) is the request identity; the product is `<package>/<asset name>`; the package import is `<package>.<asset name>`.
- `discover` scans the root, skips dotted directories and `__pycache__`, and rejects case-folded product collisions and request-id collisions.
- `discover_file` requires the source inside the project and parses only that file.

### 7.2 Observation and provenance

The built-in inference provider observes schema metadata only; it does not read data rows for inference.

- `describe` uses DuckDB `DESCRIBE` over `read_parquet`, `read_csv_auto` or `read_json_auto`, or a database relation. `DESCRIBE` decides columns and scalar types.
- `parquet_schema()` supplies nested shape/repetition, and `parquet_metadata()` supplies footer `stats_null_count` values.
- Nullability is decided by trust tier, not by observed row values:
  - `enforced` (database) can be `ENFORCED` when `DESCRIBE` says non-null;
  - `declared` (Parquet) uses `parquet_schema` repetition (`REQUIRED` → `DECLARED`, otherwise `DEFAULTED`);
  - `defaulted` (CSV/TSV/JSON) is always `DEFAULTED`.
- `schema_facts` records only schema-bearing facts: relation/class/source count/hive flag, column name/type/nullability, and nested node name/repetition/type. It does **not** record file bytes, names, sizes or locations.
- `schema_digest` is SHA-256 of those facts; the provider stamps it as `GeneratedPackage.source_digest`. The engine stores it in the manifest as provenance only; a digest change alone does not make a product stale.
- `NullabilityNote` lines are rendered into file headers:
  - `enforced`: “enforced by relation ... (NOT NULL)”;
  - `declared`: “declared by ... (required/optional)”;
  - `defaulted`: “not declared by ... - all members nullable”.
  A note with `declarations` is rendered only into files declaring one of those names; a note with no declarations is package-wide.
- `report_null_statistics` tests declared non-nullability against Parquet footer statistics. It logs warnings for violations and debug for unknown statistics; it never fails the pass. An absent statistic is not a zero count.
- Column overrides:
  - Key is `<relation path>.<column>` and must name a whole top-level column of an inferred relation.
  - `type` must be a canonical unit type; it may promote a declared-only physical type, but cannot promote a container or lift a refused type.
  - `nullable=True` declines a source non-null claim (`DEFAULTED`, leaves pre-flight); `nullable=False` asserts non-nullability (`DECLARED`, enters pre-flight).
  - Neither direction changes the rendered `Field[T]`; absent `nullable`/`type` keeps the source/reader's view.
  - Unmatched or nested override keys raise `GenerationError` with available names.

### 7.3 What generation renders

- A provider returns a `GeneratedPackage`, not source text. The engine renders twice and requires identical text before installing.
- Product files: `Table` declarations for concrete relations, `Struct` declarations for nested records, `TableGroup` declarations for group paths, an explicit `__init__.py` in every package directory, and a `.kbs-generation.json` manifest.
- Table group mode writes one file per table under group paths and one `__init__.py` per group; group classes contain `GeneratedMember` pointers to tables and nested groups.
- A generated table carries `GeneratedAsset(module, qualname)` and renders as `class XTable(Table[<Asset>]):`; the renderer imports the authored asset module.
- Fields render as `name: Field[T] = field(name='external', description=..., annotations=(...))`.
- Classes render `options = TableOptions(name=...)` or `TableGroupOptions(name=...)` when a declaration name is set; `Struct` and plain classes have no options.
- Header: do-not-edit line, `# request:`, `# fingerprint:`, applicable nullability note lines, formatter/type-checker directives, imports, declarations, optional `__all__`.
- Paths must be relative `.py` paths with no `..`; case-folded collisions, duplicate declarations, dangling/ambiguous references, and same-name import collisions are refused.
- The source package is validated by parsing with LibCST before installation.

### 7.4 What it must never add

- It must not add absence to a source-backed field. `GeneratedField.nullability` is provenance for the manifest, statistics and notes; `field_annotation()` returns only the value type. A source-backed field always renders `Field[T]`, whether the claim is `DEFAULTED`, `DECLARED` or `ENFORCED`. `| None` renders only when part of the value type (`GeneratedNullableType`), e.g. an array item or explicitly nullable computed result.
- It must not read data rows to infer structure or nullability; observation is `DESCRIBE`/Parquet schema/footer metadata.
- It must not rewrite the authored asset source or treat a hand-edited generated file as truth; a modified owned file is a conflict. It must not overwrite/delete unowned content, and a desired-path collision fails.
- It must not make a product stale because source data changed (only a request change or `--regenerate` re-observes), must not guess an unresolved/ambiguous generated reference, and must not use a generation-specific compilation path.

### 7.5 Ownership and desired-state behaviour

- Manifest records format version (`"6"`), request id, source package, provider module/qualname/version, request fingerprint, optional source digest, owned files/directories and file hashes. A product is current when format version, fingerprint and every owned hash match; it is not observed again.
- Request fingerprint includes provider identity/version, configuration/type, format version, request id, source package, asset module/qualname and `asset_digest`. `asset_digest` is SHA-256 of the whole asset source file text; `GenerationRequest`'s docstring says it covers “the asset source declaration”.
- `check=True` compares without mutation (`CURRENT`/`STALE` plus diagnostics; discovery/provider failures are errors). `regenerate=True` re-observes; with `check=True` it reports drift as `STALE` without writing.
- Watch regenerates only on declaration changes, ignores owned products and data-source changes, and reports added/changed/deleted requests before generation. Install is atomic; pruning is limited to verified owned files, empty owned directories and derived bytecode.

---

## 8. Invariants, validation errors and source paths

| Invariant / error | Raised when | Source path |
| --- | --- | --- |
| `a claim text must be a non-empty string` | `Claim("")` or non-str | `distribution/languages/semantics/model/public/units.py:51` |
| `a limitation text must be a non-empty string` | `Limitation("")` | `.../semantics/model/public/units.py:71` |
| `a frame text must be a non-empty string` | `Frame("")` | `.../semantics/model/public/units.py:100` |
| `a purpose text must be a non-empty string` | `Purpose("")` | `.../semantics/model/public/units.py:138` |
| `frame limitations must contain only Limitation values` | wrong member type | `.../semantics/model/public/units.py:104`; `.../service/_private/validation.py:16` |
| `purpose frames must contain only Frame values` | wrong member type | `.../semantics/model/public/units.py:142` |
| `semantics requires at least one claim or frame` | empty `Semantics()` | `.../semantics/model/public/units.py:186`; DTO `.../dto/semantics_dto.py:107` |
| `graph semantics purpose must be a Purpose` | wrong purpose type | `.../semantics/model/public/units.py:231` |
| `... must be a Semantics value, not GraphSemantics` | declaration attaches meaning root | `.../semantics/model/public/units.py:242` |
| `graph options semantics must be GraphSemantics` / `must carry a Purpose` | wrong options semantics | `.../graph/model/public/options.py:59` |
| `graph '<X>' must declare options = GraphOptions(...)` | missing own options | `.../graph/service/_private/declarations.py:20` |
| `a namespace may declare at most one Graph; found ...` | two graph declarations | `.../graph/service/internal/adapters/kernel_language.py:63` |
| `a graph declaration requires semantics` | document missing semantics | `.../graph/service/_private/codec.py:59` |
| `a graph semantics document requires a purpose` | document missing purpose | `.../semantics/service/_private/codec.py:145` |
| `asset '<X>' must declare options = AssetOptions(...)` | missing/wrong own options | `.../asset/service/_private/declarations.py:18` |
| `asset '<X>' has no usable name` | empty inferred name | `.../asset/service/_private/declarations.py:22` |
| `asset names must be unique` | duplicate `AssetDTO.name` | `.../asset/model/internal/dto/asset_dto.py:78` |
| `unknown asset authority ...` | codec unknown authority | `.../asset/service/_private/codec.py:148` |
| `... is not an asset declaration or descriptor` | `asset_name` wrong value | `.../asset/model/public/descriptor.py:76` |
| `annotations must contain only Annotation values` | non-annotation in sequence | `.../annotations/service/_private/validation.py:11` |
| `node labels require a non-empty label` / edge form | falsy label | `.../annotations/model/public/labels.py:31` |
| `... inherits non-framework base ...` | non-framework MRO base | `.../topology/service/_private/class_creation.py:189` |
| `... cannot mix node-side and edge-side lineage` | mixed templates/components | `.../topology/service/_private/class_creation.py:201` |
| `... must inherit from Node, AbstractNode, ...` | no framework lineage | `.../topology/service/_private/class_creation.py:206` |
| `... is a node template: its options must be NodeOptionsTemplate ...` | template with component options | `.../topology/service/_private/class_creation.py:36` |
| `... is a graph component declaration: declare NodeOptions ...` | component with template options | `.../topology/service/_private/class_creation.py:63` |
| `... has more than one abstract category parent` | multiple direct category parents | `.../topology/service/_private/class_creation.py:236` |
| `... cannot inherit from concrete graph component ...` | concrete ancestor | `.../topology/service/_private/class_creation.py:229` |
| `... has N node labels in its effective annotations; a graph component carries at most one` | duplicate matching labels | `.../topology/service/_private/class_creation.py:76` |
| `... must declare its edge endpoints` | concrete edge with no pair/parent | `.../topology/service/_private/class_creation.py:158` |
| `... endpoints (...) must equal or descend from its abstract edge lineage (...)` | widening | `.../topology/service/_private/class_creation.py:147` |
| `... endpoint category ... is not a node declaration` | endpoint not node-side | `.../topology/service/_private/class_creation.py:100` |
| `'<X>' is not a concrete node` | `endpoint()` non-concrete | `.../topology/service/_private/class_creation.py:321` |
| `property names must be non-empty` / `<Class>.<attr> must be annotated as PropertySlot[T]` | empty property name or wrong annotation | `.../topology/model/_private/properties.py:52,145` |
| `<Class> properties '<a>' and '<b>' share external name '<name>'` | duplicate external names | `.../topology/model/_private/properties.py:158` |
| `topology components require a non-empty name` | empty component name | `.../topology/service/_private/validation.py:19` |
| `component '<X>' carries at most one label` / `property names must be unique` | DTO component invariants | `.../topology/service/_private/validation.py:24,26` |
| `topology component names must be unique` | duplicate node/edge names | `.../topology/model/internal/dto/blueprint_dto.py:165` |
| `a <kind> component cannot carry a <OtherLabel> annotation` | wrong-kind label | `.../topology/service/_private/transcription.py:56` |
| `edge '<X>' does not declare both endpoints` | transcription edge without pair | `.../topology/service/_private/transcription.py:151` |
| `node/edge '<X>' parent '<Y>' is not ... abstract` | invalid parent | `.../topology/service/_private/transcription.py:268` |
| `component parent chain cycle includes ...` | parent cycle | `.../topology/service/_private/transcription.py:224` |
| `target must be a concrete node/edge component` | abstract/template/wrong target | `.../binding/service/_private/factories.py:132` |
| `node_binding takes either build_key/properties or rows/bind` | both forms | `.../binding/service/_private/factories.py:258` |
| `rows and bind must be supplied together` | half row form | `.../binding/service/_private/factories.py:262` |
| `node_binding requires build_key and properties, or rows and bind` | incomplete direct form | `.../binding/service/_private/factories.py:271` |
| `rows must be a row source value; ...` | `rows=Table` | `.../binding/service/_private/factories.py:126` |
| `node_binding bind must return NodeValues` | wrong `bind` result | `.../binding/service/_private/factories.py:267` |
| `properties must be an instance of <Target>` | wrong properties instance | `.../binding/service/_private/factories.py:84` |
| `<Target> has no declared property <names>` | extra property | `.../binding/service/_private/factories.py:88` |
| `<Target>.<prop> must be assigned a selection` | bare value | `.../binding/service/_private/factories.py:108` |
| `<Target>.<prop> expects <type>, but the selection resolves to <type>` | incompatible logical type | `.../binding/service/_private/factories.py:111` |
| `build_key must be a selection` / `must be a scalar` / `must not be nullable` | key rules | `.../binding/service/_private/factories.py:54`; kernel `require_non_nullable`/`require_scalar` |
| `source_node must name the declared endpoint category ...` | missing abstract endpoint token | `.../binding/service/_private/factories.py:171` |
| `source_node must be an endpoint(...) token` | raw class token | `.../binding/service/_private/factories.py:176` |
| `source_node <Node> must equal or descend from ...` | wrong concrete endpoint | `.../binding/service/_private/factories.py:191` |
| `pass semantics either to the binding or to BindingOptions, not both` | conflicting semantics | `.../binding/service/_private/factories.py:222` |
| `binding property names must be unique` / `unknown binding mode` / `a python binding requires a row plan` | DTO invariants | `.../binding/service/_private/validation.py:22` |
| `binding '<X>' has a duplicate identity` | duplicate canonical binding | `.../binding/service/_private/transcription.py:237` |
| `binding reads unknown logical source(s): ...` | row plan targets unknown data source | `.../binding/service/_private/transcription.py:187` |
| `binding targets an unknown component ...` | target absent from topology | `.../binding/service/_private/transcription.py:258` |
| `@asset_contract can only decorate an Asset subclass` | decorator validation | `.../generation/code_generation/service/_private/contract.py:30` |
| `asset contract provider must be a code-generation Provider` | wrong provider | `.../contract.py:25` |
| `<Provider> requires <Config>` | configuration type mismatch | `.../contract.py:27` |
| `asset contract package must be a non-empty string` / `not a dotted identifier` | bad package | `.../contract.py:14` |
| `asset contracts must be declared at module level` | nested class | `.../discovery.py:197` |
| `an asset contract requires one Asset base class` | multiple/parameterized bases | `.../discovery.py:198` |
| `@asset_contract requires one inline AssetContractOptions(...)` | wrong decorator argument | `.../discovery.py:202` |
| `AssetContractOptions accepts keyword arguments only` / `unknown/duplicate/missing field` | option shape | `.../discovery.py:218-230` |
| `provider/config type must be statically imported` / `configuration accepts keyword arguments only` | unresolved or positional config | `.../discovery.py:238-249` |
| `asset contract configuration values must be static literals` | dynamic value | `.../discovery.py:79` |
| `assets contract identity collision ...` / `product collision ...` | duplicate names/products | `.../discovery.py:334-344` |
| `owned generated file was unexpectedly modified` | manifest hash/header mismatch | `.../engine.py:80` |
| `refusing to overwrite unrecognized content at ...` | unowned desired path | `.../engine.py:237` |
| `provider ... did not render deterministically` | two renders differ | `.../engine.py:192` |
| `invalid generated Python path ...` | absolute/`..`/non-`.py` | `.../rendering/package.py:22` |
| `case-normalized generated path collision` | case-folded duplicate path | `.../rendering/package.py:69` |
| `duplicate generated declaration identity ...` | two classes same name in file | `.../rendering/package.py:75` |
| `generated reference ... names no declaration in the package` | dangling name | `.../rendering/package.py:106` |
| `generated reference ... is ambiguous across ...` | unbound duplicate name | `.../rendering/package.py:111` |
| `generated file ... would import <name> from both ...` | import shadow collision | `.../rendering/package.py:155` |
| `data-contract inference requires source= or an asset layout with a locator` | no source/locator | `.../builtins/provider.py:57` |
| `directory inference requires mode='table_group'` | directory/table mode | `.../builtins/provider.py:270` |
| `table-contract inference requires relation= when ... multiple` | ambiguous relation | `.../builtins/provider.py:279` |
| `data input ... has no relation ...` | relation not exposed | `.../builtins/provider.py:284` |
| `layout=... requires mode='table_group'` | bad layout/mode pair | `.../builtins/provider.py:239` |
| `data-contract inference input ... is a DuckDB database` | database source | `.../builtins/provider.py:241` |
| `override key ... is not a full column path` | bad key | `.../builtins/overrides.py:100` |
| `the override ... does not name a canonical unit type` | bad type | `.../builtins/overrides.py:112` |
| `override names ... reaches inside column ...` | nested path | `.../builtins/overrides.py:159` |
| `override names ... not a column ... reports` | unknown column | `.../builtins/overrides.py:167` |
| `an untyped NULL column is an absent declaration` | `NULL` digest | `.../builtins/mapping.py:132` |

---

## 9. Surprising, ambiguous and doc/code disagreements

| # | Observation | Evidence | Status |
| --- | --- | --- | --- |
| 1 | Reference topology signatures omit `semantics` from `NodeOptions`, `EdgeOptions`, `NodeOptionsTemplate`, `EdgeOptionsTemplate` and `property()`, but the code and `docs/concepts/semantics-language.md` include it. | `docs/reference/topology.md:46-58,88-95,161-166` vs `topology/model/public/options.py:38-113`, `topology/model/public/declarations.py:37-55` | Doc lag; code is authoritative. |
| 2 | Reference bindings signatures omit `semantics` and describe `BindingOptions` as annotations-only; code has semantics on both. | `docs/reference/bindings.md:31-57,291-299` vs `binding/model/public/values.py:77-102`, `binding/service/public/builders.py:43-56` | Doc lag. |
| 3 | Docs say annotations do not distinguish otherwise identical bindings; code includes annotations (and semantics) in the canonical document, duplicate check and identity hash. | `docs/reference/bindings.md:343-355` vs `binding/service/_private/transcription.py:218-240`, `symbols.py:58-69`, `codec.py:289-320` | Doc/code disagreement. |
| 4 | Docs say a nullable selection for a required property is refused; `_compatible` accepts a nullable actual type when its `value` equals the declared type. The test suite uses this (`properties=SiteNode(site_id=SiteTable.site_id)` where the source read is nullable). | `docs/reference/bindings.md:223-230` vs `binding/service/_private/factories.py:71-77`; `tests/distribution/test_binding_semantics.py:98-103` | Likely stale doc, but behavior may be intentional. |
| 5 | `NodeLabel`/`EdgeLabel` only reject falsy labels. Non-string truthy values and whitespace-only strings pass authoring; non-strings later fail topology transcription (`label` must be a non-empty string), whitespace passes. Docs claim both are rejected at authoring. | `annotations/model/public/labels.py:31-35` vs `docs/reference/semantics.md:112-117`; `topology/service/_private/transcription.py:45-50` | Authoring/blueprint validation asymmetry. |
| 6 | Docs say `InferDataContractProvider.VERSION = "7"`; code says `"8"`. | `docs/reference/generation.md:432-434` vs `builtins/provider.py:72` | Stale doc. |
| 7 | Docs say the request fingerprint contains “no source content and no source-content digest”; code includes `asset_digest`, the SHA-256 of the whole author-owned asset source file. The `GenerationRequest` docstring says it covers the asset source declaration. | `docs/reference/generation.md:264-268` vs `rendering/fingerprint.py:18-29`, `service/_private/discovery.py:309,267`, `model/public/requests.py:22-23` | Wording disagreement; declaration source is included, data source is not. |
| 8 | `AssetDescriptor` is exported by the asset package but absent from the top-level facade and reference docs, and it drops `semantics` and `annotations`. | `asset/model/public/descriptor.py:16-47`; `kg_build_system/__init__.py:65-71` | Undocumented lossy projection. |
| 9 | Asset document decoding treats a top-level `semantics` key as the profile when `profile` is absent. | `asset/service/_private/codec.py:216-225`; test `tests/distribution/test_asset_language.py:238-260` | Intentional legacy compatibility, undocumented. |
| 10 | `NodeOptions`/`EdgeOptions` accept `name=""` and `description=""`. Empty name silently falls back to the inferred name; empty description survives authoring but fails DTO validation (`description must be non-empty`). | `topology/model/public/options.py:45-61`; `topology/service/_private/class_creation.py:266-274`; `topology/service/_private/validation.py:28` | Asymmetric validation; surprising. |
| 11 | Topology `require_semantics` reports “must be a Semantics value, not GraphSemantics” for any non-`Semantics` object, not only `GraphSemantics`. | `topology/model/internal/model/metadata.py:44-55` | Misleading message. |
| 12 | Binding source rendering writes property assignments by `member_name(external_name)` with no `name=` recovery. A property declared with a custom external name may not round-trip. | `binding/service/_private/source.py:328-334,389-395`; `topology/model/_private/properties.py:120-155` | Likely defect, not run/verified. |
| 13 | `AssetLayout` is described as “not an access contract”, but generation uses `layout.locator` as a fallback source and the DuckDB planner uses the layout to resolve locations. | `docs/concepts/assets.md:176-194`; `builtins/provider.py:49-59`; `docs/reference/assets.md:219-244` | Tension between descriptive model and consumers. |
| 14 | `Semantics`/`Claim`/`Frame` text validation rejects only `""`, so whitespace-only text is valid, while docs say “non-empty” and label docs mention whitespace. | `semantics/service/_private/validation.py:10-13`; `docs/concepts/semantics-language.md:78` | Validation gap. |

### 9.1 Ambiguities to resolve with the KB team

- **Nullable property selections and binding identity**: Is permissive `_compatible` intended, and should annotations/semantics distinguish bindings? Code and docs disagree on both; tests depend on the nullable case.
- **Asset fingerprint / descriptor / legacy document**: Is `asset_digest` whole-module or declaration-only; does `AssetDescriptor` intentionally drop semantics/annotations; is `semantics`-as-profile a versioned migration rule?
- **Round-trip and label validation**: Verify custom external property names in binding source; decide whether labels/semantics should reject whitespace and non-string labels at authoring.

`unclear`: the points above; no runtime reproduction was performed.
