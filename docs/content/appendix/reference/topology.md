---
title: Topology reference
summary: Exact declarations, options, property slots, templates, base order and endpoint rules for node and edge topology.
section: reference
perspective: reference
order: 120
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/topology/model/public/declarations.py
  - kg_build_system/distribution/languages/topology/model/public/options.py
  - kg_build_system/distribution/languages/topology/service/_private/class_creation.py
  - kg_build_system/distribution/languages/topology/model/_private/properties.py
  - docs/content/appendix/reference/topology.md
---

## Surface

`Node`, `AbstractNode`, `Edge` and `AbstractEdge` declare graph components, while `NodeTemplate` and `EdgeTemplate` share properties and annotations without entering the graph.

| Declaration | Form | Role |
| --- | --- | --- |
| `Node` | `class SiteNode(Node)` | Concrete, terminal and bindable node record. |
| `AbstractNode` | `class AssetNode(AbstractNode)` | Graph-visible node category; produces no records. |
| `Edge[S, D]` | `class LinkedEdge(Edge[AssetNode, AssetNode])` | Directed, concrete and bindable edge. |
| `AbstractEdge[S, D]` | `class LinkAbstractEdge(AbstractEdge[AssetNode, AssetNode])` | Graph-visible relationship family; never a binding target. |
| `NodeTemplate` / `EdgeTemplate` | `class ProvenancedNodeTemplate(NodeTemplate)` | Inert property and annotation mixin; never a graph component. |
| `PropertySlot[T]` + `property()` | `name: PropertySlot[str] = property(meaning=...)` | One declared graph property, its value type and its meaning. |
| `endpoint(target)` | `endpoint(SiteNode)` | One concrete node token for an abstract edge side. |

Read [Declare topology](/book/part-2/02-topology) for the authoring path, [Topology specification](/appendix/spec/topology) for the requirement and [Topology subject](/appendix/subjects/topology) for the views.

## Details

Topology is data-independent: it names a component, its properties and, for an edge, its endpoints. Values arrive only through a binding. See [Declare topology](/book/part-2/02-topology) for the model, [Bind records](/book/part-2/08-binding) and [Bindings reference](/appendix/reference/bindings) for the values, and [Annotations reference](/appendix/reference/annotations) for annotations and labels.

```python
from kg_build_system import (
    AbstractNode, Claim, Edge, EdgeLabel, EdgeOptions, Meaning, Node,
    NodeLabel, NodeOptions, PropertySlot, property,
)

class AssetNode(AbstractNode):
    options = NodeOptions(
        annotations=(NodeLabel("Asset"),),
        meaning=Meaning(claims=(Claim("A thing the register records."),)),
    )
    summary: PropertySlot[str] = property(
        meaning=Meaning(claims=(Claim("A one-line summary of the asset."),)),
    )

class SiteNode(AssetNode, Node):
    options = NodeOptions(
        annotations=(NodeLabel("Site"),),
        meaning=Meaning(claims=(Claim("A monitored site."),)),
    )
    name: PropertySlot[str] = property(
        meaning=Meaning(claims=(Claim("The site's display name."),)),
    )

class LinkedEdge(Edge[AssetNode, AssetNode]):
    options = EdgeOptions(
        annotations=(EdgeLabel("LINKED"),),
        meaning=Meaning(claims=(Claim("One asset is linked to another."),)),
    )
    since: PropertySlot[str | None] = property(
        meaning=Meaning(claims=(Claim("When the link was asserted."),)),
    )
```

### Component bases

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

### `NodeOptions` and `EdgeOptions`

```python
NodeOptions(
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    *,
    meaning: Meaning | type[Omitted],
)

EdgeOptions(
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    *,
    meaning: Meaning | type[Omitted],
)
```

Assign the value to the class variable `options`.

| Field | Meaning | Default |
| --- | --- | --- |
| `name` | Logical graph name; unique across nodes and edges | Inferred from the class name |
| `annotations` | Portable metadata, including at most one matching label | Empty |
| `meaning` | One declaration fragment attached under the graph purpose, or `Omitted` | Required |

The inferred name removes one tier suffix and converts the remainder to snake case:

| Class | Inferred name |
| --- | --- |
| `SiteNode` | `site` |
| `LinkedEdge` | `linked` |
| `AssetNode` | `asset` |
| `DocumentedAbstractNode` | `documented` |

An abstract class strips `AbstractNode` or `AbstractEdge` before the plain tier suffix, so `DocumentedAbstractNode` does not become `documented_abstract`.

An explicit `options.name` replaces the inference completely. Component names must be unique across all reached nodes and edges. A concrete component does not inherit its category's meaning or label; see [Annotations reference](/appendix/reference/annotations) and [Semantic hierarchy](/appendix/philosophy/semantic-hierarchy).

```python
class UnitNode(Node):
    options = NodeOptions(
        name="equipment",
        meaning=Meaning(claims=(Claim("Installed equipment held on the register."),)),
    )
```

### `property()`

```python
property(
    *,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> PropertySlot[T]
```

Declare a graph property by assigning the result to a class attribute annotated as `PropertySlot[T]`.

```python
class UnitNode(Node):
    asset_tag: PropertySlot[str] = property(
        meaning=Meaning(
            claims=(Claim("The estate feed's asset tag for the unit."),),
        ),
    )

    labels: PropertySlot[Array[str] | None] = property(meaning=Omitted)
```

| Argument | Meaning | Default |
| --- | --- | --- |
| `name` | External property name | The attribute name in snake case, with one trailing underscore removed |
| `annotations` | Portable metadata for the property | Empty |
| `meaning` | One declaration fragment attached under the graph purpose, or `Omitted` | Required |

`PropertySlot[T]` accepts a scalar, `T | None`, a flat `Array[T]`, or `Array[T] | None`. Scalars are `bool`, `int`, `float`, `str`, `Date`, `Time`, `Timestamp`, `Uuid` and `CustomDataType`. Arrays are one level deep and hold non-null scalars. Structs, nested arrays and arrays with null items are not graph properties. See [Type vocabulary](/appendix/reference/types).

`options_` is the escape for a name collision with the framework's `options` class variable: the external name is `options`. Two properties on one component may not share an external name.

A property meaning belongs to the declaring class. An inherited property keeps
its meaning and its declaration.

```python
from kg_build_system import Array, Omitted, Timestamp

class ReadingNode(Node):
    recorded_on: PropertySlot[Timestamp] = property(
        meaning=Meaning(
            claims=(Claim("The instant the reading was taken."),),
        ),
    )
    values: PropertySlot[Array[float]] = property(meaning=Omitted)
```

#### Errors

| Condition | Error |
| --- | --- |
| `name=""` | `ValueError: property names must be non-empty` |
| The attribute is not annotated with exactly one type argument | `TypeError: <Class>.<attr> must be annotated as PropertySlot[T]` |
| The type is an unsupported graph property | `TypeError` naming the property and the unsupported shape |
| An array item is an array, struct or nullable | `TypeError` naming the property; flatten or use `drop_null_items()` |
| Two attributes resolve to one external name | `TypeError: <Class> properties '<a>' and '<b>' share external name '<name>'` |
| `annotations` contains a non-`Annotation` value | `TypeError: annotations must contain only Annotation values` |

A declaration has no docstring. Its `meaning` is its documentation; a module or
file docstring may state the file's role, not the declaration's meaning.

### Templates

`NodeTemplate` and `EdgeTemplate` are inert mixins. They share property slots and annotations with their hosts, but they never become graph components, receive a logical name, become a binding target or become an edge endpoint.

```python
from kg_build_system import (
    Node, NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)

class ProvenancedNodeTemplate(NodeTemplate):
    options = NodeOptionsTemplate(meaning=Omitted)
    source_version: PropertySlot[str] = property(meaning=Omitted)

class MeterNode(ProvenancedNodeTemplate, Node):
    name: PropertySlot[str] = property(meaning=Omitted)
```

A template's options are annotations-only:

```python
NodeOptionsTemplate(
    annotations: Sequence[Annotation] = (),
    *,
    meaning: Meaning | type[Omitted],
)
EdgeOptionsTemplate(
    annotations: Sequence[Annotation] = (),
    *,
    meaning: Meaning | type[Omitted],
)
```

| Class | Required options type |
| --- | --- |
| `NodeTemplate` subclass | `NodeOptionsTemplate` |
| `EdgeTemplate` subclass | `EdgeOptionsTemplate` |

A template has no `name`. Passing `NodeOptions` or `EdgeOptions` to a template is refused; so is passing a template-options value to a concrete or abstract component.

A declaration may mix in any number of templates of its own kind. Keep one property slot per name: redeclaring an inherited slot at another type is a static type error.

### Base order

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

### Edge endpoints

An edge declares its endpoints with two node-side type arguments. An abstract edge may declare categories; a concrete edge under it may keep those endpoints or narrow them.

```python
from kg_build_system import AbstractEdge, Edge, EdgeLabel, EdgeOptions, Omitted

class MonitoredAbstractEdge(AbstractEdge[AssetNode, AssetNode]):
    options = EdgeOptions(annotations=(EdgeLabel("MONITORED"),), meaning=Omitted)

class AssetAtEdge(MonitoredAbstractEdge, Edge[SiteNode, SiteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("ASSET_AT"),), meaning=Omitted)
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

### `endpoint()`

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

An endpoint token is required exactly when the declared side is an abstract category. A concrete declared side needs no token, but supplying one still documents the concrete component used. See [Bindings reference](/appendix/reference/bindings#endpoint-tokens).

#### Errors

| Condition | Error |
| --- | --- |
| `target` is not a class | `TypeError: <value> is not a concrete node` |
| `target` is abstract, a template, an edge or a plain class | `TypeError: '<name>' is not a concrete node` |

### Category reachability

Only reached categories enter the blueprint. A category is reached when:

- a bound concrete component names it as an ancestor; or
- a bound edge declares it as an endpoint, directly or through an inherited endpoint.

A category entry carries the properties and annotations effective on the category. A category family with no bound descendant and no bound edge endpoint is not published, because nothing in the graph can refer to it.

```python
from kg_build_system import (
    AbstractNode, Field, Meaning, Node, NodeLabel, NodeOptions, PropertySlot,
    Purpose, SourceRelation, SourceRelationOptions, field, node_binding,
    property,
)

from estate.assets import Estate

class SiteSourceRelation(SourceRelation[Estate]):
    # The contract and field definitions are stated in full on Declarations.
    options = SourceRelationOptions(contract=...)
    site_id: Field[str] = field(meaning=Omitted)
    summary: Field[str] = field(meaning=Omitted)
    name: Field[str] = field(meaning=Omitted)

class DocumentedAbstractNode(AbstractNode):
    options = NodeOptions(
        annotations=(NodeLabel("Documented"),), meaning=Omitted,
    )
    summary: PropertySlot[str] = property(meaning=Omitted)

class SiteNode(DocumentedAbstractNode, Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),), meaning=Omitted)
    name: PropertySlot[str] = property(meaning=Omitted)

site_binding = node_binding(
    target=SiteNode,
    build_key=SiteSourceRelation.site_id.alter_rows().drop_null(),
    properties=SiteNode(
        summary=SiteSourceRelation.summary.default_to(""),
        name=SiteSourceRelation.name.default_to("Unnamed site"),
    ),
    meaning=Meaning(
        purpose=Purpose("Populate each site record from the estate survey."),
    ),
)
```

Binding `SiteNode` reaches `DocumentedAbstractNode`; both appear in the blueprint. `DocumentedAbstractNode` keeps the `Documented` label and summary property; `SiteNode` keeps its own `Site` label and does not inherit the category meaning or label.

A category does not create records. Its record count in the meta-graph is the sum of its own and its descendants' records. The nearest category parent is recorded on each concrete component, so a category chain is preserved.

### What to remember

- A node is a thing; an edge is a directed assertion between two node components.
- A concrete component is terminal and bindable; a category is graph-visible and never a target.
- A template shares slots and annotations but has no identity and never enters the blueprint.
- Properties are scalars or flat arrays of non-null scalars; keys are separate and narrower.
- Base order is templates, category parent, terminal base.
- Only categories reached by a binding or endpoint are published.

For the declaration surface that supplies the rows, see [Declarations](/appendix/reference/declarations). For the binding that supplies the values, see [Bindings reference](/appendix/reference/bindings). For the pipeline that consumes the blueprint, see [Compile](/appendix/reference/compile).
