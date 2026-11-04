# Semantics

`Annotation`, `NodeLabel` and `EdgeLabel` carry the portable meaning and target-neutral naming of a declaration into the blueprint and the graph outputs.

Semantics are independent of the data: a description is prose for a reader, an annotation is a typed payload for a tool, and a label names the component in a target. See [Semantics and annotations](../concepts/semantics.md).

```python
from dataclasses import dataclass

from kg_build_system import Annotation, NodeLabel, NodeOptions, Node

@dataclass(frozen=True)
class Provenance(Annotation):
    """The build stage that produced or tracks the component."""
    namespace = "example"
    annotation_id = "provenance"
    stage: str

class SiteNode(Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"), Provenance("bound")))
```

## `Annotation`

An annotation is a frozen dataclass with a stable namespace, a stable identifier and payload fields:

```python
from dataclasses import dataclass
from typing import ClassVar

from kg_build_system import Annotation

@dataclass(frozen=True)
class MyAnnotation(Annotation):
    namespace: ClassVar[str] = "example"
    annotation_id: ClassVar[str] = "my_annotation"
    field: str
```

| Member | Kind | Meaning |
| --- | --- | --- |
| `namespace` | `ClassVar[str]` | Stable namespace owned by the declaring project or framework |
| `annotation_id` | `ClassVar[str]` | Stable identifier within the namespace |
| Payload fields | Dataclass fields | The fact the annotation records |

The blueprint stores only the namespace, the identifier and the frozen JSON payload. It never stores the annotation class. A consumer matches on namespace and identifier and reads the payload; an annotation it does not recognise is preserved and ignored.

Keep the payload JSON-compatible and stable. Do not encode the owner, the component name or the binding name in it: the attachment already says what the annotation belongs to.

```python
from dataclasses import dataclass

from kg_build_system import Annotation, NodeLabel, NodeOptions

@dataclass(frozen=True)
class SourceSystem(Annotation):
    namespace = "example"
    annotation_id = "source_system"
    system: str

options = NodeOptions(
    annotations=(NodeLabel("Site"), SourceSystem("estate-register")),
)
```

### Errors

| Condition | Error |
| --- | --- |
| An `annotations=` sequence contains a non-`Annotation` value | `TypeError: annotations must contain only Annotation values` |
| The annotation is not a dataclass | Blueprint creation fails when `asdict()` is called; declare the payload with `@dataclass(frozen=True)` |

Declare the payload with `@dataclass(frozen=True)` and stable class variables. The framework treats every `Annotation` instance as portable data.

## Labels

```python
NodeLabel(label: str)
EdgeLabel(label: str)
```

A label is an annotation with a framework-defined namespace and identifier:

| Name | Namespace | Identifier | Applies to |
| --- | --- | --- | --- |
| `NodeLabel` | `kg_build_system.topology` | `node_label` | Node components |
| `EdgeLabel` | `kg_build_system.topology` | `edge_label` | Edge components |

A node label becomes the target's node label and an edge label its relationship type. Neo4j writes a node label as `:LABEL` and an edge label as `:TYPE`.

```python
from kg_build_system import (
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions,
)

class SiteNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))

class HasUnitEdge(Edge[SiteNode, SiteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
```

Without a label, a component's label is its logical name: `SiteNode` defaults to `site`.

At most one label of the matching kind may appear in the effective annotations. The check runs when the declaration class is created, against the complete effective set, including template annotations:

| Condition | Error |
| --- | --- |
| `label` is not a string | `TypeError: node labels must be strings` or `edge labels must be strings` |
| `label` is empty or whitespace | `ValueError: node labels must be non-empty` or `edge labels must be non-empty` |
| More than one matching label | `TypeError: <Class> has <n> node labels in its effective annotations; a graph component carries at most one` |
| A label of the wrong kind | `ValueError: <kind> component '<name>' has an incompatible <OtherLabel> annotation` when a target reads labels |

A wrong-kind label remains an ordinary annotation in the blueprint; it is not a label for that component.

## Descriptions

A description is prose attached to a declaration, field or property. It is not an annotation and carries no typed payload.

| Declaration | Description source | Precedence |
| --- | --- | --- |
| `Node` / `Edge` | `options.description`, then the class docstring | Explicit option wins |
| `property()` | `description=`, then the docstring directly below the assignment | Explicit argument wins |
| `field()` | `description=`, then the docstring directly below the assignment | Explicit argument wins |
| `computed_field()` | `description=`, then the docstring directly below the assignment | Explicit argument wins |
| `Table`, `Struct`, `Projection`, `TableGroup` | `options.description`, then the class docstring | Explicit option wins |

```python
from kg_build_system import Node, NodeOptions, PropertySlot, property

class UnitNode(Node):
    """A monitored piece of equipment."""

    options = NodeOptions(
        description="Installed equipment held on the asset register.",
    )
    asset_tag: PropertySlot[str] = property()
    """The estate feed's asset tag for the unit."""
```

A component description is own-only. A concrete component with neither its own option nor its own docstring has no description, even when its category parent is documented. A label is own-only in the same way.

A property description belongs to the declaring class and travels with the inherited property. A subclass does not replace it by writing a new docstring over the inherited slot.

An attribute docstring is recovered from the declaration's source when the class is created. If the source cannot be read — a class built from a string or typed into a REPL, for example — the string yields no description; `description=` always works.

## Annotation flow

A template records its own annotations as one frozen tuple when the template class is created. A host's effective annotations are:

```text
template annotations in C3 order, each template once, base template before derived,
followed by the host's own options.annotations
```

```python
from kg_build_system import (
    AbstractNode, Annotation, Node, NodeLabel, NodeOptions,
    NodeOptionsTemplate, NodeTemplate, PropertySlot, property,
)

@dataclass(frozen=True)
class Provenance(Annotation):
    namespace = "example"
    annotation_id = "provenance"
    stage: str

class AuditedTemplate(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(Provenance("audited"),))
    source_version: PropertySlot[str] = property()
    """The data release the node's facts were built from."""

class EquipmentNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Equipment"),))

class RecordNode(AuditedTemplate, EquipmentNode, Node):
    """A recorded unit, tracked and provenanced."""
```

| Declaration | Effective annotations | Label |
| --- | --- | --- |
| `AuditedTemplate` | `Provenance("audited")` | None; it is not a component |
| `EquipmentNode` | `NodeLabel("Equipment")` | `Equipment` on the category entry |
| `RecordNode` | `Provenance("audited")` | Defaults to the logical name `record` |

A category's own annotations are not copied down. `RecordNode` does not receive the `Equipment` label. Label uniqueness is checked against the complete effective set, so a template cannot accidentally give a component two labels.

## Where annotations attach

| Declaration | Argument |
| --- | --- |
| Node or edge component | `NodeOptions(annotations=...)` / `EdgeOptions(annotations=...)` |
| Node or edge template | `NodeOptionsTemplate(annotations=...)` / `EdgeOptionsTemplate(annotations=...)` |
| Property | `property(annotations=...)` |
| Field | `field(annotations=...)` |
| Projection output | `computed_field(annotations=...)` |
| Table, struct, projection or table group | the class's `options` |
| Struct template | `StructOptionsTemplate(annotations=...)` |
| Binding | `BindingOptions(annotations=...)` |
| Asset | `AssetOptions(annotations=...)` |

A binding has no description. Use `debug_name` for its human handle and annotations for its metadata; see [Bindings](bindings.md).

## What consumers see

| Output | Semantic content |
| --- | --- |
| Blueprint | Every annotation on every reached declaration, with namespace and payload |
| `meta_graph.json` | Labels, descriptions, properties with logical types and descriptions, counts and examples |
| Neo4j bundle | Effective node labels and relationship types |

Only declarations the build reaches enter the blueprint: the tables and projections read by a binding, the components a binding targets and their ancestors and endpoints, the structs those types use, and the sources those tables need. An annotation on an unrelated declaration is valid Python but is not published.

## Errors

| Condition | Error |
| --- | --- |
| A non-`Annotation` value in an annotations sequence | `TypeError: annotations must contain only Annotation values` |
| `NodeLabel` or `EdgeLabel` receives a non-string | `TypeError: node labels must be strings` / `edge labels must be strings` |
| A label is empty or whitespace | `ValueError: node labels must be non-empty` / `edge labels must be non-empty` |
| A component has two labels of its kind | `TypeError: <Class> has <n> <kind> labels in its effective annotations; a graph component carries at most one` |
| A template uses `NodeOptions` or `EdgeOptions` | `TypeError: <Class> is a node template: its options must be NodeOptionsTemplate, which carries no identity fields` (the edge form names `EdgeOptionsTemplate`) |
| A component uses template options | `TypeError: <Class> is a graph component declaration: declare NodeOptions, not template options` (the edge form names `EdgeOptions`) |

## What to remember

- Descriptions are prose for humans; annotations are typed payloads for tools.
- An explicit `description=` wins over the docstring; component descriptions are not inherited.
- An annotation is a frozen dataclass with a stable namespace and identifier; only its payload is published.
- A node or edge carries at most one label of its kind.
- Template annotations flow to the host in order; category annotations do not.
- Only annotations on reached declarations enter the blueprint.

Related: [Semantics and annotations](../concepts/semantics.md), [Topology](topology.md), [Bindings](bindings.md), [Compile](compile.md), [Reference index](index.md).
