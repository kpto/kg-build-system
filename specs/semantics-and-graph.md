# Semantics and graph languages

This spec defines the two languages added to the distribution: `semantics` and
`graph`. It is the interface contract for implementation and review. The viewer
is out of scope.

## Model

A semantics object is either:

- **Graph semantics** — the project's meaning root:
  `GraphSemantics(claims, purpose)` where
  `purpose = Purpose(text, frames)` and each
  `frame = Frame(text, limitations)`.
- **Declaration semantics** — a fragment under the graph purpose:
  `Semantics(claims, frames)` where each frame owns its limitations.

```
GraphSemantics = (claims, purpose -> frame -> limitation)
Semantics      = (claims, frame -> limitation)      # under the graph purpose
```

- **Claim** — a contextless statement: what is, regardless of purpose or frame.
- **Purpose** — the expected use of the graph. Exactly one per project.
- **Frame** — the scope and boundary of the limitation space within the purpose.
- **Limitation** — what the reader must know given the purpose and frame: what
  is absent, excluded, or not supportable.

Claims never live under a frame. Limitations never live directly under a
purpose; they are owned by a frame. A declaration frame is read under the one
graph purpose.

## Public names

Top-level exports from `kg_build_system`:

```python
Claim(text)
Limitation(text)
Frame(text, limitations=())
Purpose(text, frames=())
Semantics(claims=(), frames=())
GraphSemantics(claims=(), *, purpose)
Graph
GraphOptions(*, name=None, description=None, semantics)
AssetProfile(subject, coverage, authority, basis, title=None, description=None)
```

`AssetSemantics` is renamed to `AssetProfile`. It is source-data profile
metadata, not the semantics language, and it has no `claims` or `limitations`
fields. `AssetOptions` gains a required `profile=` and an optional
`semantics=`. The old `claims`/`limitations` fields move to the semantics
language.

## Rules

- Text is non-empty for every unit.
- `Frame.limitations` contains only `Limitation`; `Purpose.frames` contains only
  `Frame`.
- `GraphSemantics` requires a `Purpose`; `purpose` is required, keyword-only and
  non-empty.
- `Semantics` has no purpose. The graph purpose is its implicit root.
- An empty `Semantics()` is invalid; a semantics value has at least one claim or
  frame. An empty `GraphSemantics` with a purpose but no claims is valid.
- Units are immutable values. They carry no key, owner or reference in v1.
- No inheritance, cut, change, resolution or truth evaluation in v1. The
  blueprint publishes authored units; consumers compose.

## Authoring attachments

`semantics=` is accepted on:

- `AssetOptions` — declaration fragment (profile is separate).
- `TableOptions`, `ProjectionOptions`, `StructOptions`.
- `field(...)` and `computed_field(...)`.
- `NodeOptions`, `EdgeOptions`, `NodeOptionsTemplate`,
  `EdgeOptionsTemplate`.
- `property(...)`.
- `BindingOptions.semantics`, and directly on `node_binding(...)` and
  `edge_binding(...)` (binding-wide; per-property semantics is deferred).

`TableGroupOptions` does not carry semantics. A table group is a catalog of
tables, not a blueprint part, so it has no DTO path for a semantics fragment.

Graph:

```python
class OpenTargetsGraph(Graph):
    options = GraphOptions(
        name="open_targets",
        description="...",
        semantics=GraphSemantics(
            claims=(Claim("..."),),
            purpose=Purpose(
                text="...",
                frames=(
                    Frame(
                        text="...",
                        limitations=(Limitation("..."),),
                    ),
                ),
            ),
        ),
    )
```

Exactly one `Graph` declaration is allowed per namespace. Zero is allowed for
projects that have not adopted the language. More than one is an error at
discovery.

## DTOs

New package `distribution/languages/semantics`:

```
ClaimDTO(text)
LimitationDTO(text)
FrameDTO(text, limitations)
PurposeDTO(text, frames)
SemanticsDTO(claims, frames)
GraphSemanticsDTO(claims, *, purpose)
```

New package `distribution/languages/graph`:

```
GraphDeclarationDTO(name, description, semantics: GraphSemanticsDTO)
```

`GraphBlueprint` gains `graph_declaration: GraphDeclarationDTO | None = None`.
The topology part keeps the name `graph`.

Service helpers exported from each package's `service.internal`:

```text
semantics.service.internal
    semantics_to_dto, graph_semantics_to_dto
    semantics_to_document, semantics_from_document
    graph_semantics_to_document, graph_semantics_from_document
    render_semantics, render_semantics_expression, render_graph_semantics

graph.service.internal
    GraphLanguage
    graph_declaration_to_document, graph_declaration_from_document
    render_graph_declaration_source
```

Document shapes (canonical, omit an absent optional member):

```json
{
  "claims": [{"text": "..."}],
  "frames": [
    {"text": "...", "limitations": [{"text": "..."}]}
  ]
}
```

```json
{
  "claims": [{"text": "..."}],
  "purpose": {
    "text": "...",
    "frames": [
      {"text": "...", "limitations": [{"text": "..."}]}
    ]
  }
}
```

An absent `claims`, `frames` or `limitations` member denotes an empty tuple.
`purpose` is always present in a graph semantics document. The blueprint
document gains `"graph_declaration"` when present. Semantics on a declaration is
encoded as `"semantics"` in that declaration's document when present.

## Attachment DTO changes

- `AssetDTO.profile: AssetProfileDTO`, `AssetDTO.semantics: SemanticsDTO | None`
- `ColumnDTO.semantics`, `StructDTO.semantics`, `RelationDTO.semantics`,
  `ProjectionDTO.semantics`
- `NodeDTO.semantics`, `EdgeDTO.semantics`, `PropertyDTO.semantics`
- `NodeBindingDTO.semantics`, `EdgeBindingDTO.semantics`

All optional fields default to `None` so existing construction and documents
remain accepted. Codecs omit `None`.

## Integration

- `ORDER = ("expressions", "asset", "data", "topology", "binding", "graph")`.
  `graph` is optional; the other five are required.
- `DEFAULT_LANGUAGES` and `_default_languages()` append `GraphLanguage()`.
- Default roots include every language. The graph declaration is included when
  present; a narrower root set may omit it.
- Assembly and codec carry `graph_declaration` when present.
- `blueprint_to_source` renders the graph declaration first, then assets,
  topology, data and bindings. Each layer renders its own `semantics=`.
- Validation rejects a graph declaration without `GraphSemantics` purpose.
- A declaration attachment rejects `GraphSemantics`; only the graph declaration
  carries the meaning root.
- Source rendering is mandatory: `blueprint -> source -> blueprint` preserves
  units. Use one shared renderer from the semantics language.

## Acceptance tests

1. Units validate types, non-empty text and nesting.
2. `Semantics` rejects a purpose; `GraphSemantics` requires a keyword-only one.
3. A graph declaration is discovered once; two declarations raise; zero is
   allowed.
4. Blueprint with a graph declaration and semantics on asset, table, struct,
   projection, field, node, edge, property and binding encodes and decodes
   identically.
5. Blueprint source round-trip preserves every semantics value.
6. Attachments on a declaration without semantics produce no `semantics` member.
7. A `Graph` with no purpose is rejected.
8. `AssetProfile` replaces `AssetSemantics`; asset documents use `profile` and
   may carry a separate `semantics`.
9. `TableGroupOptions` has no semantics field and produces no DTO path.
10. `semantics_to_dto` and `graph_semantics_to_dto` are the transcription helpers
    the attaching languages call.

## Open Targets migration

- Add one `OpenTargetsGraph` declaration with a purpose and frames.
- Replace the project's annotation-based `Semantics` with the framework
  language. The project may keep a local builder that maps its richer fields:
  - claims: definition, identity, reading, old claims
  - frame: the declaration's reading scope (or a named default frame)
  - limitations: absence, limits, old refusals
  - sources: retained as source claims or dropped; document the choice.
- Move `Semantics(...)` out of `annotations=(...)` into `semantics=...` at the
  declaration or property. Non-semantics annotations stay.
- The project must compile, generate a blueprint and pass its tests.

## Out of scope

Inheritance, cut, change, revisions, viewer, decisions, approval, semantic
catalogue rendering. The Open Targets semantics JSON/HTML catalogue can keep
reading the old annotation fields until a follow-up migrates it to the new DTO.
