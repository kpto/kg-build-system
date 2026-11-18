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
| 1 | **Constitution** | What is this subject for, and how does it come to be? | One layered DAG on a pan/zoom canvas. A record shows the subject and its graph ancestry in the GRAPH frame, one box per binding in the FULFILMENT frame, and each binding's relation provenance in the RELATION frame; there is no separator and the three frames do not overlap. A source relation shows its subject over its asset in the RELATION frame; a derived relation its subject over the source relations it scans and their assets in the RELATION frame; a binding its subject in the FULFILMENT frame and the relations it reads in the RELATION frame, with its target record as the Contribution in the GRAPH frame. An asset has no Constitution card: it is the origin. Every edge points from the supply to the consumer; a shared declaration is one node with one edge per consumer; ranks, ordering and edge routes are computed; the subject box carries the subject's own concept mark. Each node clamps its meaning to two lines; hovering or focusing it reveals the full meaning, selecting it dims the rest, and its label opens its document. |
| 2 | **Meaning** | What is this for, and what does it exclude? | Purpose as the lead, then two labelled readings: contextless claims and the limitations that bound the purpose. Each group states its own count; the groups stack when the card is narrow. Legacy readings follow under **Earlier reading**. |
| 3 | **Members** | Which units belong to this subject? | One table grammar: name, type, meaning, source, count; the instance pill opens its document when one exists. |
| 4 | **Connections** | Which records does this subject touch? | Endpoints of an edge, incident relations of a node, ports of a step. |
| 5 | **Bindings** | Which binding fulfils this subject? | One row per binding: name, writes, identity, rows read. The binding pill opens the binding document. |

A card title sits above the card body at its top-left: the card's concept mark
and structural title, never a banner bar or a card surface. The question in the reader's
language becomes the card's accessible label, not a visible line, and the
header carries no count: the body owns the items it shows. Every card gets a
logo; the title-to-concept mapping lives once beside `DetailBand`.

A detail document has a left index rail and one page margin around the body.
The rail lists every top-level card in reading order and scrolls to a card when
its row is chosen; it does not follow the scroll position. It is hidden when
the pane is narrower than the rail plus one readable card. The rail reads the
rendered cards, so a card added by any kind appears in it without a second
section list. The deck fills the height left by the page margin and reserves
the last card snaps to the deck start.

A binding is its own document. Its sections are **Constitution**,
**Contribution**, **Meaning** (when the binding carries one), **Expression** and
**Build steps**. The binding
banner states the record, writes, identity, rows read, step and output. A record detail does not repeat
the traversal; its Bindings table and the Constitution's binding node open the
binding document.

## Constitution and contribution

A participant detail answers two directions, and only two:

- **Constitution** is the full chain below the subject, back to the asset. A
  record's constitution is its bindings and their relation and asset
  provenance; a relation's is its asset or the relations it scans; a binding's
  is the relations it reads. Graph ancestry is a graph dependency, not a data
  one.
- **Contribution** is only the immediate level above the subject. An asset's
  contribution is its source relations. A source or derived relation's is the
  derived relations that scan it and the bindings that read it directly. A
  binding's is the record it writes. A node's graph contribution is its
  incident edges; an edge's endpoints are constitution. A property's is its
  owning record. An abstract participant's is its immediate children. A step's
  is the steps that read its outputs.

Both directions use the same constitution DAG: the subject's purpose is the
anchor, its constitution hangs below it and its contribution sits above it.
Boxes, frames, computed ranks and routed edges are shared. When a contribution
set is large, it is read at layer resolution: one linked layer box per kind
rather than an unreadable field of boxes.

Pages are named for the direction, never for a level number. A page that lists
two levels up is wrong even when its rows are true.

## Virtual collection documents

Every Explorer row is a document. A layer header's body opens a **collection**;
its arrow, on the left of the row, unfolds or folds the list. The body never
toggles and the arrow never opens the document. A workflow component header behaves the same way: its body
opens the component's collection and its arrow unfolds its steps.

A collection is a layer read as a group, not a declared subject. It carries no
Meaning card: it has no purpose, claim or limitation of its own. Its
Constitution and Contribution pages use the collection's actual items and the
actual participant subjects merged from their constitutions or contributions.
There is no collection root: the boxes are the items themselves plus their
boundary. A large set accepts items until the boundary reaches a readable size
and states how many items are shown; it never shows layer boxes or links to
another collection.

The boxes are ordered in vertical level bands. An asset is below a source
relation, a source relation below a derived relation, a derived relation below
a binding, and a record above a binding. A Constitution puts the collection's
items in the top band; a Contribution puts them in the bottom band.

| Collection page | Scope | Contents |
| --- | --- | --- |
| **Constitution** | the items and the actual participants below them, merged | one box per real item or dependency, shared subjects once, in the collection's frame. Assets have an explicit empty state: they are the origin |
| **Contribution** | the items and the actual participants exactly one level above them | one box per real item or dependant, shared subjects once, never deeper |
| **Items** | the collection itself | the layer's members with layer-specific facts; every row opens the participant document |
| **Coverage** | the collection's completeness | items, items with meaning, items with a constitution, items with a contribution |

A collection's constitution merges the actual dependencies of its items, so a
shared declaration is one box. When the merged set is larger than a readable
page, the card shows a bounded set of actual subjects and states the total.

| Collection | Constitution | Contribution | Items |
| --- | --- | --- | --- |
| Assets | empty: the origin | Source relations | assets |
| Source relations | Assets | Derived relations, Bindings | source relations |
| Derived relations | Assets → Source relations | Derived relations, Bindings | derived relations |
| Bindings | Assets → Source relations → Derived relations | Nodes, Edges | bindings |
| Nodes | Data: Assets → Source relations → Derived relations → Bindings. Graph: Graph → Abstract | Graph: Edges | nodes |
| Edges | Data: the record chain. Graph: Abstract → Nodes | none: endpoints are constitution | edges |
| Abstract | Data: own Bindings. Graph: Graph | Graph: child abstract nodes, Nodes, Edges | abstract nodes and abstract edges |
| Workflow | upstream components | downstream components | component groups |
| Workflow component | upstream components | downstream components | steps |

## Per-kind registry

| View kind | Sections | Notes |
| --- | --- | --- |
| Node | **Constitution**, **Meaning**, **Contribution**, **Members**, **Connections**, **Bindings** | Contribution is the incident edges, one graph level above; Members are properties; Connections are incident relations. |
| Edge | **Constitution**, **Meaning**, **Contribution**, **Members**, **Connections**, **Bindings** | Contribution is empty: an edge has no contribution; its endpoints are constitution. Connections repeats the endpoints with the edge. |
| Property | **Constitution**, **Meaning**, **Contribution**, **Branches**, **Connections**, **Bindings** | Contribution is the owning record; Branches is the type/presence chain and lane canvas; Connections is its ledger. |
| Abstract node | **Constitution**, **Meaning**, **Contribution** | Contribution is the immediate child abstract nodes, nodes and edges, not the whole tree. The Constitution uses the abstract node's own bindings, never its descendants' data. An abstract edge is an edge document and carries the same purple edge mark. |
| Asset | **Meaning**, **Contribution** | The banner states the layout and location; Contribution is the source relations that read the asset. Derived relations are two levels up and are not repeated. The asset is the origin: it has no Constitution, Fields or Bindings page. |
| Source relation | **Constitution**, **Meaning**, **Members**, **Contribution** | Columns are the relation; the banner states the asset and row source. The Constitution is the relation's purpose over its asset alone. Contribution is the derived relations that scan it and the bindings that read it directly; an indirect binding is not one level up. |
| Derived relation | **Constitution**, **Meaning**, **Members**, **Contribution** | Members are its columns; the banner states the row source. The Constitution is its purpose over the source relations it scans and their assets. Contribution is the derived relations that scan it and the bindings that read it directly. |
| Binding | **Constitution**, **Contribution**, **Meaning**, **Expression**, **Build steps** | The Constitution is the binding's purpose over the relations it reads; Contribution is the target record (purpose and identity only). Expression and Build steps carry the computation and the plan. |
| Step | **Constitution**, **Contribution**, **Ports**, **Payload**, **Bindings**, **Meaning**, **Sources** | Constitution is the steps that produce its inputs; Contribution is the steps that read its outputs. A step is build machinery; Meaning and Sources state their absence last. |

Text in bold is the first card the reader meets; every card in the row is
present and open, in that order.

A field is not a document kind; it belongs to its owner's Members table. A
binding is a document kind and also appears in its record's Bindings table and
the Constitution's binding node.

## The binding document carries the traversal

The record detail is read for its constitution, meaning and membership. The binding
document is the one place for the computation and the plan:

| Section | Strict meaning | Visualisation |
| --- | --- | --- |
| **Constitution** | how the binding comes to be | its purpose over the relations it reads with their provenance |
| **Contribution** | which record the binding writes | the target record's purpose and identity, one level above |
| **Meaning** | what the binding fulfils and excludes | the binding's own purpose, claims and limitations, when it carries them |
| **Expression** | the field and operator chain the binding writes | the indented expression outline: identity, source and target identity, then each property expression; an operator node states its published signature when the blueprint carries an operation declaration, otherwise the instance's actual logical type |
| **Build steps** | the plan that executes the binding | the binding step and the workflow neighbours it reads from and writes to |

Sources is not a record card. The binding banner states the rows read; the
expression tree names the source assets and relations behind each field. The UI
never uses the labels "Provenance" or "Lineage"; the model keeps those words.
The section titles state the question.

## The constitution

A constitution states how one subject comes to be. The subject's purpose is the
top node, the declarations that produce it hang below, and every edge points
from the supply to the consumer. The subject box carries the subject's own
concept mark, never the graph mark, and each box background is a tint of its
own concept colour. The concept pill is the box header: it uses the title role
and sits one stack gap above the purpose, closer than the box padding, so the
header and its body read as one group while the rank gap separates boxes. The
card is one layered DAG: a declaration shared by several consumers is one node
with one edge per consumer, ranks, ordering and edge routes are computed, and
nothing is grouped or hidden.

| Subject | How it comes to be | The card |
| --- | --- | --- |
| Node, edge, property, abstract node | its own bindings, each meeting a relation at a grain and identity; the graph states what it is and where it sits | One DAG: the purpose and graph ancestry in the GRAPH frame, one box per binding in the FULFILMENT frame, and each binding's relation provenance in the RELATION frame. An abstract node uses only the bindings that write it, never its descendants' |
| Source relation | its asset | Purpose and asset together in the RELATION frame. No bindings, no graph axis |
| Derived relation | the source relations it scans, each from its asset | Purpose, source relations and their assets together in the RELATION frame. No bindings, no graph axis |
| Binding | the relations it reads | Purpose in the FULFILMENT frame and the relations it reads with their provenance in the RELATION frame. Its target record is its Contribution, in the GRAPH frame |
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
- **Graph** appears for a record as its ancestry, each node supplying the one
  above it from the immediate parent down to the graph purpose. It groups many
  records as the first record and `+N`; the relation provenance never groups.
  For a binding subject the GRAPH frame encloses the target record and has no
  ancestry.
- **Relation** is the subject's relation components: a source relation's asset,
  a derived relation's scanned relations and their assets, and the relations a
  binding reads. A source relation or asset shared by several consumers is one
  node with one edge per consumer.
- The frame kinds are **GRAPH**, **RELATION** and **FULFILMENT**, and every
  box sits inside one of them. A record has the subject and its graph ancestry
  in the GRAPH frame, its bindings in the FULFILMENT frame, and its relation
  provenance in the RELATION frame. A source or derived relation has the
  subject and its asset or scanned sources in one RELATION frame. A binding has
  the subject in the FULFILMENT frame and the relations it reads in the RELATION
  frame; its target record is its Contribution, in the GRAPH frame. A step
  boundary uses the GRAPH frame; a collection layer DAG uses the frame of the
  collection's layer. The subject sits in the GRAPH frame's column for a record,
  and the three frames do not overlap. There is no separator, and a binding box
  is a binding, never the fulfilment itself.

When several arrows meet one box, their heads sit on a centred, evenly spaced
set of points along that edge.

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

- A document is a horizontal deck of flat section cards. When the deck has
  room, one card fills the body height and leaves a readable next-card peek
  whose title is the cue; when it is too narrow for that peek, one card fills
  the deck and the next card is off-screen. Cards are separated by the group
  spacing and have no border or background. Every card is rendered by the
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
