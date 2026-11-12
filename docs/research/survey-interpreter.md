# Survey: `distribution/interpreter` and `distribution/service`

Read-only survey of `/home/paul/Repos/kg-build-system`. Scope:
`kg_build_system/distribution/interpreter/**`,
`kg_build_system/distribution/service/**`, and
`distribution/implementations.py`. Paths are relative to
`kg_build_system/distribution/` unless stated otherwise. "Unclear" marks points
the code does not settle. No source file was modified.

## 1. File and package map

### 1.1 Interpreter facades and model

| Paths | Responsibility |
| --- | --- |
| `interpreter/__init__.py`, `interpreter/model/public/__init__.py`, `interpreter/service/public/__init__.py` | Facades. `interpreter/__init__.py` exports both; `model/public` re-exports `GraphBlueprint`; `service/public` re-exports `create_blueprint`. |
| `interpreter/model/__init__.py`, `interpreter/service/__init__.py`, `interpreter/service/_private/__init__.py` | Docstring-only package markers. |
| `interpreter/model/public/graph_blueprint.py` | Defines the frozen public `GraphBlueprint`; imports field types from language-internal DTO modules. |
| `interpreter/service/public/create.py` | Author-facing wrapper; function-local import of `_private.create`. |

### 1.2 Interpreter internal and private service

| Paths | Responsibility |
| --- | --- |
| `service/internal/__init__.py`, `service/internal/adapters/__init__.py` | `service/internal/__init__.py` exports `BlueprintLinker`, `assemble_blueprint`, `blueprint_to_document`, `blueprint_from_document`, `blueprint_to_source`, `validate_blueprint`; `adapters/__init__.py` exports `BlueprintLinker`. |
| `service/internal/adapters/kernel_linker.py` | `BlueprintLinker`, the kernel `Linker` implementation; stores optional `roots`, delegates to `link_blueprint`. |
| `service/internal/{assembly,codec,link,source,validation}.py` | Thin wrappers over `_private` equivalents; function-local private imports. |
| `service/_private/create.py` | Chooses explicit bindings vs. path namespace, builds default languages and `Toolchain`, calls `toolchain.build`. |
| `service/_private/discovery.py` | `_Values`, `_Namespace`, `_ModuleNamespace`, `namespace_modules`, `_table_declarations`, `_with_assets`. |
| `service/_private/link.py` | Actual linker: `ORDER`, `_LanguageResolver`, `_index_language`, `order_symbols`, `_assemble`, `link_blueprint`. |
| `service/_private/assembly.py` | `assemble_blueprint(...)`, a structural constructor. |
| `service/_private/validation.py` | `validate_blueprint(...)`, cross-layer name/reference checks. |
| `service/_private/codec.py` | Blueprint codec composing layer codecs. |
| `service/_private/source.py` | `blueprint_to_source`, joining language fragments and imports. |

### 1.3 Distribution service zone

| Paths | Responsibility |
| --- | --- |
| `service/public/{create,asset_tables,__init__}.py` | Public `create_blueprint`, `asset_tables`, `table_relations`, `AssetTable`, `AssetColumn`. |
| `service/internal/asset_tables.py` | Thin asset-table wrappers. |
| `service/internal/emission.py` | Neutral relational plan (`Scan`, `Expand`, `Filter`, `RelationPlan`), SQL type values, `RelationSqlEmitter`, `SqlEmitter`. This is the core/engine boundary. |
| `service/internal/execution.py` | Wrappers for output paths, relation service, query, Parquet export, input values. |
| `service/internal/relations.py` | Executor-side `RelationService` protocol. |
| `service/internal/rendering.py` | Stable import surface for shared source-form helpers. |
| `service/_private/asset_tables.py` | Which asset-backed relations a graph reads; `kg_table_<n>` mapping. |
| `service/_private/execution.py` | Reads `OutputStorage` / `RelationService`; input/artifact helpers. |
| `service/_private/rendering.py` | Pure source-form helpers (`class_name`, `member_name`, `render_logical_type`, etc.). |
| `../implementations.py`, `../__init__.py` | Export/implementation list and distribution facade: all language classes, `BlueprintLinker`, `GraphBlueprint`, `create_blueprint`. |
| `../model/public/refs.py` | Role refs wrapping `SymbolRef`: `NodeRef`, `EdgeRef`, `RelationRef`, `FieldRef`, `PropertyRef`, `AssetRef`, `OperationRef`. |

## 2. `GraphBlueprint`: fields and name visibility

```python
@dataclass(frozen=True, slots=True)
class GraphBlueprint:
    graph: GraphPartDTO
    data: DataPartDTO
    assets: AssetPartDTO
    bindings: tuple[BindingDTO, ...]
    graph_declaration: GraphDeclarationDTO | None = None
```

| Field | Type | Owning layer / module | Public? | Default | Meaning |
| --- | --- | --- | --- | --- | --- |
| `graph` | `GraphPartDTO` | topology, `languages/topology/model/internal/dto/blueprint_dto.py` | No | required | Nodes/edges, labels, properties, annotations, `abstract`, `parent`, endpoints. |
| `data` | `DataPartDTO` | data, `languages/data/model/internal/dto/blueprint_dto.py` | No | required | Structs, relations, projections, columns, row-source plans. |
| `assets` | `AssetPartDTO` | asset, `languages/asset/model/internal/dto/asset_dto.py` | No | required | Logical source-data units named by relations. |
| `bindings` | `tuple[BindingDTO, ...]` | binding, `languages/binding/model/internal/dto/blueprint_dto.py` | No; `BindingDTO` is an internal alias | required | Flat `NodeBindingDTO \| EdgeBindingDTO` tuple. |
| `graph_declaration` | `GraphDeclarationDTO \| None` | graph, `languages/graph/model/internal/dto/graph_dto.py` | No | `None` | Project-level graph declaration and `GraphSemanticsDTO` meaning root. |

Public names in this scope: `GraphBlueprint`, `create_blueprint`,
`BlueprintLinker` (also via `implementations.py` and `distribution/__init__.py`),
the role refs in `distribution/model/public/refs.py`, and `AssetTable`,
`AssetColumn`, `asset_tables`, `table_relations`.

Internal names not exported by the interpreter facade: all layer DTOs
(`GraphPartDTO`, `NodeDTO`, `EdgeDTO`, `PropertyDTO`, `DataPartDTO`,
`StructDTO`, `RelationDTO`, `ProjectionDTO`, `ColumnDTO`, all `Row*DTO`,
`Asset*DTO`, `BindingDTO`, `NodeBindingDTO`, `EdgeBindingDTO`,
`GraphDeclarationDTO`, `SemanticsDTO`), plus `assemble_blueprint`,
`validate_blueprint`, the codec and source functions. The developer docs
explicitly acknowledge this: `GraphBlueprint` is public, its fields are typed by
language DTOs that are not public names.

`validate_blueprint` requires, when `graph_declaration` is present: a
`GraphDeclarationDTO`; `semantics` of type `GraphSemanticsDTO`; a `PurposeDTO`
purpose; non-empty purpose text. `GraphDeclarationDTO.__post_init__`
independently requires a non-empty name, `GraphSemanticsDTO` semantics, and a
null-or-non-empty description.

## 3. `create_blueprint` and `BlueprintLinker`: exact sequence

### 3.1 Call chain

```text
create_blueprint (public)
  -> _private.create.create_blueprint
     -> _ModuleNamespace(namespace_modules(path)) or _Namespace(bindings)
     -> Toolchain(languages=..., linker=BlueprintLinker()).build(namespace)
        -> kernel build_model
           -> BlueprintLinker.link -> link_blueprint
              -> _index_language per language
              -> references_for / collect / order
              -> language.transcribe per reachable declaration
              -> _assemble -> order_symbols -> assemble_blueprint
                 -> validate_blueprint
```

### 3.2 Method-by-method

| Step | Method / function | What it does | Failure modes |
| --- | --- | --- | --- |
| Entry | `_private.create.create_blueprint` | Rejects `namespace_path` plus non-empty `bindings`; builds namespace; constructs `Toolchain` with default languages and `BlueprintLinker`; calls `toolchain.build(namespace)`. | `ValueError("namespace_path cannot be combined with bindings")`; import errors. |
| Discovery | `language.discover_declarations(namespace)` in `_index_language` | Each language selects declarations; namespace only supplies `.values()`. | Language exceptions (`GraphLanguage` rejects >1 graph). |
| Keying | `language.compute_key(declaration)` | Stores `indexed[SymbolRef(language.name, key)] = (language, declaration)`. | `ValueError("language '<name>' declares key <key> twice")`. |
| Resolver | `_LanguageResolver(...)` | `get_identity` across languages, rejects multiple claims. | `ValueError("more than one language claims value identity: ...")`. Dormant: no `get_references` calls it. |
| Roots | `root_names = available if roots is None else roots` | `available` = `ORDER` filtered to supplied names. Roots select declarations by `SymbolRef.language`. | `ValueError("unknown root language(s): ...")` only for names absent from `by_name`; non-`ORDER` supplied names are silently ignored. |
| Reference | `references_for(reference)` -> `language.get_references(declaration.value, resolver)` | Direct dependencies of the **authoring value**, cached by ref. | `ValueError("unknown symbol reference <ref>")`; language exceptions. |
| Closure | `collect(reference)` | Marks reachable then recurses. Marks before recursion, so cycles terminate here. | Unknown ref from `get_references` raises. |
| Ordering | `order(reference)` | DFS state 1/2; dependencies first; appends post-order. | `ValueError("symbol reference cycle at <ref>")`. |
| Transcription | `language.transcribe(declaration, SymbolContext(symbols))` | Once per reachable declaration, dependencies first; context snapshots already-transcribed symbols. | Language exception; key mismatch `ValueError("language '<name>' transcribed <key> as <key>")`. |
| Rewrite | `replace(symbol, references=references_for(reference))` | Linker overwrites the symbol's `references` with its own result. | None. |
| Assembly | `_assemble(symbols)` | Calls `order_symbols` again; buckets values by DTO type; rejects >1 graph declaration; calls `assemble_blueprint`, then `validate_blueprint`. | `ValueError("the blueprint carries more than one graph declaration")`; validation errors (section 8). |

### 3.3 Constants and roots

```python
ORDER = ("expressions", "asset", "data", "topology", "binding", "graph")
_REQUIRED = tuple(name for name in ORDER if name != "graph")
```

`graph` is optional; the other five are required. `roots=None` includes every
supplied language in `ORDER`, so all discovered declarations become reachable.
A narrow root set such as `("binding",)` follows bindings into data, topology,
asset and expressions; the graph declaration is included only if `"graph"` is in
the root set. Duplicate language names are rejected before roots are evaluated.

### 3.4 Other linker failure modes

| Condition | File | Exception / message |
| --- | --- | --- |
| Duplicate language name | `interpreter/service/_private/link.py` | `ValueError(f"duplicate language name {name!r}")` |
| Missing required language | same | `ValueError("the graph linker requires languages " + ...)` |
| Unknown root | same | `ValueError("unknown root language(s): " + ...)` |
| Two languages claim one value identity | same | `ValueError("more than one language claims value identity: ...")` |
| Unknown symbol reference | same | `ValueError(f"unknown symbol reference {reference}")` |
| Reference cycle | same | `ValueError(f"symbol reference cycle at {reference}")` |
| Transcription key mismatch | same | `ValueError(f"language {name!r} transcribed {reference.key!s} as {symbol.key!s}")` |
| >1 graph declaration in symbols | same | `ValueError("the blueprint carries more than one graph declaration")` |
| >1 `Graph` at discovery | `languages/graph/service/internal/adapters/kernel_language.py` | `ValueError("a namespace may declare at most one Graph; found ...")` |
| `order_symbols` unknown ref / cycle | `interpreter/service/_private/link.py` | Same two messages as above. |

## 4. Keys, `SymbolRef` identity, and closure resolution

### 4.1 Kernel identity

`Key` is `segments: tuple[str, ...]`; `str(key)` joins segments with `/`.
`SymbolRef` is exactly `(language, key)`; `str` is `language:key`.
`Symbol` is `(key, kind, value, references=())`. Role refs wrap a `SymbolRef`;
their equality/hash delegate to the wrapped ref, so role is a serialization
token, not part of identity.

### 4.2 Per-language key and identity derivation

| Language | Key | `get_identity(value)` | Source |
| --- | --- | --- | --- |
| `expressions` | `Key((spec.name,))` per `DEFAULT_OPERATIONS` | `OperationSpec` or known name -> `OperationRef("expressions", Key((name,)))`; else `None` | `languages/expressions/service/_private/symbols.py` |
| `asset` | `Key((asset_name(value),))` | asset declaration or `AssetDTO` -> `SymbolRef("asset", Key((name,)))` | `languages/asset/service/_private/symbols.py` |
| `data` | graph name `Key((name,))`; repeated/colliding struct: `Key((name, f"{module}.{qualname}"))`; field: `Key((f"{owner}.{field}",))` | field/declaration/`ColumnDTO`/relation/projection -> corresponding data ref | `languages/data/service/_private/symbols.py` |
| `topology` | node/edge `Key((name,))`; property `Key((f"{owner}.{prop}",))` | property/node/edge/DTO -> corresponding ref | `languages/topology/service/_private/symbols.py` |
| `binding` | `Key((binding_identity(value),))` | binding value/DTO -> `SymbolRef("binding", Key((binding_identity(value),)))` | `languages/binding/service/_private/symbols.py` |
| `graph` | `Key((value._graph_name,))`; DTO `Key((dto.name,))` | graph declaration/DTO -> graph ref | `languages/graph/service/_private/symbols.py` |

Data qualification: `DataLanguage.discover_declarations` computes
`_name_counts` over non-field declarations; `needs_qualified_struct` is true
only when a struct's graph-name count exceeds 1. `declaration_key(..., qualify_struct=True)`
then returns `Key((name, f"{module}.{qualname}"))`. A unique struct keeps the
bare name; a struct colliding with a relation/projection is qualified while the
relation/projection keeps the bare key. `_name_counts` is assigned on the
instance after discovery, and `compute_key`/`get_identity` depend on the most
recent batch.

Binding identity: `binding_to_document(dto)`, pop `debug_name` and `python_ref`,
canonical JSON (`sort_keys=True, separators=(",", ":")`, `default=str`),
SHA-256 hex first 16 chars; return `f"{debug_name}:{digest}"` if debug name is
truthy, else the digest. It includes target, identity, properties, rows, mode,
annotations and semantics; it excludes `python_ref` from the digest.

### 4.3 Closure resolution, in code order

```python
indexed = {}
for name in available:
    for key, declaration in _index_language(by_name[name], namespace):
        indexed[SymbolRef(name, key)] = (by_name[name], declaration)
references = {}
def references_for(reference):
    if reference in references: return references[reference]
    language, declaration = indexed[reference]      # unknown -> ValueError
    references[reference] = tuple(
        language.get_references(declaration.value, resolver))
    return references[reference]
reachable = {}
def collect(reference):
    if reference in reachable: return
    if reference not in indexed:
        raise ValueError(f"unknown symbol reference {reference}")
    reachable[reference] = None
    for dependency in references_for(reference):
        collect(dependency)
for reference in indexed:
    if reference.language in root_languages: collect(reference)
ordered, state = [], {}
def order(reference):
    status = state.get(reference)
    if status == 1: raise ValueError(f"symbol reference cycle at {reference}")
    if status == 2: return
    state[reference] = 1
    for dependency in references_for(reference): order(dependency)
    state[reference] = 2
    ordered.append(reference)
for reference in reachable: order(reference)
symbols = {}
for reference in ordered:
    language, declaration = indexed[reference]
    symbol = language.transcribe(declaration, SymbolContext(symbols))
    if symbol.key != reference.key: raise ValueError(...)
    symbols[reference] = replace(symbol, references=references_for(reference))
return _assemble(symbols)
```

Key properties: the closure is resolved from `get_references` before any
transcription; unreachable declarations are never transcribed; references are
cached; `collect` marks before recursion so cycles terminate; `order` is a
global dependency-first DFS, not per-language; `SymbolContext` copies the dict
into a read-only mapping; the linker overwrites `Symbol.references` after
transcription, so only `get_references` affects ordering; `_assemble` calls
`order_symbols` a second time, redundantly re-checking unknown refs and cycles.

### 4.4 Dormant resolver

`_LanguageResolver.get_identity` is constructed and passed to every
`get_references`, but every current language discards the resolver (`del
resolver`) or ignores it. `get_identity` is therefore not exercised on the
normal link path, and the multi-claim check only runs if a language calls it.
References are built directly from authoring metadata.

## 5. Transcription contract per language

### 5.1 Kernel signatures

```python
class Language(Protocol):
    name: str
    def discover_declarations(self, namespace: Namespace) -> Iterable[Declaration]: ...
    def compute_key(self, declaration: Declaration) -> Key: ...
    def get_kind(self, declaration: Declaration) -> str: ...
    def get_identity(self, value: Any) -> SymbolRef | None: ...
    def get_references(self, value: Any, resolver: ReferenceResolver) -> tuple[SymbolRef, ...]: ...
    def transcribe(self, declaration: Declaration, context: SymbolContext) -> Symbol: ...
    def render(self, symbol: Symbol, context: RenderContext) -> SourceFragment: ...
```

`SourceFragment(kind: Literal["inline", "declaration"], body: str, imports: tuple[str, ...] = ())`.

### 5.2 What a language must return

- `discover_declarations` returns `Declaration` values; the linker does not
  inspect the wrapped authoring value. `compute_key` returns a `Key` unique
  within that language; duplicate detection is the linker's.
- `get_references`: **direct** dependencies only, as `SymbolRef`s; the linker
  expands recursion. It receives the authoring declaration value, not a DTO.
- `transcribe`: one `Symbol` whose `key` equals the indexed key and whose
  `value` is a DTO type the assembly stage recognizes. Its `references` field is
  overwritten by the linker and is advisory.
- `get_kind` and `get_identity` are not called by `BlueprintLinker` in normal
  linking; `render` is called only by `blueprint_to_source`. `SymbolContext` is
  read-only and holds dependencies already transcribed; `get_symbol` raises
  `KeyError(f"unknown symbol {reference}")`.

### 5.3 Per-language behavior

| Language | `get_references` | `transcribe` result | Notes |
| --- | --- | --- | --- |
| `expressions` | For an `ExpressionNode`: field refs (skipping `derived:` sources), lookup relation refs, built-in operation refs. For the actual declaration value (`OperationSpec`): `()`. | `Symbol(Key((spec.name,)), "operation", spec)` | Discovers one declaration per `DEFAULT_OPERATIONS`; ignores namespace. Expression trees are values, not declarations. Custom operations outside `DEFAULT_OPERATIONS` are not symbols and are skipped by `authoring_references`. |
| `asset` | `()` | `Symbol(Key((dto.name,)), "asset", AssetDTO)` | `transcribe` raises `TypeError` for a non-asset. |
| `data` | Declaration: field refs; relation adds asset ref; projection adds scan-source data refs, plan expression refs and field expression refs. Field: expression leaf refs plus nested struct ref. | `StructDTO`, `RelationDTO`, `ProjectionDTO`, or `ColumnDTO` for a field. Columns rewritten with `FieldRef("data", field_key(owner, column.name))`. | Ignores `context`. Every field is its own declaration/symbol. Struct columns are not cross-validated by `validate_blueprint`. |
| `topology` | Node: property refs + parent ref. Edge: property refs + parent ref + source/target node refs. Property: `()`. | `Symbol(..., "node", NodeDTO)`, `... "edge", EdgeDTO`, or `... "property", PropertyDTO`. | Ignores `context`; node/edge `transcribe` calls `_validate_parent_chain`, rejecting cyclic, unknown or non-abstract parents. |
| `binding` | Target component ref; edge source/target node refs; rows scan-source data refs and plan expression refs; every build/source/target/property expression leaf. | `Symbol(Key((binding_identity(dto),)), "binding", dto)`. Uses `_PartContext` built from data/topology symbols in `context`, then `validate_bindings`. | The only language consuming `SymbolContext`. Rejects unknown row sources and unknown topology targets/endpoints. |
| `graph` | `()` | `Symbol(Key((dto.name,)), "graph", GraphDeclarationDTO)` | Zero or one `Graph` at discovery; two raise. |

### 5.4 Grouping by component
1. **Blueprint part grouping (assembly).** `_assemble` buckets by the runtime
   type of `symbol.value`: `StructDTO` -> `DataPartDTO.structs`;
   `RelationDTO` -> `.relations`; `ProjectionDTO` -> `.projections`;
   `AssetDTO` -> `AssetPartDTO.assets`; `NodeDTO` -> `GraphPartDTO.nodes`;
   `EdgeDTO` -> `.edges`; `NodeBindingDTO`/`EdgeBindingDTO` -> `bindings`;
   `GraphDeclarationDTO` -> `graph_declaration`. `ColumnDTO` and `PropertyDTO`
   are symbols but live inside their owner DTO, not directly in a part. Any
   other value type is ignored.
2. **Binding-by-component.** A binding DTO exposes `component` (`node.name` or
   `edge.name`). The batch helper `transcribe_bindings` sorts by
   `("node"|"edge", component, debug_name, canonical document)`, but the
   linker calls `symbol_for_declaration` per binding, so
   `GraphBlueprint.bindings` is in discovery/closure order, not necessarily
   sorted by target.
3. **Source-variable grouping.** `render_binding_source` names variables
   `<member_name(component)>_binding`; duplicate bases get `_<index>`. This is
   renderer-only.

`transcribe_graph_part` emits nodes/edges sorted by name, but the linker path
transcribes individual node/edge/property symbols. `DataPartDTO` has no
uniqueness check; duplicate relation/projection names are caught by the
linker's key check for authored declarations, not by the DTO or
`validate_blueprint`. `GraphPartDTO` and `AssetPartDTO` enforce unique names in
`__post_init__`.

## 6. Codec and document shape

### 6.1 Blueprint document

```python
def blueprint_to_document(blueprint: GraphBlueprint) -> dict[str, Any]
def blueprint_from_document(value: Mapping[str, Any]) -> GraphBlueprint
```

```json
{"graph_declaration": {...}, "graph": {"nodes": [...], "edges": [...]},
 "data": {"structs": [...], "relations": [...], "projections": [...]},
 "assets": [...], "bindings": [...]}
```

`graph`, `data`, `assets`, `bindings` are always written. `assets` is an array,
not an object; `bindings` is an array, one object per binding. Decoding requires
`graph` and `data`, defaults `assets` to `()`, accepts legacy `"binding"` for
`"bindings"`, and defaults `graph_declaration` to `None`. The codec composes
layer codecs and does not inspect layer DTOs.

### 6.2 Language document shapes

| Layer | Members |
| --- | --- |
| Graph declaration | `name`, optional `description`, required `semantics`. |
| Graph semantics | optional `claims`, required `purpose {text, frames?}`; frame `{text, limitations?}`. |
| Topology (`graph`) | `nodes`, `edges`. Node `{name, labels, abstract, properties, annotations, parent?, description?, semantics?}`; edge adds `source`, `target`. |
| Data (`data`) | `structs`, `relations`, `projections`. Struct `{name, columns, annotations, description?, semantics?}`; relation adds `asset`; projection adds `row_source`. Column `{name, logical_type, ref, annotations, description?, expression?, semantics?}`. |
| Row plan | `kind` plus: `scan{relation}`, `filter{input,predicate}`, `union{left,right,all}`, `join{left,right,left_key,right_key,how}`, `group_by{input,keys[{name,expression}]}`, `distinct{input}`, `order_by{input,keys[{expression,ascending}]}`, `unnest{input,field,expression}`. |
| Binding (`bindings[]`) | `kind` (`node`/`edge`), target (`node`/`edge`), `identity`, `properties`, `rows`, `annotations`, `mode`; edge also `source_identity`, `target_identity`; optional `debug_name`, `python_ref`, `semantics`; edge optional `source_node`, `target_node`. `properties` is an object; `python_ref` is `{module, qualname, signature}`. |
| Asset (`assets[]`) | `name`, `website`, `version`, `layout`, `profile`, `governance`, `annotations`; optional `semantics`. Profile `{subject, coverage, authority, basis, title?, description?}`; governance `{license, owner, metadata}`. |
| Expression | `kind` (`literal`/`variable`/`field`/`lookup`/`operation`), `logical_type`, plus kind fields: field `{field, path}`, lookup `{relation, target_field, key}`, operation `{operator, arguments, parameters}`. |
| Semantics attachment | optional `claims`, optional `frames`; no purpose. |

### 6.3 Omitted vs. explicit null

| Layer / member | When absent | Evidence |
| --- | --- | --- |
| Blueprint `graph_declaration` | Omitted | `interpreter/service/_private/codec.py` |
| Graph declaration `description` | Omitted | `languages/graph/service/_private/codec.py` |
| Topology `parent`, `description`, `semantics` | Omitted | `languages/topology/service/_private/codec.py` |
| Topology `labels`, `abstract`, `properties`, `annotations` | Always written (`[]`, `false`, `[]`, `[]`) | same |
| Data `description`, `expression`, `semantics` | Omitted | `languages/data/service/_private/codec.py` |
| Data `annotations` | Always written as array | same |
| Data `structs`, `relations`, `projections` | Always written; decoder treats absent as empty | same |
| Binding `debug_name`, `python_ref`, `semantics` | Omitted | `languages/binding/service/_private/codec.py` |
| Binding `rows` | **Explicit `null`** | same |
| Binding `identity`, `properties`, `annotations`, `mode` | Always written | same |
| Binding edge `source_node`, `target_node` | Omitted | same |
| Asset `website`, `version`, `layout`, `governance.license`, `governance.owner`, `profile.title`, `profile.description` | **Explicit `null`** | `languages/asset/service/_private/codec.py` |
| Asset `semantics` | Omitted | same |
| Semantics `claims`, `frames`, `limitations` | Omitted when empty | `languages/semantics/service/_private/codec.py` |
| Graph semantics `purpose` | Always written; decoder requires it | same |
| Expression `parameters` / `path` | Decoder defaults to `{}` / `[]`; encoder always writes them | `languages/expressions/service/_private/dto_codec.py` |

`specs/semantics-and-graph.md` says "canonical, omit an absent optional member"
and "Codecs omit `None`." That is not true for asset nullable fields or binding
`rows`, which are explicitly null. Round-trip works because decoders accept both
styles.

### 6.4 Decoder leniency and examples

- Legacy fallbacks: `"binding"` -> `"bindings"`; asset input may be an array or
  `{"assets": [...]}`; if asset `"profile"` is absent, profile is read from
  legacy `"semantics"` and the asset semantics attachment is dropped.
- Topology/data default absent arrays to `()`; topology `abstract` defaults
  `False`; data `union.all` has no default and fails if absent. Graph
  declarations require `"semantics"`; expressions require `logical_type`, and
  operations require an `arguments` array and an operation ref.
- Binding decoding requires non-empty `mode`; it does not default. The
  `binding_from_document` docstring example (lines 332-342) omits `mode` and
  would raise `ValueError("'mode' must be a non-empty string")`.

### 6.5 Round-trip guarantees

Documented contract (`docs/developer/data-and-expressions.md`):
`GraphBlueprint -> source -> create_blueprint -> equivalent GraphBlueprint`,
where "equivalent" means the same semantic model, not the same text.

Verified by tests:

- `tests/distribution/test_graph_blueprint.py`: empty and graph-declaration
  blueprints round-trip through the codec; graph semantics survive source
  round-trip.
- `tests/distribution/test_blueprint_source.py`: a fixture with asset, table
  and binding round-trips through rendered source to the same canonical JSON
  document.

Guaranteed: a JSON-compatible document with the documented top-level members;
`blueprint_from_document(blueprint_to_document(bp))` reconstructs an equal
blueprint for tested fixtures; source round-trip reconstructs the same
canonical document for those fixtures.

Not guaranteed: original text, declaration class names, module layout, or
callable bodies; blueprint validity after decoding (no validation call); a
total order across all layers (the linker uses discovery/closure order and only
some renderers sort); symmetric omit/null style; round-trip of legacy
asset-`semantics`-as-profile documents (the semantics attachment is lost).

## 7. Source rendering

### 7.1 `blueprint_to_source` order

`interpreter/service/_private/source.py`:

1. `GraphLanguage().render(blueprint.graph_declaration, context)` when present.
2. `AssetLanguage().render(blueprint.assets, context)`.
3. `TopologyLanguage().render(blueprint.graph, context)`.
4. `DataLanguage().render(blueprint.data, context, class_names=asset_class_names)`.
5. `BindingLanguage().render(blueprint.bindings, context)`.

`asset_class_names` maps each asset name to `class_name(asset.name, "Asset")`.
`_assemble` collects `fragment.imports`, normalizes each to start with `import `
or `from `, sorts them lexicographically, joins with `\n`, strips each body
(extracted via a string or `body`/`text`/`source`/`code` attribute, else
`str(fragment)`), drops empty bodies, joins parts with `\n\n`, and appends a
final newline if anything was produced. The docstring calls this the "inverse
of `create_blueprint`"; it is dependency-friendly, not the literal reverse of
`ORDER`.

### 7.2 Per-language renderers

| Language | Renderer | Ordering / behavior |
| --- | --- | --- |
| Graph | `render_graph_declaration_source` (`languages/graph/service/_private/source.py`) | One `class <Name>Graph(Graph)` with `GraphOptions(name=..., description?, semantics=...)`. |
| Asset | `render_asset_source` (`languages/asset/service/_private/source.py`) | Assets sorted by name; `class <Name>Asset(Asset)` with `AssetOptions(profile=..., semantics?, name=..., website?, version?, layout?, governance?, annotations?)`; default governance omitted. |
| Topology | `render_graph_source` (`languages/topology/service/_private/source.py`) | Nodes then edges; each group sorted by `(depth, name)`, parent classes before children; `Node`/`Edge` or `AbstractNode`/`AbstractEdge`; `NodeOptions`/`EdgeOptions` always names the graph name; labels become `NodeLabel`/`EdgeLabel`; properties/annotations/semantics rendered. |
| Data | `render_data` (`languages/data/service/_private/source.py`) | Structs, relations, projections in DTO tuple order. Struct -> `Struct` + `StructOptions`; relation -> `Table[<AssetClass>]` + `TableOptions`; projection -> `Projection(<row-source expression>)` + `ProjectionOptions`. Row plans render as method chains; column expressions use `computed_field` for projections and `Field[...] = field(...)` otherwise. |
| Binding | `render_binding_source` (`languages/binding/service/_private/source.py`) | Bindings in blueprint order; variable `<member_name(component)>_binding`, duplicate bases `_<index>`. Declarative vs. Python mode; `node_binding`/`edge_binding`; optional `options=BindingOptions(annotations=...)`, endpoint, `debug_name`, semantics. |
| Expressions | `render_expression_source` (`languages/expressions/service/_private/source.py`) | Not called directly by `blueprint_to_source`; data/binding renderers call it for inline expressions. |

### 7.3 Caveats

- `blueprint_to_source` hard-codes fresh default language instances; it has no
  `languages` parameter, so a custom language/renderer cannot participate.
- `context` is passed through but current renderers mostly ignore it; imports
  are sorted globally, not per fragment.
- `_fragment_text` can fall back to `str(fragment)`, and data/binding scans fall
  back to `class_name(name, "Table")`; a custom name or unrecognized fragment
  may not round-trip.

## 8. Assembly, validation, asset tables, and the engine boundary

### 8.1 Assembly

`assemble_blueprint(graph, data, assets, bindings, graph_declaration=None)` is a
pure structural constructor: `bindings` becomes a tuple and `graph_declaration`
passes through unchanged. It introduces no authoring path, declaration object or
symbol table, and does **not** validate. Only `link_blueprint` calls
`validate_blueprint` after assembly.

### 8.2 Validation checks

`validate_blueprint(blueprint) -> None`:

| Check | Enforced | Error |
| --- | --- | --- |
| Graph declaration | `GraphDeclarationDTO`; `GraphSemanticsDTO`; `PurposeDTO`; non-empty purpose text. | `ValueError("the graph declaration must be a GraphDeclarationDTO")`, `"...requires GraphSemantics semantics"`, `"...requires a purpose"`, `"...purpose must be non-empty"` |
| Component names | Node+edge names unique (or `graph.components` fallback). | `ValueError("component names must be unique")` |
| Properties | `prop.ref == PropertyRef("topology", Key((f"{component}.{prop}",)))`. | `ValueError("component <name> property <prop> does not carry <expected>")` |
| Edge endpoints | Source/target in node refs. | `ValueError("edge <name> has an unknown endpoint <endpoint>")` |
| Parents | Node parent in node refs; edge parent in edge refs. | `ValueError("component <name> has an unknown parent <parent>")` |
| Asset names | Unique. | `ValueError("asset names must be unique")` |
| Relation asset | Relation names an asset that exists. | `ValueError("relation <name> must name its logical asset")`, `"...names an unknown asset <asset>"` |
| Relation/projection columns | `column.ref == FieldRef("data", Key((f"{owner}.{column}",)))`. | `ValueError("<relation/projection> <name> column <col> does not carry <expected>")` |
| Binding target | Target ref in known components. | `ValueError("binding targets an unknown component <component>")` |
| Node/edge binding target | Node target is node; edge target is edge. | `ValueError("node binding targets an unknown node <component>")`, `"edge binding targets an unknown edge <component>"` |
| Edge binding endpoints | Optional source/target nodes exist. | `ValueError("edge binding targets an unknown endpoint <endpoint>")` |

Not checked: struct columns (only relations/projections are iterated);
duplicate relation/projection names in a manually built blueprint; binding
expression refs beyond target/endpoints; duplicate binding identities in a
manually assembled blueprint. `_components` falls back to `graph.components` and
`_relations` falls back to `data.tables`; neither attribute exists on current
DTOs (dead defensive code).

### 8.3 Asset-table planning

`asset_tables(blueprint) -> tuple[AssetTable, ...]`,
`table_relations(blueprint) -> Mapping[str, str]` (`MappingProxyType`).
`_read_relations` scans `blueprint.bindings` (identity, edge source/target
identity, property expressions, row plan) and `blueprint.data.projections`
(column expressions, `row_source`). Expression discovery: `FieldReferenceDTO`
-> `field.relation`; `LookupExpressionDTO` -> `relation.name`. Plan discovery:
scan sources, plan expressions, recursive inputs. The names are intersected with
`blueprint.data.relations`, sorted by relation name, and assigned
`relation=f"kg_table_{index}"`, `relation_name=relation.name`,
`asset=AssetDescriptor`, `AssetColumn(name, type_from_dto(logical_type))`.
`table_relations` maps `relation_name -> kg_table_n`.

Consequences: an unread relation is omitted even if it is in the blueprint
(possible with default roots); numbering follows lexicographic relation order.
`_asset_for` re-checks the relation's asset and raises `ValueError("relation
<name> must name its logical asset")` or `"...names an unknown asset <asset>"`.
Consumers: `modules/core/.../planning/plan.py` builds `CorePlan.table_relations`;
`modules/duckdb/service/_private/planner.py` emits `source_relation` steps.

### 8.4 Neutral relation plan

`service/internal/emission.py`:

```python
class Scan: source: str; relation: str; alias: str
class Expand: scope: tuple[str, ...]; expression: ExpressionDTO; alias: str
class Filter: expression: ExpressionDTO; mode: Literal["present", "true"] = "present"
class RelationPlan: scans; expands; filters; outputs; relations; shapes
```

The plan carries expression DTOs and logical relation names; no SQL text or
engine object. `relations`/`shapes` resolve named relations an inline lookup
reads without making them scans of this product.

`ArraySqlType(item)` and `StructSqlType(members)` compose `SqlType`; a
`CanonicalTypeName` is a unit name.

`CANONICAL_SQL_TYPES` maps `bool/int/float/str/date/time/timestamp/uuid` to
`BOOLEAN/BIGINT/DOUBLE/VARCHAR/DATE/TIME/TIMESTAMP/UUID`.
`canonical_sql_type` composes `Array[int] -> BIGINT[]` and
`Struct{a: int} -> STRUCT(a BIGINT)`; it raises for an empty struct and for a
bare non-unit canonical name. `NULL_GUARD_MACRO = "_kg_nn"`; `sql_identifier`
quotes only when needed.

### 8.5 Emitter protocols consumed by core

```python
class RelationSqlEmitter(Protocol):
    def relation_sql(self, plan: RelationPlan) -> str: ...
    def emit_row_source(self, plan: RowSourcePlanDTO, relations, shapes) -> str: ...
class SqlEmitter(Protocol):
    kind: InstructionKind
    instruction_emitter: RelationSqlEmitter
    def emit(self, plan: RelationPlan, context: Any = None) -> Instruction: ...
```

Core uses `emit` for relational products (`product_sql` extracts and requires a
non-empty `payload["sql"]`) and `instruction_emitter.emit_row_source` for
row-source plans. `plan_product` raises for no outputs, a missing materialized
relation, or more than one driving field source ("additional sources must be
introduced by an explicit lookup"). Row effects are derived from operation specs
(`expand` -> `Expand`; `drop_null`/`drop_if`/filter operations -> `Filter`) and
deduped by canonical expression document.

DuckDB: `DuckDbSqlEmitter` is a frozen dataclass with
`kind = InstructionKind("sql", "duckdb")` and a `DuckDbInstructionEmitter`;
`emit` renders `relation_sql(plan)` to `{"sql": sql}` and adds
`{"relation": context.relation}` when present. Core imports only
`service/internal/emission.py`, never the DuckDB module.

### 8.6 `RelationService` protocol

```python
class RelationService(Protocol):
    def reference(self, value: object) -> str: ...
    def view(self, name: str, query: str) -> RelationRef: ...
    def materialize(self, name: str, query: str, parameters=()) -> RelationRef: ...
    def query(self, query: str, parameters=()) -> RelationQueryResult: ...
    def export_parquet(self, query: str, destination: Path,
                       *, compression: str = "zstd") -> None: ...
    def register_filesystem(self, filesystem: object) -> None: ...
```

`service/_private/execution.py` gets it via `resources.get(RelationService)` and
wraps `reference`, `query`, `export_parquet`; it also provides `output_path`
(via `OutputStorage.child(PurePosixPath(...))`), `input_values` (normalizes
`None`/tuple/list/scalar) and `artifact_of` (reads `.artifact`). DuckDB's
`DuckDBRelationService` implements the protocol.

## 9. Invariants and error conditions

### 9.1 Linker and blueprint

| Invariant | Where | Failure |
| --- | --- | --- |
| `namespace_path` XOR non-empty `bindings` | `interpreter/service/_private/create.py` | `ValueError("namespace_path cannot be combined with bindings")` |
| Required languages present (`expressions`, `asset`, `data`, `topology`, `binding`) | `interpreter/service/_private/link.py` | `ValueError("the graph linker requires languages ...")` |
| Unique language names | same | `ValueError(f"duplicate language name {name!r}")` |
| Roots are supplied languages | same | `ValueError("unknown root language(s): ...")`; non-`ORDER` supplied names silently ignored |
| Unique declaration keys per language | same | `ValueError(f"language {name!r} declares key {key!s} twice")` |
| Transcribed key equals indexed key | same | `ValueError(f"language {name!r} transcribed {reference.key!s} as {symbol.key!s}")` |
| Every reference names an indexed symbol | same | `ValueError(f"unknown symbol reference {reference}")` |
| Reference graph acyclic | same | `ValueError(f"symbol reference cycle at {reference}")` |
| At most one graph declaration | same | `ValueError("the blueprint carries more than one graph declaration")` |
| At most one `Graph` at discovery | `languages/graph/service/internal/adapters/kernel_language.py` | `ValueError("a namespace may declare at most one Graph; found ...")` |
| Only reachable declarations transcribed | `interpreter/service/_private/link.py` | unreachable declarations silently absent |
| Read-only, dependency-first `SymbolContext` | `kernel/model/public/symbol.py` + linker | `KeyError(f"unknown symbol {reference}")` |
| Data relation names an asset | data transcription / validation | `ValueError("relation <name> has no logical asset")`, `"...must name its logical asset"` |
| Projection has a row source | data transcription | `ValueError("projections require a row source")` |
| Topology parent is abstract and acyclic | topology transcription / `validate_graph_part` | parent-chain `ValueError`s |
| Edge declares both endpoints | topology transcription | `ValueError("edge <name> does not declare both endpoints")` |
| Binding rows read known data sources | binding transcription | `ValueError("binding reads unknown logical source(s): ...")` |
| Binding mode is `declarative`/`python` | binding `validate_bindings` | `ValueError("unknown binding mode ...")` |
| Binding identities unique | binding `validate_bindings` | `ValueError("binding <component> has a duplicate identity")` |
| Asset names unique | `AssetPartDTO.__post_init__` / validation | `ValueError("asset names must be unique")` |
| Topology component names unique | `GraphPartDTO.__post_init__` / validation | `ValueError("topology component names must be unique")` / `"component names must be unique"` |

### 9.2 Codec and engine boundary

| Invariant | Where |
| --- | --- |
| Keys are arrays of strings | `kernel/model/public/key.py::from_document` (`ValueError` for non-array/non-string) |
| Ref documents are `[language, role, *segments]`; role optional on decode | `distribution/model/public/refs.py` |
| Graph declaration requires `semantics`; graph semantics requires `purpose` | graph/semantics codecs |
| Row plan `kind` is one of eight; join `how` is `inner/left/right/full` | data/binding codecs |
| Binding `kind` is `node`/`edge`; `mode` non-empty | binding codec |
| Ref type matches field role | all layer codecs |
| Expression `kind` is one of five; operation parameters object | expression codec |
| Asset authority is a known `AssetAuthority` | asset codec (`ValueError("unknown asset authority ...")`) |
| A relational product has ≥1 output and ≤1 driving field source | `modules/core/.../planning/emission.py::plan_product` |
| Referenced source has a materialized relation name | same |
| `canonical_sql_type` refuses empty struct/bare container | `service/internal/emission.py` |
| SQL emit returns object payload with non-empty SQL | `modules/core/.../emission.py::product_sql` |
| `asset_tables` returns only relations actually read | `service/_private/asset_tables.py` |

## 10. Surprising, ambiguous, and doc/code disagreement points
1. **`BlueprintLinker`'s docstring order is wrong.** It says `expressions`,
   `data`, `topology`, `binding`
   (`interpreter/service/internal/adapters/kernel_linker.py`, lines 16-18).
   `ORDER` is `expressions, asset, data, topology, binding, graph`
   (`interpreter/service/_private/link.py`, line 42). `link.py`'s module
   docstring and `docs/developer/data-and-expressions.md` include `asset` and
   `graph`.
2. **`docs/developer/system-design.md` also omits `graph`** from the sentence
   "The distribution's `BlueprintLinker` indexes languages in the fixed order
   `expressions`, `asset`, `data`, `topology`, `binding`". Code and
   `specs/semantics-and-graph.md` include it.
3. **Docs say `GraphBlueprint` has four fields; code has five.**
   `docs/concepts/build-and-outputs.md` and `docs/reference/compile.md` list
   only `graph`, `data`, `assets`, `bindings`. Code adds
   `graph_declaration: GraphDeclarationDTO | None = None`, as documented in
   `docs/developer/data-and-expressions.md` and the spec.
4. **`_LanguageResolver` is dormant.** It is constructed and passed to every
   `get_references`, but every language discards it. `get_identity` is not
   called on the normal link path, so the multi-claim identity check never runs
   during `create_blueprint`.
5. **All declarations are indexed, including unreachable ones.** A duplicate
   key in an orphan declaration fails the link before roots are applied.
6. **Roots can be silently ignored.** `unknown_roots` is checked against
   `by_name`, not the ORDER-filtered `available`; a supplied language outside
   `ORDER` is accepted as a root but never indexed.
7. **`order_symbols` runs twice.** `link_blueprint` orders reachable refs, then
   `_assemble` calls `order_symbols(symbols)` again. The second pass is the one
   that produces `Symbol`-level unknown/cycle errors.
8. **The linker overwrites `Symbol.references`.** Only `get_references`
   determines ordering and the final references; the `references` returned by
   `transcribe` is advisory.
9. **`get_kind` is unused by the linker.** `BlueprintLinker` uses the `kind` on
   the returned `Symbol`; a language could return a symbol whose `kind` differs
   from `get_kind` without the linker noticing.
10. **`DataLanguage` keying is stateful.** `_name_counts` is assigned during
    `discover_declarations`; `compute_key`/`get_identity` depend on the most
    recent batch. Reusing one instance across namespaces, or calling before
    discovery, can change a repeated struct's key. The class-level mutable `{}`
    is shadowed per instance.
11. **Binding order differs from the batch helper.** `transcribe_bindings`
    sorts by target/component/document, but the linker calls
    `symbol_for_declaration` per binding. `GraphBlueprint.bindings` follows
    discovery/closure order; the "sorted by target" docstring applies to the
    batch helper, not the blueprint path.
12. **Binding identity includes `mode`/`rows`, excludes `python_ref`.** The
    digest pops `debug_name` and `python_ref`; the final key prefixes
    `debug_name`, so adding a debug name changes the key. Changing a Python
    reference does not change the digest.
13. **Validation skips struct columns and most binding expressions.** Only
    relation/projection columns are checked; struct column refs are built with
    `field_key(owner_key(...), name)` and, for qualified structs, would not
    match `_field_ref(owner.name, column.name)`. Binding `identity`,
    `source_identity`, `target_identity`, property expressions and row-plan
    refs are not validated by `validate_blueprint`.
14. **`assemble_blueprint` and `blueprint_from_document` do not validate.** Only
    `link_blueprint` calls `validate_blueprint`; a manually assembled or decoded
    blueprint can be invalid until separately checked.
15. **Dead defensive branches in validation.** `_components` falls back to
    `graph.components`; `_relations` falls back to `data.tables`. Neither
    attribute exists on current DTOs; unclear legacy remnants.
16. **Omit/null style is inconsistent.** Asset nullable fields and binding
    `rows` are explicit null; topology/data/graph optional members are omitted.
    The spec's "omit an absent optional member" / "Codecs omit `None`" is only
    partly true.
17. **Legacy decode paths.** `"binding"` is accepted for `"bindings"`; assets
    may be an array or `{"assets": [...]}`; asset `"semantics"` is read as
    profile when `"profile"` is absent, in which case the asset semantics
    attachment is dropped.
18. **A codec example is not runnable.** `binding_from_document`'s example
    document omits `"mode"`, but the decoder requires a non-empty mode.
19. **`blueprint_to_source` ignores the languages that built the blueprint.**
    It hard-codes `GraphLanguage`, `AssetLanguage`, `TopologyLanguage`,
    `DataLanguage`, `BindingLanguage`; there is no `languages` parameter and no
    custom renderer path.
20. **"Inverse of `create_blueprint`" is imprecise.** Source order is graph,
    asset, topology, data, binding; linker indexing order is expressions,
    asset, data, topology, binding, graph. It is dependency-friendly, not a
    literal reverse. Ordering is layer-dependent: assets sort by name,
    topology by depth/name, data by DTO tuple order, bindings by blueprint order.
21. **Explicit bindings and path discovery expand assets differently.**
    `_Namespace.values()` calls `_with_assets`, resolving table declarations
    implied by binding expressions and adding their assets.
    `_ModuleNamespace.values()` does not call `_with_assets`; it relies on
    imported module values. A binding passed explicitly may pull in more
    declarations than the same binding discovered from a path.
22. **`namespace_modules` mutates `sys.path` and populates `sys.modules`.** It
    inserts `root.parent`, imports sorted names, removes the path, but does not
    purge imported modules. It treats the directory name as a top-level package,
    so a nested package can shadow or be shadowed by an installed module of the
    same name; nested-package behavior is unclear.
23. **`_table_declarations` is heuristic.** It finds concrete `Table`
    subclasses whose `_kg_declaration_spec.name` matches a relation read by a
    binding expression and whose fields include the read fields; it prefers
    candidates whose `__module__` matches a binding target's module, otherwise
    returns all candidates. Same-named tables in different modules can be
    ambiguous.
24. **Distribution `create_blueprint()` with no arguments returns an empty
    blueprint.** It builds `_Namespace(())`. The author docs' "calling file's
    directory" behavior lives in `kg_build_system/api.py`
    (`_calling_namespace_path`), which delegates here; do not attribute it to
    the interpreter service.
25. **Docs default-language lists omit `graph`.** `docs/reference/compile.md`
    says "expressions, asset, data, topology and binding";
    `_default_languages()` in `interpreter/service/_private/create.py` appends
    `GraphLanguage()`, and `specs/semantics-and-graph.md` says it does.
26. **Documentation/map hygiene.** `ARCHITECTURE.md` and
    `docs/developer/system-design.md` do not list every service file (for
    example `asset_tables.py`; `ARCHITECTURE.md` also omits `emission.py`).
    `GraphPartDTO`/`AssetPartDTO`
    already reject duplicate names, so parts of `validate_blueprint` are
    redundant. `canonical_sql_type` refuses a bare
    `ARRAY_CANONICAL`/`STRUCT_CANONICAL`; the doc's exact
    `distribution/model/internal/canonical_types.py` path is not confirmed by
    the import (code imports from the `distribution/model/internal` facade);
    mark that path unclear.

## 11. Signatures

```python
# interpreter/public
create_blueprint(*, namespace_path: str | Path | None = None,
                 bindings: Iterable[Any] = (), languages: Sequence[Any] | None = None) -> GraphBlueprint
# interpreter/internal
class BlueprintLinker: __init__(*, roots: Sequence[str] | None = None); link(languages, namespace) -> GraphBlueprint
assemble_blueprint(graph, data, assets, bindings, graph_declaration=None) -> GraphBlueprint
validate_blueprint(blueprint) -> None
blueprint_to_document(blueprint) -> dict[str, Any]
blueprint_from_document(value) -> GraphBlueprint
blueprint_to_source(blueprint, context) -> str
# interpreter/private
ORDER = ("expressions", "asset", "data", "topology", "binding", "graph")
order_symbols(symbols) -> tuple[SymbolRef, ...]
link_blueprint(languages, namespace, *, roots=None) -> GraphBlueprint
# distribution service/public
create_blueprint(...) -> GraphBlueprint
asset_tables(blueprint) -> tuple[AssetTable, ...]
table_relations(blueprint) -> Mapping[str, str]
# distribution service/internal/emission
class Scan: source; relation; alias
class Expand: scope; expression; alias
class Filter: expression; mode = "present"
class RelationPlan: scans; expands; filters; outputs; relations; shapes
class RelationSqlEmitter(Protocol): relation_sql(plan); emit_row_source(plan, relations, shapes)
class SqlEmitter(Protocol): kind; instruction_emitter; emit(plan, context=None)
canonical_sql_type(canonical) -> str
sql_identifier(value) -> str
# distribution service/internal/relations
class RelationService(Protocol):
    reference(value); view(name, query); materialize(name, query, parameters=())
    query(query, parameters=()); export_parquet(query, destination, *, compression="zstd")
    register_filesystem(filesystem)
```

### 11.1 Tests covering this area

`test_blueprint_linker.py` (required languages, order, duplicate keys, missing
refs, cycles, root closure, default roots), `test_blueprint_source.py`
(blueprint-source-blueprint canonical document), `test_graph_blueprint.py`
(graph declaration/codec/source/validation), `test_blueprint_dto.py` (no
`symbol_id`, refs, field types), `test_core_custom_emitter.py` (custom
`SqlEmitter`), `test_duckdb_source_planner.py` (`asset_tables`), and
`test_expression_operations.py` (`RelationPlan`/SQL).

*End of survey.*
