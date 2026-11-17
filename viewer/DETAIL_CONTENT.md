# Detail content contract

Every item detail document is one application. A kind adds content, not chrome:
the header, the section grammar, the identity strip, the meaning renderer, the
member table and the empty state are shared.

The skin is in `DESIGN_BLENDER.md`; the ladder is in `DESIGN_LANGUAGE.md`; the
routes and owners are in `HIERARCHY.md`.

## The section registry

The registry order is the shared default. Each kind reorders the sections it
includes by their immediate importance to a reader; it never renames one. A
**primary** card opens by default, a **secondary** card starts collapsed.

| Order | Section | Question it answers | Content |
| --- | --- | --- | --- |
| 1 | **Overview** | What is this, in one screen? | One fact grid: kind, labels, identity, owner or endpoints, counts and licence. |
| 2 | **Constitution** | What does this subject assert, and how is it fulfilled? | One wide purpose at the top; the Graph chain on the left and the Relation chain on the right. The Fulfilment box sits directly under the purpose, the relation under it, and the relation's provenance branches below. Arrows point up to the level each box is accountable to. The dashed centre is the axis divide, not a binding. Each box clamps its purpose to two lines; hovering or focusing it reveals the full meaning, and a box label opens its document. The Fulfilment box states the binding count, identity fields and coverage. A grouped branch shows the first item and `+N`; one control expands the full axis map. |
| 3 | **Meaning** | What is this for, and what does it exclude? | The full meaning of the current subject: purpose, the limitations it owns, then contextless claims; compact counts in the header. |
| 4 | **Sources** | Where does this value come from? | Assets, source relations and derived relations, as navigable references with counts. |
| 5 | **Build steps** | How is this built? | The narrowed workflow graph of the steps that produce the subject. |
| 6 | **Expression** | Which fields and operations produce the value? | The expression outline, one root per binding or column. |
| 7 | **Members** | Which units belong to this subject? | One table grammar: name, type, meaning, source, count; a row opens its document when it has one. |
| 8 | **Connections** | Which records does this subject touch? | Endpoints of an edge, incident relations of a node, ports of a step. |
| 9 | **Bindings** | Which binding fulfils this subject? | One row per binding: name, writes, identity, rows read. |

A section header carries four things only: the section's concept logo, the
structural title, the question in the reader's language, and one noun-bearing
count. Every card gets a logo; the title-to-concept mapping lives once beside
`DetailBand`.

## Per-kind registry

| View kind | Sections | Notes |
| --- | --- | --- |
| Node | **Overview**, **Constitution**, **Meaning**, **Members**, **Connections**, Sources, Build steps, Expression, Bindings | Members are properties; Connections are incident relations. |
| Edge | **Overview**, **Constitution**, **Meaning**, **Members**, **Connections**, Sources, Build steps, Expression, Bindings | Overview states the endpoints; Connections repeats them with the label. |
| Property | **Overview**, **Constitution**, **Meaning**, **Branches**, **Connections**, **Expression**, Sources, Build steps, Bindings | Branches is the type/presence chain and lane canvas; Connections is its ledger. |
| Abstract category | **Overview**, **Constitution**, **Meaning**, **Members** | Members are concrete descendants. |
| Asset | **Overview**, **Constitution**, **Meaning**, **Sources**, **Members**, **Fields**, Bindings | Sources states the release boundary; Members are relations, then fields. |
| Source relation | **Overview**, **Constitution**, **Meaning**, **Members**, **Sources**, Build steps, Bindings, Expression | Columns are the relation; Sources states its asset and scans. The Meaning card is omitted when the declaration states no units; the Constitution root and relation box state the absence explicitly. |
| Derived relation | **Overview**, **Constitution**, **Meaning**, **Expression**, **Members**, Sources, Build steps, Bindings | Expression is the computation; Members are its outputs. |
| Step | **Overview**, **Ports**, **Payload**, **Connections**, **Bindings**, Meaning, Sources | A step is build machinery; Meaning and Sources state their absence last. |

Text in bold is primary and opens by default; the remaining cards are secondary
and start collapsed. The card's `data-priority` attribute records the class.

`field` and `binding` are not document kinds. A field belongs to its owner's
Members table; a binding belongs to its record's Bindings table and to the
Constitution's fulfilment box.

## Provenance and lineage are two visualisations

Both answer "where did this come from?", so the reader is given two distinct
questions rather than one word used twice:

| Section | Strict meaning | Visualisation |
| --- | --- | --- |
| **Sources** | the release data the value is read from | asset, source relation and derived relation references |
| **Build steps** | the plan that computes the value | the narrowed workflow graph |
| **Expression** | the field and operator chain of one value | the indented expression outline |

The UI never labels a section "Provenance" or "Lineage". "Provenance" remains
the model term for the sources traversal; "lineage" remains the model term for
the derivation. The section titles state the question.

## The constitution

The Constitution card reads one subject as two axes under one purpose. It is a
tree, not a Cartesian plot: the purpose is the root, the graph and relation
branches descend from it, and each box points up to the level it is accountable
to.

- **Purpose** is the wide root: the graph purpose. A record subject walks its
  record axis below it; a relation or asset subject lists the records it
  fulfils. A relation's own purpose stays on the relation box and is not
  promoted into the root, because a relation purpose is a peer of the graph
  purpose, not a narrowing of it.
- **Graph** is the record axis: category → component → property, ordered from
  the broadest level to the current subject. Each box states its own purpose;
  the current box is tinted and marked.
- **Relation** is the relation axis. The Fulfilment box sits directly under the
  purpose; the relation sits under the Fulfilment box; the relation's
  provenance branches sit under the relation. A derived relation splits into
  its scanned source relation and its asset; a source relation shows its asset.
  The current declaration is marked when the subject is a relation or asset.
- **Fulfilment** is a box on the relation side, not the dashed centre. It
  states the binding count, identity fields and coverage. The dashed centre is
  the axis divide. The graph asserts, the relation supplies, and the
  Fulfilment box states their meeting.
- A branch with many records, relations or assets shows the first item and
  `+N`, so the card stays compact. **Full axis map** expands the same data into
  the three-column records / fulfilment / relations view.

The card never invents a purpose, a relation or a binding. When a declaration
states no meaning, the box says so; when no binding meets the two axes, the
Fulfilment box says so. Hovering a box reveals its full meaning; clicking a box
label opens that level's document. The box itself is inspection only.

## One grammar per concept

| Concept | One renderer |
| --- | --- |
| Header | concept mark, kicker, title, subtitle, licence. Titles read `Kind · name` for graph subjects and the relation name for data subjects. |
| Identity | one fact grid. A fact is a label and a value; an absent value is stated as absent, not dressed as a value. |
| Meaning | one renderer for the subject and for attached units. The label is always **Meaning**. |
| Members | one table: name, type, meaning, source, count. The row opens its document when one exists. |
| Counts | always noun-bearing and correctly pluralised: `1 binding`, `2 bindings`, `9 properties`. |
| Empty state | one inline sentence inside the section. The only whole-document empty state is a document with no content at all. |
| Licence | the effective licence in the header; a step states that it has none because it owns no data. |

## Layout

- A document is a stack of section cards inset 12px from the document edge and
  separated by 8px. Each card has a 1px outline, a 3px radius and no drop
  shadow. Every card is rendered by the one shared `DetailBand` frame; a detail
  view does not declare its own card markup or surface.
- The header is sticky; the cards scroll.
- The section body is 8px above and 10px below its content; a flush body is
  used for a canvas or a table that owns its own padding.
- A table shares one `grid-template-columns` between its head and every row.
- At narrow width the Sources groups stack and the full axis map becomes one
  column; nothing overflows horizontally.
