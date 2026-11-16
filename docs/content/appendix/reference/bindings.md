---
title: Bindings reference
summary: Exact node_binding and edge_binding signatures, forms, key and property rules, endpoint tokens and errors.
section: reference
perspective: reference
order: 130
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/binding/service/public/builders.py
  - kg_build_system/distribution/languages/binding/service/_private/factories.py
  - kg_build_system/distribution/languages/binding/model/public/values.py
  - kg_build_system/distribution/languages/binding/service/_private/symbols.py
  - docs/content/appendix/reference/bindings.md
---

## Surface

`node_binding` and `edge_binding` connect one row source to one concrete component, assign a present key and every declared property, and state the fulfilment between the relation and the record.

| Surface | Return | Form |
| --- | --- | --- |
| `node_binding(...)` | `NodeBinding[N]` | Direct `build_key` + `properties`, or `rows` + `bind`. |
| `edge_binding(...)` | `EdgeBinding[E]` | Direct three keys + `properties`, or `rows` + `bind`. |
| `NodeValues(build_key, properties)` | Row-derived node values | Returned by a node `bind` callable. |
| `EdgeValues(build_key, source_build_key, target_build_key, properties)` | Row-derived edge values | Returned by an edge `bind` callable. |
| `BindingOptions(annotations=..., meaning=...)` | Frozen options value | Portable metadata and the fulfilment for one binding. |
| `endpoint(target)` | `Endpoint[N]` | A concrete node token for an abstract edge side. |

Read [Bind records](/book/part-2/08-binding) for the authoring path, [Binding specification](/appendix/spec/binding) for the requirement and [Bindings subject](/appendix/subjects/binding) for the views.

## Details

A binding is the only place data shape and graph meaning meet. The declaration stays in [Topology reference](/appendix/reference/topology); the rows come from a source relation or derived relation. See [Declare topology](/book/part-2/02-topology) for the declaration model and [Declare meaning](/book/part-2/01-meaning-and-purpose) for the meaning fragment. A stage is not a published relation and is never bindable.

```python
from kg_build_system import (
    Claim, Contract, Definition, Edge, Field, Meaning, Node, Omitted,
    PropertySlot, SourceRelation, SourceRelationOptions, field, property,
)

from estate.assets import Estate

class EquipmentSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        contract=Contract(
            definition=Definition(
                grain="one row per registered unit",
                identity=("unit_ref",),
            ),
            meaning=Meaning(
                claims=(Claim("One row names one equipment unit."),),
            ),
        ),
    )
    site_id: Field[str] = field(meaning=Omitted)
    unit_ref: Field[str] = field(meaning=Omitted)
    unit_name: Field[str] = field(meaning=Omitted)
    in_service: Field[bool] = field(meaning=Omitted)

class SiteNode(Node):
    name: PropertySlot[str] = property(meaning=Omitted)

class UnitNode(Node):
    name: PropertySlot[str] = property(meaning=Omitted)
    in_service: PropertySlot[bool] = property(meaning=Omitted)

class HasUnitEdge(Edge[SiteNode, UnitNode]):
    as_at: PropertySlot[str] = property(meaning=Omitted)
```

A binding states the fulfilment in its own meaning. The examples use these two:

```python
from kg_build_system import Meaning, Purpose

unit_fulfilment = Meaning(
    purpose=Purpose(
        "Populate each unit record from the estate register.",
        limitations=(
            "A unit the register omits is not emitted.",
        ),
    ),
)

has_unit_fulfilment = Meaning(
    purpose=Purpose(
        "Connect each site to the units the register assigns to it.",
    ),
)
```

### Fulfilment

A binding is not a field map. It is the claim that one relation is sufficient for one record, with the shortfall stated. The claim has four checks:

| Check | Question | If it fails |
| --- | --- | --- |
| Grain | Does one relation row mean one record? | Split the relation or change the record; do not repair it in the binding. |
| Identity | Does the relation carry the record's build key and, for an edge, both endpoints? | The key is a limitation or the relation is wrong. |
| Coverage | Does the relation's row scope state every record the purpose claims? | State the gap as a `Limitation` under the binding purpose. |
| Meaning | Does the relation's `Meaning` fit the record's meaning? | Use another relation. |

The binding states the answer in its own `Meaning`. Its purpose MUST say which relation satisfies which record purpose, at which grain, identity and coverage, and where it falls short. A binding without a purpose is refused; a mapping recipe is not a fulfilment.

A binding may be simple when the relation already has the record's grain. It must not be vacuous: if the relation already chose the record's key, properties and endpoints, the design happened on the relation side and the binding is a copy. A published relation is record-agnostic; the binding is the only place that knows both sides.

### Signatures

```python
node_binding(
    *,
    target: type[N],
    build_key: Selection[NonNullableGraphValue] | None = None,
    properties: N | None = None,
    rows: RelationRowSource[S] | DerivedRowSource[S] | None = None,
    bind: Callable[[S], NodeValues[N, NonNullableGraphValue]] | None = None,
    name: str | None = None,
    options: BindingOptions | None = None,
    meaning: Meaning | None = None,
) -> NodeBinding[N]

edge_binding(
    *,
    target: type[E],
    build_key: Selection[NonNullableGraphValue] | None = None,
    source_build_key: Selection[NonNullableGraphValue] | None = None,
    target_build_key: Selection[NonNullableGraphValue] | None = None,
    properties: E | None = None,
    rows: RelationRowSource[S] | DerivedRowSource[S] | None = None,
    bind: Callable[[S], EdgeValues[E, NonNullableGraphValue, NonNullableGraphValue, NonNullableGraphValue]] | None = None,
    name: str | None = None,
    options: BindingOptions | None = None,
    meaning: Meaning | None = None,
    source_node: Endpoint[NodeSideBase] | None = None,
    target_node: Endpoint[NodeSideBase] | None = None,
) -> EdgeBinding[E]
```

| Argument | Meaning |
| --- | --- |
| `target` | A concrete `Node` or `Edge` class; categories and templates are refused |
| `rows` | A published row-source value: `SourceRelation.row_source()` or `DerivedRelation.row_source()`, or a derived value. A `StageRowSource` is refused. |
| `bind` | A callable receiving a typed row proxy and returning `NodeValues` or `EdgeValues` |
| `build_key` | The present scalar selection identifying one node or edge record |
| `properties` | An instance of the target with one selection per declared property |
| `source_build_key` / `target_build_key` | Edge only: the build keys of the source and target nodes |
| `source_node` / `target_node` | Edge only: `endpoint(...)` tokens naming concrete endpoint components |
| `name` | Optional human handle carried into the meta-graph and binding identity |
| `options` | `BindingOptions(annotations=..., meaning=...)` |
| `meaning` | The fulfilment, with a required `Purpose`; pass it here or in `options`, not both |

The two forms are exclusive:

| Form | Arguments | Row values |
| --- | --- | --- |
| Direct | `build_key` + `properties`; edges also add the two endpoint keys | Selections written against a declaration |
| `rows=` / `bind=` | `rows` + `bind` | Values returned from the callable for the supplied row proxy |

Supplying both forms, or half of either, is refused.

Both factories return a frozen binding value:

| Return | Meaning |
| --- | --- |
| `NodeBinding[N]` | The target, key, properties, optional `name`, annotations, row-source value and meaning |
| `EdgeBinding[E]` | The same, plus both endpoint keys and resolved endpoint components |

`compile` accepts the returned values directly. See [Compile](/appendix/reference/compile).

### Direct form

A node binding assigns the key and every declared property directly:

```python
from kg_build_system import node_binding

unit_binding = node_binding(
    target=UnitNode,
    build_key=EquipmentSourceRelation.unit_ref.alter_rows().drop_null(),
    properties=UnitNode(
        name=EquipmentSourceRelation.unit_name.default_to("Unnamed unit"),
        in_service=EquipmentSourceRelation.in_service.alter_rows().drop_null(),
    ),
    meaning=unit_fulfilment,
)
```

An edge binding adds the two endpoint keys:

```python
from kg_build_system import edge_binding, endpoint

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    build_key=EquipmentSourceRelation.unit_ref.alter_rows().drop_null(),
    source_build_key=EquipmentSourceRelation.site_id.alter_rows().drop_null(),
    target_build_key=EquipmentSourceRelation.unit_ref.alter_rows().drop_null(),
    properties=HasUnitEdge(
        as_at=EquipmentSourceRelation.unit_name.default_to("Unnamed unit"),
    ),
    source_node=endpoint(SiteNode),
    target_node=endpoint(UnitNode),
    meaning=has_unit_fulfilment,
)
```

The direct form still evaluates per row: a class-level selection is a symbolic reference to the field, not a constant.

### `rows=` / `bind=` form

The callable receives a typed row proxy, not data and not a dictionary. Access fields as selections and return the matching values object.

```python
from kg_build_system import NodeValues, node_binding

unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.alter_rows().drop_null(),
        ),
    ),
    meaning=unit_fulfilment,
)
```

```python
from kg_build_system import EdgeValues, edge_binding

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(
            as_at=row.unit_name.default_to("Unnamed unit"),
        ),
    ),
    meaning=has_unit_fulfilment,
)
```

| Value | Fields |
| --- | --- |
| `NodeValues(build_key, properties)` | The node key and the component instance |
| `EdgeValues(build_key, source_build_key, target_build_key, properties)` | The edge key, the two endpoint keys and the component instance |

`rows` accepts a published row-source value, never a `SourceRelation` or `DerivedRelation` class and never a `StageRowSource`. A filter belongs in the row source:

```python
active_units = EquipmentSourceRelation.row_source().where(
    lambda row: row.unit_name.alter_rows().drop_null().equals("Pump")
)

active_unit_binding = node_binding(
    target=UnitNode,
    rows=active_units,
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.alter_rows().drop_null(),
        ),
    ),
    meaning=unit_fulfilment,
)
```

### Keys

The build key is graph identity. A node key identifies one node within its component; an edge key identifies one relationship record. An edge binding also supplies `source_build_key` and `target_build_key`, which name the endpoint nodes by their build keys.

Every key follows the same rule:

| Rule | Result |
| --- | --- |
| A present `Selection[T]` of a scalar | Accepted |
| A nullable selection | Refused |
| An array or struct selection | Refused |
| A Python literal | Refused; wrap it in `value_expression(...)` |
| A source field read | Narrow with `alter_rows().drop_null()`, or deliberately use `default_to(...)` |

Keys may use any scalar type. A key written from a source field needs `alter_rows().drop_null()` because source access is nullable. `default_to()` is legal on a key but gives every missing identifier the same identity; use it only when one shared sentinel is genuinely correct.

Keys may overlap between producers. Two bindings can emit the same key independently; compose a deduplication planner when exact duplicates must disappear. See [Planners and executors](/appendix/reference/planners-and-executors).

### Properties

Assign every declared property exactly once, including inherited properties:

```python
UnitNode(
    name=EquipmentSourceRelation.unit_name.default_to("Unnamed unit"),
    in_service=EquipmentSourceRelation.in_service.alter_rows().drop_null(),
)
```

| Rule | Result |
| --- | --- |
| Every declared property is present | Required |
| A present selection for a nullable property | Accepted |
| A nullable selection for a required property | Refused; narrow or default it |
| A literal value | Refused; use `value_expression(...)` |
| An unknown or extra property | Refused |
| A property declared as `Array[T]` | Requires a present array with non-null items |

A binding never aggregates: one input row produces one record. Reshape rows in a derived relation first. A `group_by` source has already collapsed each key tuple to one row, so a binding over `{by, members}` emits one record per group.

`alter_rows().drop_null()` in any property selection is a row filter for the whole binding, not a per-property mask. Use `default_to(...)` when the row is meaningful without the value.

```python
present_name = EquipmentSourceRelation.unit_name.alter_rows().drop_null()
```

This drops the row when `unit_name` is null, so the property is present and the record disappears entirely. For a descriptive property that may be absent, use `default_to(...)` instead.

### Endpoint tokens

```python
endpoint(target: type[N]) -> Endpoint[N]
```

`source_node` names the declared source side and `target_node` the declared target side.

```python
from kg_build_system import endpoint

source_node=endpoint(SiteNode)
target_node=endpoint(UnitNode)
```

| Declared side | Token |
| --- | --- |
| Concrete node | Optional; supplying it documents the component used |
| Abstract category | Required; the token selects one concrete descendant |

A token must name a concrete node that equals or descends from the declared endpoint. Endpoint identity is the component, not a producer, so two bindings may name different concrete endpoints.

```python
from kg_build_system import (
    AbstractNode, Edge, Meaning, Node, Omitted, PropertySlot, Purpose,
    endpoint, property,
)

class DocumentedAbstractNode(AbstractNode):
    summary: PropertySlot[str] = property(meaning=Omitted)

class PlaceNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property(meaning=Omitted)

class AssetAtPlaceEdge(Edge[DocumentedAbstractNode, DocumentedAbstractNode]):
    pass

asset_at_place = edge_binding(
    target=AssetAtPlaceEdge,
    build_key=EquipmentSourceRelation.site_id.alter_rows().drop_null(),
    source_build_key=EquipmentSourceRelation.site_id.alter_rows().drop_null(),
    target_build_key=EquipmentSourceRelation.unit_ref.alter_rows().drop_null(),
    properties=AssetAtPlaceEdge(),
    source_node=endpoint(PlaceNode),
    target_node=endpoint(PlaceNode),
    meaning=Meaning(
        purpose=Purpose("Place each unit at the site the register records."),
    ),
)
```

### Annotations and debug names

`BindingOptions` carries portable metadata and the fulfilment:

```python
BindingOptions(
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | None = None,
)
```

| Field | Meaning | Default |
| --- | --- | --- |
| `annotations` | Portable metadata attached to the binding | Empty |
| `meaning` | The fulfilment: which relation satisfies which record purpose, at which grain, identity and coverage, and where it falls short | `None`; a purpose is required |

A binding must supply the meaning here or as `meaning=` on the factory. A missing meaning, a meaning without a purpose and two different meanings are refused.

```python
from dataclasses import dataclass
from kg_build_system import Annotation, BindingOptions

@dataclass(frozen=True)
class Tracked(Annotation):
    namespace = "example"
    annotation_id = "tracked"
    stage: str

options = BindingOptions(
    annotations=(Tracked(stage="bound"),),
    meaning=unit_fulfilment,
)
```

`name` is the human handle for a producer. Use it when one component has more than one binding. It appears in the meta-graph's binding entries and prefixes the binding identity; the content digest excludes it. It does not appear in failure messages. See [Annotations reference](/appendix/reference/annotations) for annotation construction and label rules.

Two bindings targeting the same component, from the same row context, with the same values and no distinguishing `name` are the same binding by identity. Compilation reports a duplicate blueprint symbol rather than treating them as two producers.

### Errors

| Condition | Error |
| --- | --- |
| `target` is abstract, a template or the wrong kind | `TypeError: target must be a concrete node component, not <name>` or the matching edge message |
| Direct and `rows=` arguments are mixed | `TypeError: node_binding takes either build_key/properties or rows/bind`; the edge message is `edge_binding takes either key/properties or rows/bind` |
| Only one of `rows` and `bind` is supplied | `TypeError: rows and bind must be supplied together` |
| Neither form is complete | `TypeError: node_binding requires build_key and properties, or rows and bind`; the edge form says `edge_binding requires keys and properties, or rows and bind` |
| `rows` is not a published row source | `TypeError: rows must be a published row source value; use SourceRelation.row_source() or DerivedRelation.row_source()` |
| `rows` is a `StageRowSource` | `TypeError: rows must not read a stage; bind the derived relation that publishes the stage` |
| `bind` returns the wrong values type | `TypeError: node_binding bind must return NodeValues` or `edge_binding bind must return EdgeValues` |
| `properties` is not an instance of the target | `TypeError: properties must be an instance of <Target>` |
| A property is missing | `TypeError: <Target>.<property> must be assigned a value selection or expression` |
| A property is assigned a bare value | `TypeError: <Target>.<property> must be assigned a selection` |
| A property has the wrong logical type | `TypeError: <Target>.<property> expects <type>, but the selection resolves to <type>` |
| An unknown or extra property is supplied | `TypeError: <Target> has no declared property <names>` |
| A key is not a selection | `TypeError: <argument> must be a selection` |
| A key is nullable | `TypeError: <argument> must be non-nullable` |
| A key is an array or struct | `TypeError: <argument> must be scalar` |
| An abstract endpoint has no token | `TypeError: source_node must name the declared endpoint category <Category>: pass endpoint(...) for that side`; the target side names `target_node` |
| A token is a raw class rather than `endpoint(...)` | `TypeError: source_node must be an endpoint(...) token, not the raw value <value>` |
| A token does not name a concrete node | `TypeError: source_node must name a concrete node component, not <name>` |
| A token is not a concrete descendant | `TypeError: source_node <Node> must equal or descend from the declared endpoint category <Category>` |
| No meaning, or a meaning without a purpose | `ValueError: a binding requires a meaning with a purpose` |
| `meaning` is passed twice with different values | `ValueError: pass meaning either to the binding or to BindingOptions, not both` |
| Two bindings have the same identity | `ValueError: blueprint symbol IDs must be unique` |
| The target is abstract at compile | `ValueError: <kind> binding '<id>' may not target abstract component '<name>'` |
| A property map is incomplete or has an extra entry | `ValueError: binding '<id>' must map every declared component property exactly once` |
| A key reaches compilation as nullable or composite | `ValueError: binding '<id>' keys must be non-null scalar selections` |
| A selection names an unknown source or field | `ValueError: ... references unknown field '<name>' on logical source '<source>'` or `references unknown logical source '<name>'` |

### What compilation records

A binding becomes one frozen blueprint entry containing:

- the target component and its node or edge kind;
- the build key, and both endpoint keys for an edge;
- every bound property selection;
- the resolved endpoint components;
- the optional `name`;
- the binding annotations and meaning;
- the row-source plan when `rows=` was used.

The entry's identity is the SHA-256 digest of the canonical binding document with `name` and `python_ref` removed, truncated to 16 hexadecimal characters. The document covers the target, kind, keys, property selections, endpoint components and row-source plan. `name` prefixes the identity string but does not enter the digest. Annotations are carried but do not distinguish otherwise identical bindings.

Binding annotations are part of the blueprint. They do not change the workflow plan. A record written by `FileExecutor` carries `_kg_binding_symbol`, the binding's identity, until a merging step removes it.

Bindings are discovered only as module-level values. A binding created inside a function or stored only in a container is not discovered; re-exported values are deduplicated by object identity. See [Compile](/appendix/reference/compile).

### What to remember

- A binding is a fulfilment, not a field map: state grain, identity, coverage and meaning.
- A binding must supply a `Meaning` with a purpose; a mapping recipe is not a fulfilment.
- A binding reads only a published relation. A `StageRowSource` is never bindable.
- One binding maps one row context to one concrete component.
- Use either the direct form or `rows=`/`bind=`, never both.
- Every key is a present scalar selection; narrow a source field.
- Every declared property, including inherited ones, is assigned exactly once.
- An abstract edge side needs an `endpoint(...)` token.
- `alter_rows().drop_null()` drops the whole row when a nullable value is null; `default_to()` keeps it.
- Use `name` when one component has several producers.

For the relation a binding reads, see [Derived relations](/appendix/reference/derived-relations) and [Declarations](/appendix/reference/declarations). For the declaration the binding targets, see [Topology reference](/appendix/reference/topology). For the step that turns bindings into a plan, see [Compile](/appendix/reference/compile). For the design rationale, see [The binding is the fulfilment](/appendix/philosophy/binding-is-fulfilment).
