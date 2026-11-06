# Semantics language

The semantics language states what a graph or one declaration means. It is a
separate channel from descriptions and annotations: the build publishes authored
meaning units as data, alongside the topology, data declarations and bindings.

Write the units from `kg_build_system`:

```python
from kg_build_system import (
    Claim, Frame, Graph, GraphOptions, GraphSemantics, Limitation, Purpose,
    Semantics,
)
```

## Two levels of semantics

A semantics value is either the project's meaning root or a declaration
fragment:

```text
GraphSemantics(claims=(), *, purpose)
Purpose(text, frames=())

Semantics(claims=(), frames=())
```

- `GraphSemantics` is the meaning root of the project. It owns the claims that
  are true of the graph and exactly one `Purpose`.
- `Semantics` is a declaration fragment. It has claims and frames, but no purpose
  of its own; every frame is read under the graph's one purpose.
- `Purpose(text, frames=())` is the expected use of the graph.
- `Frame(text, limitations=())` is the scope and boundary of the limitation space
  within the purpose. A frame owns its limitations.
- `Claim(text)` and `Limitation(text)` are text units.

| Unit | Answers | Owned by |
| --- | --- | --- |
| `Claim` | What is, regardless of purpose or frame? | `GraphSemantics` or `Semantics` |
| `Purpose` | What is the graph for? | `GraphSemantics` only |
| `Frame` | Within what scope is the limitation stated? | `Purpose` or `Semantics` |
| `Limitation` | What must a reader know given the purpose and frame? | `Frame` only |

Claims never live under a frame. Limitations never live directly under a
purpose. A declaration's frames are read under the graph purpose, which is
implicit for that declaration.

## Claims and limitations

A claim is contextless. Write a claim when the statement holds for the graph or
declaration no matter how a consumer intends to use it:

```python
Semantics(claims=(Claim("Scores are per datatype."),))
```

A limitation depends on the purpose and frame. Write a frame when the meaning
changes with the intended use, and put the limitation under that frame:

```python
Semantics(
    frames=(
        Frame(
            text="Curated evidence only.",
            limitations=(
                Limitation("No literature mining is present."),
                Limitation("Non-human organisms are excluded."),
            ),
        ),
    ),
)
```

A limitation is a statement about absence, exclusion or support, not an error.
Recording it lets a consumer decide whether the graph answers its question;
inventing precision is the only wrong answer.

Every unit has non-empty text. `Frame.limitations` accepts only `Limitation`
values, and `Purpose.frames` accepts only `Frame` values. Units are immutable and
carry no key, owner or reference.

## One graph declaration per project

The graph declaration states the project's meaning root. Declare it once in the
project's namespace:

```python
class OpenTargetsGraph(Graph):
    options = GraphOptions(
        name="open_targets",
        description="Curated target-disease evidence.",
        semantics=GraphSemantics(
            claims=(Claim("The graph describes gene-disease associations."),),
            purpose=Purpose(
                text="Target prioritisation.",
                frames=(
                    Frame(
                        text="Curated evidence only.",
                        limitations=(
                            Limitation("No literature mining is present."),
                        ),
                    ),
                ),
            ),
        ),
    )
```

`GraphOptions` accepts keyword arguments. `semantics` is required and must be a
`GraphSemantics` carrying a `Purpose`; `purpose` itself is keyword-only. `name`
defaults to the class name in snake case and `description` is optional prose.

A namespace may declare zero graph declarations or exactly one. Zero is valid for
a project that has not adopted the language. Two declarations fail at discovery
because a project has exactly one meaning root.

The graph declaration is not a node, edge or asset. It becomes the
`graph_declaration` member of the blueprint when present, and is rendered before
the other layers when a blueprint is written back to source.

## Where semantics attach

A declaration attaches one `Semantics` fragment through the options or helper
that owns it:

| Declaration | Attachment |
| --- | --- |
| Asset | `AssetOptions(semantics=...)`; the profile is separate |
| Table | `TableOptions(semantics=...)` |
| Struct | `StructOptions(semantics=...)` |
| Projection | `ProjectionOptions(semantics=...)` |
| Source field | `field(semantics=...)` |
| Computed field | `computed_field(semantics=...)` |
| Node or edge | `NodeOptions(semantics=...)` / `EdgeOptions(semantics=...)` |
| Node or edge template | `NodeOptionsTemplate(semantics=...)` / `EdgeOptionsTemplate(semantics=...)` |
| Property | `property(semantics=...)` |
| Binding | `BindingOptions(semantics=...)`, or `node_binding(semantics=...)` / `edge_binding(semantics=...)` |

`TableGroupOptions` does not carry semantics. A table group is a catalog of
tables, not a blueprint part, so it has no declaration to attach semantics to.
Per-property binding semantics is also not part of v1; attach one fragment to the
whole binding.

A declaration attachment accepts `Semantics`, never `GraphSemantics`. Passing the
graph meaning root where a declaration fragment belongs is an error.

```python
class TargetTable(Table[OpenTargets]):
    options = TableOptions(
        name="targets",
        semantics=Semantics(
            claims=(Claim("One row is one target."),),
        ),
    )
    target_id: Field[str] = field(
        semantics=Semantics(
            frames=(
                Frame(
                    text="Identifiers from the release.",
                    limitations=(
                        Limitation("The identifier is not a stable accession."),
                    ),
                ),
            ),
        ),
    )


class TargetNode(Node):
    approved_symbol: PropertySlot[str] = property(
        semantics=Semantics(
            claims=(Claim("The symbol is the approved gene symbol."),),
        ),
    )


binding = node_binding(
    target=TargetNode,
    build_key=TargetTable.target_id,
    properties=TargetNode(approved_symbol=TargetTable.approved_symbol),
    semantics=Semantics(
        claims=(Claim("One target row yields one target node."),),
    ),
)
```

## Asset profile and asset semantics

An asset has two different authoring values:

- `AssetProfile` is source-data metadata: `subject`, `coverage`, `authority`,
  `basis` and optional `title` and `description`. It says what the source data
  represents and how it was produced. It has no claims or limitations.
- `AssetOptions(semantics=...)` is an optional `Semantics` fragment. It states
  what the asset means and the limits of that meaning in the same units as every
  other declaration.

```python
class OpenTargets(Asset):
    options = AssetOptions(
        profile=AssetProfile(
            subject="gene-disease associations",
            coverage="curated evidence for human genes and diseases",
            authority=AssetAuthority.PRIMARY,
            basis="Open Targets Platform release",
            title="Open Targets Platform",
        ),
        semantics=Semantics(
            claims=(
                Claim("Each association names the evidence that supports it."),
            ),
            frames=(
                Frame(
                    text="Curated evidence only.",
                    limitations=(
                        Limitation("Non-human organisms are excluded."),
                    ),
                ),
            ),
        ),
    )
```

`profile` is required; `semantics` is optional. The profile is not a substitute
for the semantics language, and a claim or limitation belongs in `semantics`, not
in the profile.

## Source and document shape

The canonical declaration document omits an empty optional member:

```json
{
  "claims": [{"text": "Scores are per datatype."}],
  "frames": [
    {
      "text": "Curated evidence only.",
      "limitations": [{"text": "No literature mining is present."}]
    }
  ]
}
```

The graph document always carries its purpose:

```json
{
  "claims": [{"text": "The graph describes associations."}],
  "purpose": {
    "text": "Target prioritisation.",
    "frames": [
      {
        "text": "Curated evidence only.",
        "limitations": [{"text": "No literature mining is present."}]
      }
    ]
  }
}
```

An absent `claims`, `frames` or `limitations` member means an empty tuple. A
declaration document carries `"semantics"` only when a fragment is attached. The
blueprint document carries `"graph_declaration"` only when the project declares a
graph.

Source generation renders each declaration's `semantics=` with the semantics
language. The graph declaration renders first, followed by assets, topology, data
and bindings. The round trip `blueprint -> source -> blueprint` preserves every
unit.

## The one-purpose rule

There is exactly one project purpose, and it is not repeated on declarations:

- `GraphSemantics` requires a `Purpose`; omitting it is an error.
- `Semantics` has no purpose parameter. A declaration frame is interpreted under
  the graph purpose.
- A `Purpose` owns frames; a frame owns limitations. The nesting is enforced by
  the unit types.
- `Semantics()` with no claim and no frame is invalid. A `GraphSemantics` with a
  purpose and no claims is valid, and frames may be empty.

If a statement only makes sense under a narrower scope, it is a limitation in a
frame. If it holds regardless of the intended use, it is a claim at the
declaration or graph level.

## Limits

- Units carry no key, owner or reference in v1. The attachment says what they
  belong to.
- There is no inheritance, cut, change, revision, resolution or truth evaluation.
  The blueprint publishes the authored units; consumers compose them.
- A declaration fragment cannot declare its own purpose.
- A declaration attachment rejects `GraphSemantics`; only the graph declaration
  carries the meaning root.
- `TableGroupOptions` has no semantics field and a table group has no blueprint
  part.
- Per-property binding semantics, decisions, approval and catalogue rendering are
  out of scope.

## Next steps

- [Semantics and annotations](semantics.md) separates meaning units from
  descriptions, labels and annotation payloads.
- [Assets](assets.md) explains `AssetProfile`, layout and governance.
- [Topology](topology.md) and [bindings](bindings.md) show where declaration
  fragments attach.
- [Compile, execute and outputs](build-and-outputs.md) follows the blueprint that
  carries `graph_declaration` and each declaration's `semantics`.
