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
| 2 | **Constitution** | What is this subject for, and how does it come to be? | One layered DAG on a pan/zoom canvas. A record shows its purpose at the root, its graph ancestry in the GRAPH frame on the left, one box per binding in the FULFILMENT frame, and each binding's relation provenance in the RELATION frame on the right; there is no separator. A source relation shows its Purpose over its asset; a derived relation its Purpose over the source relations it scans and their assets; a binding its Purpose over the target record's purpose and identity and the relations it reads. An asset has no Constitution card: it is the origin. Every edge points from the supply to the consumer; a shared declaration is one node with one edge per consumer; ranks, ordering and edge routes are computed; the purpose box carries the subject's own concept mark. Each node clamps its purpose to two lines; hovering or focusing it reveals the full meaning, selecting it dims the rest, and its label opens its document. |
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

A binding is its own document. Its sections are **Meaning**, **Constitution**,
**Expression** and **Build steps**. The binding banner states the record,
writes, identity, rows read, step and output. A record detail does not repeat
the traversal; its Bindings table and the Constitution's binding node open the
binding document.

## Per-kind registry

| View kind | Sections | Notes |
| --- | --- | --- |
| Node | **Meaning**, **Constitution**, **Members**, **Connections**, **Bindings** | Members are properties; Connections are incident relations. |
| Edge | **Meaning**, **Constitution**, **Members**, **Connections**, **Bindings** | The banner states the endpoints; Connections repeats them with the edge. |
| Property | **Meaning**, **Constitution**, **Branches**, **Connections**, **Bindings** | Branches is the type/presence chain and lane canvas; Connections is its ledger. |
| Abstract category | **Meaning**, **Constitution**, **Members** | Members are concrete descendants. |
| Asset | **Meaning**, **Members**, **Fields**, **Bindings** | The banner states the layout and location; Members are relations, then fields. An asset is the origin, so it has no Constitution card. |
| Source relation | **Meaning**, **Constitution**, **Members**, **Bindings** | Columns are the relation; the banner states the asset and row source. The Constitution is the relation's purpose over its asset alone: a source relation is not fulfilled by a binding and has no graph axis. |
| Derived relation | **Meaning**, **Constitution**, **Members**, **Bindings** | Members are its columns; the banner states the row source. The Constitution is its purpose over the source relations it scans and their assets. |
| Binding | **Meaning**, **Constitution**, **Expression**, **Build steps** | The Constitution is the binding's purpose over the target record (purpose and identity only) and the relations it reads; Expression and Build steps carry the computation and the plan. |
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
| **Constitution** | how the binding comes to be | its purpose over the target record's purpose and identity, and the relations it reads with their provenance |
| **Build steps** | the plan that executes the binding | the binding step and the workflow neighbours it reads from and writes to |

Sources is not a record card. The binding banner states the rows read; the
expression tree names the source assets and relations behind each field. The UI
never uses the labels "Provenance" or "Lineage"; the model keeps those words.
The section titles state the question.

## The constitution

A constitution states how one subject comes to be. The subject's purpose is the
top node, the declarations that produce it hang below, and every edge points
from the supply to the consumer. The purpose box carries the subject's own
concept mark, never the graph mark, and each box background is a tint of its
own concept colour. The concept pill is the box header: it uses the title role
and sits one stack gap above the purpose, closer than the box padding, so the
header and its body read as one group while the rank gap separates boxes. The
card is one layered DAG: a declaration shared by several consumers is one node
with one edge per consumer, ranks, ordering and edge routes are computed, and
nothing is grouped or hidden.

| Subject | How it comes to be | The card |
| --- | --- | --- |
| Node, edge, property, abstract category | its bindings, each meeting a relation at a grain and identity; the graph states what it is and where it sits | One DAG: the purpose at the root, the graph ancestry in the GRAPH frame, one box per binding in the FULFILMENT frame, and each binding's relation provenance in the RELATION frame |
| Source relation | its asset | Purpose over its asset alone; no bindings, no graph axis |
| Derived relation | the source relations it scans, each from its asset | Purpose over those source relations and their assets; no bindings, no graph axis |
| Binding | the meeting of a record and a relation | Purpose over the target record (purpose and identity only) and the relations it reads with their provenance |
| Asset | nothing: it is the given source | no Constitution card |
| Step | build machinery, not a semantic declaration | no Constitution card |

The record's graph ancestry belongs to the record's own constitution, not to
its binding's. A binding owns neither side's meaning: its purpose states the
fulfilment, and the target record keeps its purpose and identity; the record's
purpose is not repeated as the binding's parent.

- **Purpose** is the subject's own use, marked current. For a record it is the
  use the bindings answer; for a relation and a binding it is the `Purpose`
  value declared on that subject.
- **Binding** appears only for a record: one box per binding, and the bindings
  together are the fulfilment. They are enclosed by one dashed **FULFILMENT**
  frame whose label sits at its top-left, like a topology category frame. Each
  box states the binding's display name and purpose; identity fields and
  coverage stay in the binding document.
- **Graph** appears only for a record: each node supplies the one above it,
  from the immediate parent down to the graph purpose. It groups many records
  as the first record and `+N`; the relation provenance never groups.
- **Relation** is the subject's components below the purpose: a binding's
  target record and the relations it reads, a source relation's asset, a
  derived relation's scanned relations and their assets. A source relation or
  asset shared by several consumers is one node with one edge per consumer.
- A record is one intact DAG with its purpose at the root, its graph ancestry in
  the GRAPH frame on the left, its bindings in the FULFILMENT frame, and its
  relation provenance in the RELATION frame on the right; there is no
  separator. A binding box is a binding, never the fulfilment itself. A
  relation or binding subject has one production group and no frame.

The card never invents a purpose, a relation or a binding. When a declaration
states no meaning, the node says so; when a record has no binding, the card
says so; when a produced subject has no component, it says that instead. The
canvas opens fitted and pans and zooms; hovering or focusing a node reveals its
full meaning, selecting one dims every other node and keeps its incident edges,
and a node label opens its document. The node itself is inspection only.

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
  canvas opens fitted and pans and zooms, the index rail hides, and nothing
  overflows horizontally.
