# Detail content contract

Every item detail document is one application. A kind adds content, not chrome:
the header, the section grammar, the identity strip, the meaning renderer, the
member table and the empty state are shared.

The skin is in `DESIGN_BLENDER.md`; the ladder is in `DESIGN_LANGUAGE.md`; the
routes and owners are in `HIERARCHY.md`.

## The section registry

The tab banner carries the overview. The registry below starts at the first
card; each kind orders the cards it includes by their immediate importance to
a reader and never renames one. Every card is static: all content is open, and
the index rail is the only navigation between cards.

| Order | Section | Question it answers | Content |
| --- | --- | --- | --- |
| 1 | **Meaning** | What is this for, and what does it exclude? | Purpose as the lead, then two labelled readings: contextless claims and the limitations that bound the purpose. Each group states its own count; the groups stack when the card is narrow. Legacy readings follow under **Earlier reading**. |
| 2 | **Constitution** | What does this subject assert, and how is it fulfilled? | One DAG on a pan/zoom canvas: Purpose and one Fulfilment per binding are the top consumers, the graph ancestry hangs below Purpose and the relation provenance below the bindings. Each declaration is one node and each edge points from the supply to the consumer; shared relations and assets appear once with one edge per consumer. The separator begins below the fulfilment row and divides the two subgraphs. The GRAPH and RELATION labels sit below their subgraphs. Each node clamps its purpose to two lines; hovering or focusing it reveals the full meaning, selecting it dims the rest, and its label opens its document. Each Fulfilment node states its binding's display name and purpose; identity fields and coverage stay in the binding detail. The graph subgraph groups records as the first record and `+N`; the relation provenance never groups. |
| 3 | **Members** | Which units belong to this subject? | One table grammar: name, type, meaning, source, count; the instance pill opens its document when one exists. |
| 4 | **Connections** | Which records does this subject touch? | Endpoints of an edge, incident relations of a node, ports of a step. |
| 5 | **Bindings** | Which binding fulfils this subject? | One row per binding: name, writes, identity, rows read. The binding pill opens the binding document. |

A card title sits above the card body at its top-left: the card's concept mark
and structural title, never a banner bar or a card surface. The question in the reader's
language becomes the card's accessible label, not a visible line, and the
header carries no count: the body owns the items it shows. Every card gets a
logo; the title-to-concept mapping lives once beside `DetailBand`.

A detail document has a left index rail. It lists every top-level card in
reading order and scrolls to a card when its row is chosen; it does not follow
the scroll position. It is hidden when the pane is narrower than the rail plus
one readable card. The rail reads the rendered cards, so a card added by any
kind appears in it without a second section list.

A binding is its own document. Its sections are **Meaning**, **Expression** and
**Build steps**. The binding banner states the record, writes, identity, rows
read, step and output. A record detail does not repeat the traversal; its
Bindings table and the Constitution's binding node open the binding document.

## Per-kind registry

| View kind | Sections | Notes |
| --- | --- | --- |
| Node | **Meaning**, **Constitution**, **Members**, **Connections**, **Bindings** | Members are properties; Connections are incident relations. |
| Edge | **Meaning**, **Constitution**, **Members**, **Connections**, **Bindings** | The banner states the endpoints; Connections repeats them with the edge. |
| Property | **Meaning**, **Constitution**, **Branches**, **Connections**, **Bindings** | Branches is the type/presence chain and lane canvas; Connections is its ledger. |
| Abstract category | **Meaning**, **Constitution**, **Members** | Members are concrete descendants. |
| Asset | **Meaning**, **Constitution**, **Members**, **Fields**, **Bindings** | The banner states the layout and location; Members are relations, then fields. |
| Source relation | **Meaning**, **Constitution**, **Members**, **Bindings** | Columns are the relation; the banner states the asset and row source. The Meaning card is omitted when the declaration states no units; the Constitution root and relation box state the absence explicitly. |
| Derived relation | **Meaning**, **Constitution**, **Members**, **Bindings** | Members are its columns; the banner states the row source. |
| Binding | **Meaning**, **Expression**, **Build steps** | One binding's identity and property expressions, then its workflow neighbourhood. |
| Step | **Ports**, **Payload**, **Connections**, **Bindings**, Meaning, Sources | A step is build machinery; Meaning and Sources state their absence last. |

Text in bold is the first card the reader meets; every card in the row is
present and open, in that order.

A field is not a document kind; it belongs to its owner's Members table. A
binding is a document kind and also appears in its record's Bindings table and
the Constitution's binding node.

## The binding document carries the traversal

The record detail is read for meaning, constitution and membership. The binding
document is the one place for the computation and the plan:

| Section | Strict meaning | Visualisation |
| --- | --- | --- |
| **Expression** | the field and operator chain the binding writes | the indented expression outline: identity, source and target identity, then each property expression |
| **Build steps** | the plan that executes the binding | the binding step and the workflow neighbours it reads from and writes to |

Sources is not a record card. The binding banner states the rows read; the
expression tree names the source assets and relations behind each field. The UI
never uses the labels "Provenance" or "Lineage"; the model keeps those words.
The section titles state the question.

## The constitution

The Constitution card draws one subject as a DAG on the shared graph canvas:
the purpose and one fulfilment per binding are the top consumers, the graph
ancestry hangs below the purpose and the relation provenance below the
bindings, and every edge points from the supply to the consumer. A declaration
is one node: a source relation or asset shared by several consumers appears once
and carries one edge per consumer. The axes are parallel lanes, not a Cartesian
plot.

- **Purpose** is the record axis's top node: the current subject's purpose, the
  use the binding answers. A record subject lists its ancestry below it; a
  relation or asset subject lists the records it fulfils. The graph purpose is
  the bottom node of the ancestry, not the top, so the current item leads the
  reading.
- **Graph** is the record axis below Purpose: each node supplies the one above
  it, from the current subject's immediate parent down to the graph purpose. A
  grouped record keeps the first record and `+N`; the node states its own
  purpose and the root purpose is marked current.
- **Relation** is the relation provenance below the bindings. Every relation a
  binding reads is a node; each derived relation's scanned relations and each
  source relation's asset are nodes below it. A shared declaration is one node
  with one edge per consumer; nothing is grouped or hidden. The relation root
  supplies its binding. The current declaration is marked when the subject is a
  relation or asset.
- **Fulfilment** is one node per binding, in a row to the right of Purpose;
  each binding→purpose edge enters Purpose's right edge. A binding is not part
  of either axis: the relations it reads supply it, and it answers the purpose.
  Each node states the binding's display name and purpose; identity fields and
  coverage stay in the binding document. The dashed separator begins below the
  fulfilment row and divides the two subgraphs. The graph asserts, the
  relations supply, and each binding states its own meeting; a binding is never
  the parent of either axis.
- The graph subgraph groups many records as the first record and `+N`. The
  relation provenance never groups: every relation, scanned relation and asset
  is a node.

The card never invents a purpose, a relation or a binding. When a declaration
states no meaning, the node says so; when no binding meets the two axes, the
card says so. The canvas pans and zooms; hovering or focusing a node
reveals its full meaning, selecting one dims every other node and keeps its
incident edges, and a node label opens its document. The node itself is
inspection only.

## One grammar per concept

| Concept | One renderer |
| --- | --- |
| Header | concept mark, kicker, title, subtitle, licence. Titles read `Kind · name` for graph subjects and the relation name for data subjects. |
| Identity | one fact grid. A fact is a label and a value; an absent value is stated as absent, not dressed as a value. |
| Meaning | one renderer for the subject and for attached units. The label is always **Meaning**. |
| Members | one table: name, type, meaning, source, count. The instance pill opens its document when one exists. |
| Counts | a count sits beside the noun or the label that names its list: `2 bindings`, `Claims 3`. A standalone count is noun-bearing and correctly pluralised. |
| Empty state | one inline sentence inside the section. The only whole-document empty state is a document with no content at all. |
| Licence | the effective licence in the header; a step states that it has none because it owns no data. |

## Layout

- A document is a horizontal deck of flat section cards. Each card fills
  the available body height and is narrower than the deck so the next card's
  edge stays visible as the cue for more content. Cards are separated by the
  group spacing and have no border or background. Every card is rendered by the
  one shared `DetailBand` feature primitive; a detail view does not declare its
  own card markup or surface.
- The banner and the left index are static. The deck scrolls horizontally; each
  card body scrolls vertically.
- The card title sits above the body at the top-left, in the heading role. The
  body starts below it with the region gap and is inset from the title's left
  edge by the page role, so the title reads as a label rather than the first
  content line. A flush body is used for a canvas or a table that owns its own
  padding.
- A table shares one `grid-template-columns` between its head and every row.
- At narrow width the Meaning readings stack into one column, the Constitution
  canvas pans and zooms, the index rail hides, and nothing overflows
  horizontally.
