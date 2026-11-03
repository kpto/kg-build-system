# Bindings

`node_binding` and `edge_binding` connect one row source to one concrete component and assign a non-null key and every declared property.

A binding is the only place data shape and graph meaning meet. The declaration stays in [Topology](topology.md); the rows come from a table, projection or derived row source. See [Bindings](../concepts/bindings.md) for the model.

```python
from kg_build_system import Edge, Field, Node, PropertySlot, Table, field, property

class EquipmentTable(Table):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()

class SiteNode(Node):
    name: PropertySlot[str] = property()

class UnitNode(Node):
    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()

class HasUnitEdge(Edge[SiteNode, UnitNode]):
    as_at: PropertySlot[str | None] = property()
```

## Signatures

```python
node_binding(
    *,
    target: type[N],
    build_key: ValueInput[Any] | None = None,
    properties: N | None = None,
    rows: RowSource | None = None,
    bind: Callable[[S], NodeValues[N, Any]] | None = None,
    debug_name: str | None = None,
    options: BindingOptions = BindingOptions(),
) -> NodeBinding[N]

edge_binding(
    *,
    target: type[E],
    build_key: ValueInput[Any] | None = None,
    source_build_key: ValueInput[Any] | None = None,
    target_build_key: ValueInput[Any] | None = None,
    properties: E | None = None,
    rows: RowSource | None = None,
    bind: Callable[[S], EdgeValues[E, Any, Any, Any]] | None = None,
    debug_name: str | None = None,
    options: BindingOptions = BindingOptions(),
    source_node: Endpoint[Any] | None = None,
    target_node: Endpoint[Any] | None = None,
) -> EdgeBinding[E]
```

| Argument | Meaning |
| --- | --- |
| `target` | A concrete `Node` or `Edge` class; categories and templates are refused |
| `rows` | A row-source value: `Table.row_source()`, `Projection.row_source()`, or a derived source; a `Table` or `Projection` class is accepted as a compatibility shorthand |
| `bind` | A callable receiving a symbolic shape instance and returning `NodeValues` or `EdgeValues` |
| `build_key` | The non-null scalar expression identifying one node or edge record |
| `properties` | An instance of the target with one expression per declared property |
| `source_build_key` / `target_build_key` | Edge only: the build keys of the source and target nodes |
| `source_node` / `target_node` | Edge only: `endpoint(...)` tokens naming concrete endpoint components |
| `debug_name` | Optional human handle carried into the meta-graph and binding identity |
| `options` | `BindingOptions(annotations=...)` |

The two forms are exclusive:

| Form | Arguments | Row values |
| --- | --- | --- |
| Direct | `build_key` + `properties`; edges also add the two endpoint keys | Selections or expressions written against a declaration |
| `rows=` / `bind=` | `rows` + `bind` | Values returned from the callable for the supplied row shape |

Supplying both forms, or half of either, is refused.

Both factories return a frozen binding value:

| Return | Meaning |
| --- | --- |
| `NodeBinding[N]` | The target, key, properties, optional `debug_name`, annotations and row-source value |
| `EdgeBinding[E]` | The same, plus both endpoint keys and resolved endpoint components |

`compile` accepts the returned values directly. See [Compile](compile.md).

## Direct form

A node binding assigns the key and every declared property directly:

```python
from kg_build_system import node_binding

unit_binding = node_binding(
    target=UnitNode,
    build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    properties=UnitNode(
        name=EquipmentTable.unit_name.default_to("Unnamed unit"),
        in_service=EquipmentTable.in_service.default_to(False),
    ),
)
```

An edge binding adds the two endpoint keys:

```python
from kg_build_system import edge_binding, endpoint

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    source_build_key=EquipmentTable.site_id.alter_rows().drop_null(),
    target_build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    properties=HasUnitEdge(as_at=EquipmentTable.unit_name),
    source_node=endpoint(SiteNode),
    target_node=endpoint(UnitNode),
)
```

The direct form still evaluates per row: a class-level selection is a symbolic reference to the field, not a constant.

## `rows=` / `bind=` form

The callable receives a symbolic shape instance, not data and not a dictionary. Access fields as attributes and return the matching values object.

```python
from kg_build_system import NodeValues, node_binding

unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
        ),
    ),
)
```

```python
from kg_build_system import EdgeValues, edge_binding

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(as_at=row.unit_name),
    ),
)
```

| Value | Fields |
| --- | --- |
| `NodeValues(build_key, properties)` | The node key and the component instance |
| `EdgeValues(build_key, source_build_key, target_build_key, properties)` | The edge key, the two endpoint keys and the component instance |

`rows` accepts a row-source value. It also accepts a `Table` or `Projection`
declaration as a compatibility shorthand and converts it with `row_source()`;
prefer the explicit value. A `Struct` is a shape, not a row source. A filter
belongs in the row source:

```python
active_units = EquipmentTable.row_source().where(
    lambda row: row.unit_name.alter_rows().drop_null().expression.equals("Pump")
)

active_unit_binding = node_binding(
    target=UnitNode,
    rows=active_units,
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
        ),
    ),
)
```

## Keys

The build key is graph identity. A node key identifies one node within its component; an edge key identifies one relationship record. An edge binding also supplies `source_build_key` and `target_build_key`, which name the endpoint nodes by their build keys.

Every key follows the same rule:

| Rule | Result |
| --- | --- |
| A present `ValueSelection` or `ValueExpression` | Accepted |
| A nullable selection or nullable expression | Refused |
| An array or struct expression | Refused |
| A Python literal | Refused; wrap it in `value_expression(...)` |
| A source column declared `Field[T \| None]` | Narrow with `alter_rows().drop_null()`, or deliberately use `default_to(...)` |
| A source column declared `Field[T]` | Accepted directly |

Keys may use any scalar type. A key written from a nullable source column needs
`alter_rows().drop_null()`; a `Field[T]` key is already present. `default_to()` is
legal on a key but gives every missing identifier the same identity; use it only
when one shared sentinel is genuinely correct.

Keys may overlap between producers. Two bindings can emit the same key independently; register a deduplication module when exact duplicates must disappear. See [Modules](modules.md).

## Properties

Assign every declared property exactly once, including inherited properties:

```python
UnitNode(
    name=EquipmentTable.unit_name.default_to("Unnamed unit"),
    in_service=EquipmentTable.in_service.default_to(False),
)
```

| Rule | Result |
| --- | --- |
| Every declared property is present | Required |
| A non-null expression for a nullable property | Accepted |
| A nullable expression for a required property | Accepted for compatibility; narrow or default it to carry the non-null claim |
| A literal value | Refused; use `value_expression(...)` |
| An unknown or extra property | Refused |
| A property declared as `Array[T]` | Requires a present array with non-null items |

A binding never aggregates: one input row produces one record. Reshape rows in a projection first. A `group_by` source has already collapsed each key tuple to one row, so a binding over `{by, members}` emits one record per group.

`alter_rows().drop_null()` in any property expression is a row filter for the whole binding, not a per-property mask. Use `default_to(...)` when the row is meaningful without the value.

```python
present_name = EquipmentTable.unit_name.alter_rows().drop_null()
```

This drops the row when `unit_name` is null, so the property is present and the record disappears entirely. For a descriptive property that may be absent, use `default_to(...)` instead.

## Endpoint tokens

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
    AbstractNode, Edge, Node, PropertySlot, endpoint, property,
)

class DocumentedAbstractNode(AbstractNode):
    summary: PropertySlot[str] = property()

class PlaceNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property()

class AssetAtPlaceEdge(Edge[DocumentedAbstractNode, DocumentedAbstractNode]):
    pass

asset_at_place = edge_binding(
    target=AssetAtPlaceEdge,
    build_key=EquipmentTable.site_id.alter_rows().drop_null(),
    source_build_key=EquipmentTable.site_id.alter_rows().drop_null(),
    target_build_key=EquipmentTable.site_id.alter_rows().drop_null(),
    properties=AssetAtPlaceEdge(),
    source_node=endpoint(PlaceNode),
    target_node=endpoint(PlaceNode),
)
```

## Annotations and debug names

`BindingOptions` carries portable metadata:

```python
BindingOptions(annotations: Sequence[Annotation] = ())
```

| Field | Meaning | Default |
| --- | --- | --- |
| `annotations` | Portable metadata attached to the binding | Empty |

```python
from dataclasses import dataclass
from kg_build_system import Annotation, BindingOptions

@dataclass(frozen=True)
class Tracked(Annotation):
    namespace = "example"
    annotation_id = "tracked"
    stage: str

options = BindingOptions(annotations=(Tracked(stage="bound"),))
```

`debug_name` is the human handle for a producer. Use it when one component has more than one binding. It appears in the meta-graph's binding entries and it distinguishes binding identity; it does not appear in failure messages.

Two bindings targeting the same component, from the same row context, with the same values and no distinguishing `debug_name` are the same binding by identity. Compilation reports a duplicate blueprint symbol rather than treating them as two producers.

## Errors

| Condition | Error |
| --- | --- |
| `target` is abstract, a template or the wrong kind | `TypeError: target must be a concrete node component, not <name>` or the matching edge message |
| Direct and `rows=` arguments are mixed | `TypeError: node_binding takes either build_key/properties or rows/bind`; the edge message names keys and properties |
| Only one of `rows` and `bind` is supplied | `TypeError: rows and bind must be supplied together` |
| Neither form is complete | `TypeError: node_binding requires build_key and properties, or rows and bind`; the edge form says `edge_binding requires keys and properties, or rows and bind` |
| `rows` is not a row source or a `Table`/`Projection` declaration | `TypeError: rows must be a row source value or a Table/Projection declaration; use Table.row_source()` |
| `bind` returns the wrong values type | `TypeError: node_binding bind must return NodeValues` or `edge_binding bind must return EdgeValues` |
| A property is missing | A `TypeError` from the target's constructor, or the compile-time property-map error below |
| A property is assigned a bare value | `TypeError: <Target>.<property> must be assigned a value selection or expression` |
| A property has the wrong logical type | `TypeError: <Target>.<property> expects <type>, but the expression resolves to <type>` |
| A key is not an expression | `TypeError: <argument> must be a value selection or expression` |
| A key is nullable | `TypeError: <argument> must not be nullable` |
| A key is an array or struct | `TypeError: <argument> must be a scalar` |
| An abstract endpoint has no token | `TypeError: source_node must name the declared endpoint category <Category>: pass endpoint(...) for that side`; the target side names `target_node` |
| A token is a raw class rather than `endpoint(...)` | `TypeError: source_node must be an endpoint(...) token, not the raw value <value>` |
| A token is not a concrete descendant | `TypeError: source_node <Node> must equal or descend from the declared endpoint category <Category>` |
| Two bindings have the same identity | `ValueError: blueprint symbol IDs must be unique` |
| The target is abstract at compile | `ValueError: <kind> binding '<id>' may not target abstract component '<name>'` |
| A property map is incomplete or has an extra entry | `ValueError: binding '<id>' must map every declared component property exactly once` |
| A key reaches compilation as nullable or composite | `ValueError: binding '<id>' keys must be non-null scalar expressions` |
| An expression names an unknown source or field | `ValueError: ... references unknown field '<name>' on logical source '<source>'` or `references unknown logical source '<name>'` |

## What compilation records

A binding becomes one frozen blueprint entry containing:

- the target component and its node or edge kind;
- the build key, and both endpoint keys for an edge;
- every bound property expression;
- the resolved endpoint components;
- the optional `debug_name`;
- the binding annotations;
- the row-source plan when `rows=` was used.

The entry's identity is derived from the target, kind, `debug_name`, keys, property expressions, endpoint components and row-source plan. Annotations are carried but do not distinguish otherwise identical bindings.

Binding annotations are part of the blueprint. They do not change the compiled workflow. A record written by `FileModule` carries `_kg_binding_symbol`, the binding's identity, until a merging stage removes it.

Bindings are discovered only as module-level values. A binding created inside a function or stored only in a container is not discovered; re-exported values are deduplicated by object identity. See [Compile](compile.md).

## What to remember

- One binding maps one row context to one concrete component.
- Use either the direct form or `rows=`/`bind=`, never both.
- Every key is a present scalar expression; narrow a nullable source column.
- Every declared property, including inherited ones, is assigned exactly once.
- An abstract edge side needs an `endpoint(...)` token.
- `alter_rows().drop_null()` drops the whole row when a nullable value is null;
  `default_to()` keeps it. Both are no-ops on a present value.
- Use `debug_name` when one component has several producers.

Related: [Bindings](../concepts/bindings.md), [Topology](topology.md), [Semantics](semantics.md), [Compile](compile.md), [Modules](modules.md), [Reference index](index.md).
