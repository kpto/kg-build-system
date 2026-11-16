# Detail content contract

Every item detail document is one application. A kind adds content, not chrome:
the header, the section grammar, the identity strip, the meaning renderer, the
member table and the empty state are shared.

The skin is in `DESIGN_BLENDER.md`; the ladder is in `DESIGN_LANGUAGE.md`; the
routes and owners are in `HIERARCHY.md`.

## The section registry

A detail document renders these sections in this order. A kind includes or
omits a section; it never renames one for itself.

| Order | Section | Question it answers | Content |
| --- | --- | --- | --- |
| 1 | **Overview** | What is this, in one screen? | One fact grid: kind, labels, identity, owner or endpoints, counts and licence. |
| 2 | **Meaning** | What is this for, and what does it exclude? | One renderer: purpose, the limitations it owns, then contextless claims. Attached units follow under one "Attached meaning" sub-label. |
| 3 | **Fulfilment** | How do the record and relation axes meet? | The axis map: graph records, the binding, the domain relations. Compact by default; one control reveals the full three-column map. |
| 4 | **Sources** | Where does this value come from? | Assets, source relations and derived relations, as navigable references with counts. |
| 5 | **Build steps** | How is this built? | The narrowed workflow graph of the steps that produce the subject. |
| 6 | **Expression** | Which fields and operations produce the value? | The expression outline, one root per binding or column. |
| 7 | **Members** | Which units belong to this subject? | One table grammar: name, type, meaning, source, count; a row opens its document when it has one. |
| 8 | **Connections** | Which records does this subject touch? | Endpoints of an edge, incident relations of a node, ports of a step. |
| 9 | **Bindings** | Which binding fulfils this subject? | One row per binding: name, writes, identity, rows read. |

A section header carries three things only: the structural title, the question
in the reader's language, and one noun-bearing count.

## Per-kind registry

| View kind | Sections | Notes |
| --- | --- | --- |
| Node | Overview, Meaning, Fulfilment, Sources, Build steps, Expression, Members, Connections, Bindings | Members are properties; Connections are incident relations. |
| Edge | Same as node | Overview states the endpoints; Connections repeats them with the label. |
| Property | Overview, Meaning, Fulfilment, Sources, Build steps, Expression, Branches, Connections, Bindings | **Branches** is the branch toolbar, type/presence chain and lane canvas. Connections is the branch's connection ledger. |
| Abstract category | Overview, Meaning, Fulfilment, Members | Members are concrete descendants; a row opens the record document. |
| Asset | Overview, Meaning, Fulfilment, Sources, Members, Bindings | Members are source relations and derived relations, then fields. Sources states the release boundary. |
| Source relation | Overview, Meaning, Fulfilment, Sources, Build steps, Expression, Members, Bindings | Expression states that a source relation has no computed expression. |
| Derived relation | Overview, Meaning, Fulfilment, Sources, Build steps, Expression, Members, Bindings | Expression holds one outline per output column. |
| Step | Overview, Meaning, Sources, Ports, Payload, Connections, Bindings | Meaning and Sources state the absence: a step is build machinery and has no release source. |

`field` and `binding` are not document kinds. A field belongs to its owner's
Members table; a binding belongs to its record's Bindings table and to the
Fulfilment map.

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

## The fulfilment map

The map is one renderer. Left is the record axis, right is the relation axis,
and the centre is the binding that fulfils one with the other.

- **Compact** (default) is one row per fulfilment for a record, and one row per
  relation above twelve fulfilments. A row reads `record ← binding → relation`.
- **Full axis map** is three columns: `GRAPH · records`, `FULFILMENT`,
  `RELATIONS · domain`. Every card states the facts the declaration owns:
  identity, grain, coverage, and the meaning count or its absence.
- A card is clickable whenever it has a document.
- The selected record or relation is highlighted; the map never moves a
  settled graph node.

The viewer reads a snapshot that predates relation contracts. When the
snapshot carries no contract or meaning, the map says so; it does not invent a
purpose, a grain or an identity.

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

- A document is a stack of full-width bands separated by 1px rules. No band is
  a floating card and no band has a drop shadow.
- The header is sticky; the bands scroll.
- The band body is 8px above and 10px below its content; a flush body is used
  for a canvas or a table that owns its own padding.
- A table shares one `grid-template-columns` between its head and every row.
- At narrow width the Sources groups stack and the full axis map becomes one
  column; nothing overflows horizontally.
