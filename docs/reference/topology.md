# Topology declarations

`Node`, `AbstractNode`, `Edge` and `AbstractEdge` declare graph components, while `NodeTemplate` and `EdgeTemplate` share properties and annotations without entering the graph.

Topology is data-independent: it names a component, its properties and, for an edge, its endpoints. Values arrive only through a binding. See [Topology](../concepts/topology.md) for the model and [Bindings](bindings.md) for the values.

```python
from kg_build_system import (
    AbstractNode, Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
    PropertySlot, property,
)

class AssetNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Asset"),))
    summary: PropertySlot[str] = property()
    """A one-line description of the asset."""

class SiteNode(AssetNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))
    name: PropertySlot[str] = property()
    """The site's display name."""

class LinkedEdge(Edge[AssetNode, AssetNode]):
    options = EdgeOptions(annotations=(EdgeLabel("LINKED"),))
    since: PropertySlot[str | None] = property()
    """When the link was asserted, when the source records it."""
```

## Component bases

| Name | Declaration form | Graph-visible | Bindable |
| --- | --- | --- | --- |
| `Node` | `class SiteNode(Node)` | Yes | Yes |
| `AbstractNode` | `class AssetNode(AbstractNode)` | Yes | No |
| `Edge[S, D]` | `class LinkedEdge(Edge[AssetNode, AssetNode])` | Yes | Yes |
| `AbstractEdge[S, D]` | `class LinkAbstractEdge(AbstractEdge[AssetNode, AssetNode])` | Yes | No |
| `NodeTemplate` | `class ProvenancedNodeTemplate(NodeTemplate)` | No | No |
| `EdgeTemplate` | `class ProvenancedEdgeTemplate(EdgeTemplate)` | No | No |

`Edge[S, D]` is directed: `S` is the source side and `D` the target side. Both type arguments must be node-side declarations, abstract or concrete.

A concrete component is terminal. A class declared as a concrete `Node` or `Edge` may not be subclassed. An abstract component is graph-visible and may be an edge endpoint, but it is never a binding target and produces no records of its own.

## `NodeOptions` and `EdgeOptions`

```python
NodeOptions(
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
)

EdgeOptions(
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
)
```

Assign the value to the class variable `options`.

| Field | Meaning | Default |
| --- | --- | --- |
| `name` | Logical graph name; unique across nodes and edges | Inferred from the class name |
| `description` | Prose description of the component | The class docstring, if present |
| `annotations` | Portable metadata, including at most one matching label | Empty |

The inferred name removes one tier suffix and converts the remainder to snake case:

| Class | Inferred name |
| --- | --- |
| `SiteNode` | `site` |
| `LinkedEdge` | `linked` |
| `AssetNode` | `asset` |
| `DocumentedAbstractNode` | `documented` |

An abstract class strips `AbstractNode` or `AbstractEdge` before the plain tier suffix, so `DocumentedAbstractNode` does not become `documented_abstract`.

An explicit `options.name` replaces the inference completely. Component names must be unique across all reached nodes and edges. A concrete component does not inherit its category's `description` or label; see [Semantics](semantics.md).

```python
class UnitNode(Node):
    options = NodeOptions(name="equipment", description="Installed equipment.")
```

## `property()`

```python
property(
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> PropertySlot[T]
```

Declare a graph property by assigning the result to a class attribute annotated as `PropertySlot[T]`.

```python
class UnitNode(Node):
    asset_tag: PropertySlot[str] = property()
    """The estate feed's asset tag for the unit."""

    labels: PropertySlot[Array[str] | None] = property()
    """Optional labels recorded for the unit."""
```

| Argument | Meaning | Default |
| --- | --- | --- |
| `name` | External property name | The attribute name in snake case, with one trailing underscore removed |
| `description` | Property description | The docstring directly below the assignment |
| `annotations` | Portable metadata for the property | Empty |

`PropertySlot[T]` accepts a scalar, `T | None`, a flat `Array[T]`, or `Array[T] | None`. Scalars are `bool`, `int`, `float`, `str`, `Date`, `Time`, `Timestamp`, `Uuid` and `CustomDataType`. Arrays are one level deep and hold non-null scalars. Structs, nested arrays and arrays with null items are not graph properties. See [Type vocabulary](types.md).

`options_` is the escape for a name collision with the framework's `options` class variable: the external name is `options`. Two properties on one component may not share an external name.

A property description belongs to the declaring class. An inherited property keeps its description and its declaration; a subclass does not replace it by writing a new docstring over the inherited slot.

```python
from kg_build_system import Array, Timestamp

class ReadingNode(Node):
    recorded_on: PropertySlot[Timestamp] = property(
        description="The instant the reading was taken.",
    )
    values: PropertySlot[Array[float]] = property()
```

### Errors

| Condition | Error |
| --- | --- |
| `name=""` | `ValueError: property names must be non-empty` |
| The attribute is not annotated with exactly one type argument | `TypeError: <Class>.<attr> must be annotated as PropertySlot[T]` |
| The type is an unsupported graph property | `TypeError` naming the property and the unsupported shape |
| An array item is an array, struct or nullable | `TypeError` naming the property; flatten or use `drop_null_items()` |
| Two attributes resolve to one external name | `TypeError: <Class> properties '<a>' and '<b>' share external name '<name>'` |
| `annotations` contains a non-`Annotation` value | `TypeError: annotations must contain only Annotation values` |

A docstring is read from the declaration's source when the class is created. A class built from a string or typed directly into a REPL has no readable source, so its docstring yields no description; the `description=` argument always works.

## Templates

`NodeTemplate` and `EdgeTemplate` are inert mixins. They share property slots and annotations with their hosts, but they never become graph components, receive a logical name, become a binding target or become an edge endpoint.

```python
from kg_build_system import (
    Node, NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)

class ProvenancedNodeTemplate(NodeTemplate):
    options = NodeOptionsTemplate()
    source_version: PropertySlot[str] = property()
    """The data release the node's facts were built from."""

class MeterNode(ProvenancedNodeTemplate, Node):
    name: PropertySlot[str] = property()
```

A template's options are annotations-only:

```python
NodeOptionsTemplate(annotations: Sequence[Annotation] = ())
EdgeOptionsTemplate(annotations: Sequence[Annotation] = ())
```

| Class | Required options type |
| --- | --- |
| `NodeTemplate` subclass | `NodeOptionsTemplate` |
| `EdgeTemplate` subclass | `EdgeOptionsTemplate` |

A template has no `name` or `description`. Passing `NodeOptions` or `EdgeOptions` to a template is refused; so is passing a template-options value to a concrete or abstract component.

A declaration may mix in any number of templates of its own kind. Keep one property slot per name: redeclaring an inherited slot at another type is a static type error.

## Base order

The base order is normative:

```text
templates first, the one abstract category parent in the middle, the terminal base last
```

```python
class MeterNode(ProvenancedNodeTemplate, DocumentedAbstractNode, Node):
    ...
```

Templates are read from the ancestry and the category parent is the one direct abstract base. Write the order above so the declaration reads the same way the framework resolves it.

| Rule | Error |
| --- | --- |
| At most one direct abstract category parent | `TypeError: <Class> has more than one abstract category parent: ...` |
| No concrete component in the ancestry | `TypeError: <Class> cannot inherit from concrete graph component <Class>` |
| Only matching-kind templates | `TypeError: <Class> cannot mix node-side and edge-side lineage: ...` |
| No non-framework base class | `TypeError: <Class> inherits non-framework base '<name>': ...` |
| The class descends from a framework root | `TypeError: <Class> must inherit from Node, AbstractNode, NodeTemplate, Edge, AbstractEdge, or EdgeTemplate` |

A category may chain: `class PlaceNode(DocumentedAbstractNode, Node)` records `DocumentedAbstractNode` as its nearest category parent. Categories are siblings of the concrete bases, not concrete bases themselves.

## Edge endpoints

An edge declares its endpoints with two node-side type arguments. An abstract edge may declare categories; a concrete edge under it may keep those endpoints or narrow them.

```python
from kg_build_system import AbstractEdge, Edge, EdgeLabel, EdgeOptions

class MonitoredAbstractEdge(AbstractEdge[AssetNode, AssetNode]):
    options = EdgeOptions(annotations=(EdgeLabel("MONITORED"),))

class AssetAtEdge(MonitoredAbstractEdge, Edge[SiteNode, SiteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("ASSET_AT"),))
```

| Rule | Error |
| --- | --- |
| An edge must declare or inherit a pair of endpoints | `TypeError: <Class> must declare its edge endpoints, for example 'Edge[SourceNode, TargetNode]', or inherit them from an abstract edge` |
| A redeclared endpoint equals or descends from every abstract ancestor's endpoint | `TypeError: <Class> endpoints (...) must equal or descend from its abstract edge lineage (...)` |
| Each endpoint is a node declaration, abstract or concrete | `TypeError: <Class> endpoint category ... is not a node declaration — endpoints must be node components` |
| No endpoint is a template, edge or plain class | Same endpoint error |
| A concrete edge with no pair inherits its parent's pair | No error; the inherited pair is recorded |

Widening an inherited endpoint is refused at class creation. A concrete edge may declare no type arguments and inherit its parent's pair:

```python
class UnnarrowedAssetAtEdge(MonitoredAbstractEdge, Edge):
    ...
```

## `endpoint()`

```python
endpoint(target: type[N]) -> Endpoint[N]
```

`endpoint()` names one concrete node component for an edge binding. It is a frozen value with a `target` field and is passed as `source_node=` or `target_node=` to `edge_binding`.

| Name | Meaning |
| --- | --- |
| `target` | A concrete `Node` class |
| Return | `Endpoint[N]`, carrying `target` |

```python
from kg_build_system import endpoint
site_endpoint = endpoint(SiteNode)
```

An endpoint token is required exactly when the declared side is an abstract category. A concrete declared side needs no token, but supplying one still documents the concrete component used. See [Bindings](bindings.md#endpoint-tokens).

### Errors

| Condition | Error |
| --- | --- |
| `target` is not a class | `TypeError: <value> is not a concrete node` |
| `target` is abstract, a template, an edge or a plain class | `TypeError: '<name>' is not a concrete node` |

## Category reachability

Only reached categories enter the blueprint. A category is reached when:

- a bound concrete component names it as an ancestor; or
- a bound edge declares it as an endpoint, directly or through an inherited endpoint.

A category entry carries the properties and annotations effective on the category. A category family with no bound descendant and no bound edge endpoint is not published, because nothing in the graph can refer to it.

```python
from kg_build_system import (
    AbstractNode, Field, Node, NodeLabel, NodeOptions, PropertySlot, Table,
    field, node_binding, property,
)

from estate.assets import Estate

class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    summary: Field[str] = field()
    name: Field[str] = field()

class DocumentedAbstractNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Documented"),))
    summary: PropertySlot[str] = property()

class SiteNode(DocumentedAbstractNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))
    name: PropertySlot[str] = property()

site_binding = node_binding(
    target=SiteNode,
    build_key=SiteTable.site_id.alter_rows().drop_null(),
    properties=SiteNode(
        summary=SiteTable.summary.default_to(""),
        name=SiteTable.name.default_to("Unnamed site"),
    ),
)
```

Binding `SiteNode` reaches `DocumentedAbstractNode`; both appear in the blueprint. `DocumentedAbstractNode` keeps the `Documented` label and summary property; `SiteNode` keeps its own `Site` label and does not inherit the category description or label.

A category does not create records. Its record count in the meta-graph is the sum of its own and its descendants' records. The nearest category parent is recorded on each concrete component, so a category chain is preserved.

## What to remember

- A node is a thing; an edge is a directed assertion between two node components.
- A concrete component is terminal and bindable; a category is graph-visible and never a target.
- A template shares slots and annotations but has no identity and never enters the blueprint.
- Properties are scalars or flat arrays of non-null scalars; keys are separate and narrower.
- Base order is templates, category parent, terminal base.
- Only categories reached by a binding or endpoint are published.

Related: [Topology](../concepts/topology.md), [Bindings](bindings.md), [Semantics](semantics.md), [Type vocabulary](types.md), [Reference index](index.md).
