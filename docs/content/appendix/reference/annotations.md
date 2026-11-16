---
title: Annotations reference
summary: Exact annotations, labels, displayed meaning text, template annotation flow and the errors a declaration raises.
section: reference
perspective: reference
order: 140
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/annotations/model/public/base.py
  - kg_build_system/distribution/languages/annotations/model/public/labels.py
  - kg_build_system/distribution/languages/annotations/service/_private/validation.py
  - kg_build_system/distribution/languages/topology/service/_private/class_creation.py
  - docs/content/appendix/reference/annotations.md
---

## Surface

`Annotation`, `NodeLabel` and `EdgeLabel` carry the portable meaning and target-neutral naming of a declaration into the blueprint and the graph outputs.

| Surface | Kind | Carries |
| --- | --- | --- |
| `Annotation` | Frozen dataclass | A stable namespace, a stable identifier and a JSON-compatible payload. |
| `NodeLabel` / `EdgeLabel` | Framework annotation | One label string for a node or edge component. |
| Display text | Prose | The declaration's purpose, first claim or field definition; never a typed payload. |
| `meaning` | Declaration fragment | An optional purpose with its limitations, plus contextless claims, attached by an options value. See [Declare meaning](/book/part-2/01-meaning-and-purpose). |

Read [Declare meaning](/book/part-2/01-meaning-and-purpose) for the meaning-unit language, [Meaning specification](/appendix/spec/meaning) for the requirement and [Meaning subject](/appendix/subjects/meaning) for the views.

## Details

Annotations and labels are independent of the data: an annotation is a typed payload for a tool, and a label names the component in a target. A display surface reads the declaration's meaning, not a separate description field. See [Declare meaning](/book/part-2/01-meaning-and-purpose) for the model and [Semantic hierarchy](/appendix/philosophy/semantic-hierarchy) for the design rationale.

This page covers annotations, labels and the text a display surface reads. Meaning units (`Claim`, `Limitation`, `Purpose` and `Meaning`) are the separate meaning language; see [Declare meaning](/book/part-2/01-meaning-and-purpose) and [Meaning specification](/appendix/spec/meaning).

```python
from dataclasses import dataclass

from kg_build_system import Annotation, Node, NodeLabel, NodeOptions, Omitted

@dataclass(frozen=True)
class Provenance(Annotation):
    """The build stage that produced or tracks the component."""
    namespace = "example"
    annotation_id = "provenance"
    stage: str

class SiteNode(Node):
    """A monitored site: a premises the estate maintains."""

    options = NodeOptions(annotations=(NodeLabel("Site"), Provenance("bound")), meaning=Omitted)
```

### `Annotation`

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

from kg_build_system import Annotation, NodeLabel, NodeOptions, Omitted

@dataclass(frozen=True)
class SourceSystem(Annotation):
    namespace = "example"
    annotation_id = "source_system"
    system: str

options = NodeOptions(
    annotations=(NodeLabel("Site"), SourceSystem("estate-register")),
    meaning=Omitted,
)
```

#### Errors

| Condition | Error |
| --- | --- |
| An `annotations=` sequence contains a non-`Annotation` value | `TypeError: annotations must contain only Annotation values` |
| The annotation is not a dataclass | Blueprint creation fails when `asdict()` is called; declare the payload with `@dataclass(frozen=True)` |

Declare the payload with `@dataclass(frozen=True)` and stable class variables. The framework treats every `Annotation` instance as portable data.

### Labels

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
    Edge, EdgeLabel, EdgeOptions, Node, NodeLabel, NodeOptions, Omitted,
)

class SiteNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),), meaning=Omitted)

class HasUnitEdge(Edge[SiteNode, SiteNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),), meaning=Omitted)
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

### Meaning replaces description

A declaration carries no `description` option. Its `Meaning` states what it is
for and what it asserts; a display surface reads the purpose text, then the first
claim, then the field definition's value. A free-text summary would duplicate
that text and drift from it.

| Declaration | Display text |
| --- | --- |
| `Node`, `Edge`, `Asset`, `Struct`, `SourceRelation` | Purpose text, else the first claim |
| A property or a field | Its `Meaning` purpose or first claim, else the `FieldDefinition` value |
| `DerivedRelation` | Its contract purpose |

A declaration with no meaning states `meaning=Omitted`. The blueprint records no
meaning for it, and a display surface shows nothing rather than inventing prose.
The graph declaration, a published contract and a binding cannot opt out.

A module docstring states the file's role; it is not a declaration's meaning and
does not become a description.

### Annotation flow

A template records its own annotations as one frozen tuple when the template class is created. A host's effective annotations are:

```text
template annotations in C3 order, each template once, base template before derived,
followed by the host's own options.annotations
```

```python
from dataclasses import dataclass

from kg_build_system import (
    AbstractNode, Annotation, Node, NodeLabel, NodeOptions,
    NodeOptionsTemplate, NodeTemplate, Omitted, PropertySlot, property,
)

@dataclass(frozen=True)
class Provenance(Annotation):
    namespace = "example"
    annotation_id = "provenance"
    stage: str

class AuditedTemplate(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(Provenance("audited"),), meaning=Omitted)
    source_version: PropertySlot[str] = property(meaning=Omitted)
    """The data release the node's facts were built from."""

class EquipmentNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Equipment"),), meaning=Omitted)

class RecordNode(AuditedTemplate, EquipmentNode, Node):
    """A recorded unit, tracked and provenanced."""
```

| Declaration | Effective annotations | Label |
| --- | --- | --- |
| `AuditedTemplate` | `Provenance("audited")` | None; it is not a component |
| `EquipmentNode` | `NodeLabel("Equipment")` | `Equipment` on the category entry |
| `RecordNode` | `Provenance("audited")` | Defaults to the logical name `record` |

A category's own annotations are not copied down. `RecordNode` does not receive the `Equipment` label. Label uniqueness is checked against the complete effective set, so a template cannot accidentally give a component two labels.

### Where annotations attach

| Declaration | Argument |
| --- | --- |
| Node or edge component | `NodeOptions(annotations=...)` / `EdgeOptions(annotations=...)` |
| Node or edge template | `NodeOptionsTemplate(annotations=...)` / `EdgeOptionsTemplate(annotations=...)` |
| Property | `property(annotations=...)` |
| Field | `field(annotations=...)` |
| DerivedRelation output | `computed_field(annotations=...)` |
| Source relation, struct, derived relation or source relation group | the class's `options` |
| Struct template | `StructOptionsTemplate(annotations=...)` |
| Binding | `BindingOptions(annotations=...)` |
| Asset | `AssetOptions(annotations=...)` |

A binding has no description. Use `name` for its human handle and annotations for its metadata; see [Bindings reference](/appendix/reference/bindings).

### What consumers see

| Output | Semantic content |
| --- | --- |
| Blueprint | Every annotation on every reached declaration, with namespace and payload |
| `meta_graph.json` | Labels, displayed meaning text, properties with logical types and their display text, counts and examples |
| Neo4j bundle | Effective node labels and relationship types |

Only declarations the build reaches enter the blueprint: the source relations and derived relations read by a binding, the components a binding targets and their ancestors and endpoints, the structs those types use, and the sources those relations need. An annotation on an unrelated declaration is valid Python but is not published.

### Errors

| Condition | Error |
| --- | --- |
| A non-`Annotation` value in an annotations sequence | `TypeError: annotations must contain only Annotation values` |
| `NodeLabel` or `EdgeLabel` receives a non-string | `TypeError: node labels must be strings` / `edge labels must be strings` |
| A label is empty or whitespace | `ValueError: node labels must be non-empty` / `edge labels must be non-empty` |
| A component has two labels of its kind | `TypeError: <Class> has <n> <kind> labels in its effective annotations; a graph component carries at most one` |
| A template uses `NodeOptions` or `EdgeOptions` | `TypeError: <Class> is a node template: its options must be NodeOptionsTemplate, which carries no identity fields` (the edge form names `EdgeOptionsTemplate`) |
| A component uses template options | `TypeError: <Class> is a graph component declaration: declare NodeOptions, not template options` (the edge form names `EdgeOptions`) |
| `meaning` is neither a `Meaning` nor `Omitted` | `TypeError: <context> meaning must be a Meaning value or the Omitted marker` |

### What to remember

- A declaration has no description; its `Meaning` is the text a display surface reads.
- An annotation is a typed payload for tools; it is not a substitute for meaning.
- An annotation is a frozen dataclass with a stable namespace and identifier; only its payload is published.
- A node or edge carries at most one label of its kind.
- Template annotations flow to the host in order; category annotations do not.
- Only annotations on reached declarations enter the blueprint.

For the declaration that receives a label, see [Topology reference](/appendix/reference/topology). For a binding's annotations and `name`, see [Bindings reference](/appendix/reference/bindings). For the attachment forms on data declarations, see [Declarations](/appendix/reference/declarations). For the pipeline that publishes the blueprint, see [Compile](/appendix/reference/compile).
