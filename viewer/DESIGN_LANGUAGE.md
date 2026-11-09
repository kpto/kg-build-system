# Viewer design language

The complete visible hierarchy — every window, task, panel, section, row,
field, control and owner — is in `HIERARCHY.md`. This document states the rules
that hierarchy follows.

The viewer is one application, not a collection of screens. Every surface is
built from the same seven levels. Each level answers exactly one question and
owns exactly one kind of chrome. A level may be omitted; it may not be
reordered, duplicated or wrapped in another level of the same kind.

## The ladder

```text
Window        where am I, and what application is this?
  Workspace   what task am I doing?
    Panel     what kind of information is this?
      Section what facet of the subject?
        Row   which item?
          Field  what value?
            Control  what can I do with it?
```

| Level | Concept | Owns | May contain | Never contains |
| --- | --- | --- | --- | --- |
| **Window** | the campaign: dataset, revision and review state | identity, workspace switch, global search/import, global status | workspaces, global overlays | panel content, editor tabs, property fields, graph canvases |
| **Workspace** | the task: orient, diagnose or audit | the arrangement of panels for one task | one to three panels | its own title bar or content |
| **Panel** | the model slice: structure, execution, provenance or evidence | one responsibility, one header, one scroll owner | sections, a canvas, a section rail | another panel with its own header |
| **Section** | the question or claim about that model slice | one facet of the panel subject | rows, fields, a bounded list | panel headers, tabs, nested sections |
| **Row** | the subject under review | one item in a repeated list | fields, badges, row actions | another row, a section |
| **Field** | the evidence for the row's claim | one named value | a copy action | editable controls, nested fields |
| **Control** | the decision or one-level move | one action or one input | an icon and a label | content, headers, containers |

## Level contracts

### Window

The application frame. It answers "what is this and where can I go?".

**Concept:** the campaign — one dataset snapshot, its revision and its aggregate
review state. Every panel is scoped by that campaign; no panel may switch
dataset silently.

- A single 32px header: logo, `Map | Explore | Review`, search, import.
- A single 25px status bar: dataset counts, review progress, score, build mode.
- Global overlays only: search results, import errors, toasts, the shortcut
  sheet.
- No editor tab, view control, property field or panel action belongs here.
  `Workflow | Blueprint | Lineage` are not window tabs.

### Workspace

A named task arrangement. It answers "what am I trying to do?".

**Concept:** the task — orientation (Map), diagnosis (Workflow, Blueprint,
Lineage) or audit (Review). The task decides which model slice is relevant; it
does not add another level of chrome.

- `Map`: a viewport plus a Navigator.
- `Explore`: Outliner, Editor, Properties.
- `Review`: one full-width Editor with a section rail.
- A workspace has no visible body of its own. The active tab in the Window
  header is its only chrome.
- Switching workspace replaces the panel arrangement. It never stacks a second
  layer or opens a second window-like surface.

### Panel

A tiled region with one responsibility and exactly one header. This is the unit
the user reads as a region.

**Concept:** the model slice — topology structure, workflow execution, property
provenance or audit evidence. The header must name the slice; a generic "Editor"
label is only acceptable when the active tab names it.

- Every panel header is 32px: editor-type icon, a sentence-case title, optional
  count/selection, right-aligned panel actions, and (Editor only) view tabs.
- Panels tile edge to edge with 1px separators. No outer margin, no radius, no
  shadow, no floating.
- A panel body has exactly one scroll owner. If two parts need independent
  scroll, they are two panels.
- The Editor panel's tabs select the representation (`Workflow`, `Blueprint`,
  `Lineage`); they do not create new panels.
- A panel may contain a canvas or a stack of sections. It never contains another
  titled region with its own border.

### Section

A facet of the panel's subject. This is the level that was previously drawn as a
"card" and caused the glued-together look.

**Concept:** the question or claim — "which properties define this entity?",
"why is this finding high severity?", "where does this branch enter?". The label
can be short, but the question must be answerable from the section's rows and
fields.

- A section has a band, not a floating label: 28px, sentence-case title, optional
  count, optional disclosure, section actions on the right.
- Sections stack in one column or split in two with a 1px rule. They are flush
  with the panel body.
- A section has no outer border, radius or shadow. Separation is a rule, not a
  card.
- A section body is rows, fields or a bounded list. Nested sections are not
  allowed. A subject that needs its own evidence rows is a **row group**: a
  subject row followed by its evidence rows as siblings, not a nested section
  and not a card.
- Collapsing is a section behaviour. The chevron lives in the section label row;
  the body hides or unmounts; the label row remains.

### Row

The repeated unit of detail: outliner rows, property rows, finding rows,
coverage rows, decision rows, receipt rows, neighbour rows.

**Concept:** the subject under review — a node, edge, property, step, finding or
decision that can become the next scope. If the item cannot be opened,
inspected or decided, it is not a row.

- Two forms, one concept:
  - **compact row** — 20–24px, one line, for navigation and list items;
  - **subject row** — auto height up to about three lines, for a finding,
    decision or entity that carries its own description, evidence and actions.
- A row may contain fields, badges and secondary actions. It never contains
  another row or a section header. A **row group** is a subject row plus its
  evidence rows as siblings (for example a Blueprint entity and its properties);
  it is not a section.
- Clicking the row performs its primary action. Secondary controls stop
  propagation.
- Row selection is contextual: **blue** in navigation and list panels, **orange**
  only in a graph/canvas context.

### Field

One named value.

**Concept:** the evidence for the row's claim — a type, source, expression,
binding index, count or impact. It is read, copied or compared; it is not a
navigation level.

- Label: 10.5px, muted, sentence case.
- Value: 10.5–11px, tabular numerals for counts, mono for ids/SQL/expressions.
- Values sit in an inset cell (2px radius, 1px `line-soft`) or align in a
  two-column grid. Long values truncate with a title.
- Only action: copy. No nested fields, no edit-in-place unless the whole viewer
  becomes editable.

### Control

One action or one input.

**Concept:** the decision or the one-level move — open lineage, trace a step,
acknowledge a finding, waive a rule, pin a baseline. A control that does not
change review state or move exactly one level is presentation, and belongs with
the panel or section it presents.

- 26px tall, flat, 4px radius. Primary is a blue outline/tint, never a
  solid loud pill. Orange is never an ordinary control colour.
- Controls never create their own containers or headers.
- The action lives at the narrowest level that owns it:
  - global action → Window header;
  - view/tab action → Panel header;
  - section action → Section label row;
  - item action → Row;
  - value action → Field.
- One control performs one action. A control that opens a menu owns the menu;
  the menu is an overlay, not a section.

## Meaning before partition

A partition exists only when it can be summed up in **one sentence**. A panel,
section, rail tab or workspace is not a container for related fragments; it is
an answer to one question.

- If the honest label is a list — "Identity, Structure, Expressions, Code,
  Connections" — the partition is an aggregation of fragments. Re-cut it by the
  question each fragment helps answer.
- If the honest summary is "a bit of everything", the partition is not a
  partition. Split it or merge it into the level that owns the question.
- A label names the **meaning**, not the data type. "Production" is a meaning;
  "Branches, rows, expressions and source" is a list of fragments.
- The evidence supports the meaning. Counts, badges and fields are not the
  meaning by themselves; they are what lets the answer be checked.
- Two partitions that answer the same question are one partition. One partition
  that answers two unrelated questions is two.

Applied to the Properties editor, the rail becomes:

| Rail | Question it answers |
| --- | --- |
| Definition | What is this? |
| Production | How is it produced? |
| Emission | What does it emit? |
| Dependencies | What depends on it? |
| Context | What else is recorded? |

The rail tab is a question, not a bucket of section names. It **filters** the
panel body: only sections that answer the active question are visible. If a
subject has no section that answers a question, that tab is absent. The panel
header meta states the active question, so the blue icon always has a readable
meaning.

### Coherence with the parent and siblings

A meaning is not enough on its own. Every partition must be:

1. **a refinement of the parent** — the parent question plus one constraint;
2. **one of a set of siblings that partition the parent question** — no
   overlap, no orphan topic;
3. **readable as one sentence** with its parent and siblings.

The test is a sentence:

> To answer *parent question*, I need to know *sibling 1*, *sibling 2*, …

| Parent question | Sibling meanings |
| --- | --- |
| Properties: which evidence defines this subject? | Definition (what is it?), Production (how is it produced?), Emission (what does it emit?), Dependencies (what depends on it?), Context (what else is recorded?) |
| Review: is the model trustworthy, and what do we do? | Summary (the verdict), Findings (what is wrong?), Questions (what is unresolved?), Coverage (what is untested?), Decisions (what did we decide?), Build (did it publish?), Diff (what changed?), Dossier (what do we hand over?) |
| Map: what exists and how is it connected? | Selection (what is selected?), Groups (what groups exist?), Properties (what defines it?), Neighbours (what is it connected to?) |
| Explore / Blueprint: what does this semantic group mean? | Group (which entities belong here?), Entity (what is this entity?), Property (what is this property?), Source (where is it declared?) |

If a sibling does not fit the sentence, it belongs to another parent. If two
siblings produce the same clause, they are one partition. If a sibling is a list
of data types, it has not found its meaning yet.

The old Properties rail failed this test: "Identity, Structure, Expressions,
Code, Connections" is a list of fragments, and "Structure" contained branches,
rows, fields, layout, properties and artifacts — several different questions in
one tab. It was re-cut by meaning, not by section name.

## Conceptual flow

The ladder is not only containment. It is a chain of meaning:

```text
Campaign    the dataset and review state I am responsible for
  Task      the kind of question I am asking of it
    Model   the slice of the graph that can answer it
      Question  the claim I am testing or explaining
        Subject  the thing under review
          Evidence  the facts that support or contradict it
            Decision  what I do about it
```

Structural and conceptual containment must agree. A panel labelled only
"Editor" tells the user where they are but not which model slice they are in;
"Blueprint" or "Lineage" does. A section labelled only "ASSOCIATION" names a
group, not a question; its subtitle or accessible name must state what it
answers, for example "which properties define the association edges?".

### Downward: narrowing the question

Each descent does four things:

1. inherits the parent scope — dataset, task and current subject;
2. adds exactly one constraint — a representation, group, entity, property or
   branch;
3. removes evidence that cannot answer the narrowed question;
4. offers one next action at this level.

No level repeats the parent's context. It only narrows it. Detail is earned: a
row shows the fields needed for its claim, not every field the model carries.

### Upward: returning a result

Going back does not reset to a blank page. Each level returns:

- the selected subject, so the parent can highlight it;
- the review-state change, if any — acknowledged, waived, decided, pinned;
- the evidence inspected, so the parent can show coverage or a reviewed mark;
- a summary that the parent aggregates.

This is why `target.approvedSymbol` survives Map → Blueprint → Lineage →
Review: it is the same **Subject** seen through a deeper **Model** slice, not a
new page.

### The scope stack

There is one active scope stack per workspace:

```text
dataset
  representation      Map | Workflow | Blueprint | Lineage | Review
    group             parent group / lane / finding group
      subject         node, edge, property, step, finding, decision
        evidence      binding branch, expression, source, impact
          action      open, acknowledge, waive, decide, pin
```

The top of the stack is the selected thing. Panel headers and active tabs show
the stack without a second breadcrumb. Back pops one level and restores the
previous selection; forward repeats it. Switching representation keeps the
subject, swaps the model slice, and resets only the levels below the subject.

### Workspace flows

**Map — orientation.** Campaign → topology task → topology model → parent group
→ entity → relationship/property → open in Explore. The Map answers "what
exists and how is it connected?". "How is this value produced?" belongs to
Lineage, and the subject is handed over, not re-selected.

**Explore / Workflow — execution.** Campaign → execution task → workflow model
→ component/emitter group → step → instruction/artifact → trace or review. The
question is "what ran, in what order, and what does this step consume and
produce?".

**Explore / Blueprint — semantics.** Campaign → semantic task → blueprint model
→ parent group → entity → property → source/expression → open lineage or
review. The question is "what does this node or edge mean, and what defines
it?".

**Explore / Lineage — provenance.** Campaign → provenance task → lineage model
→ lane → binding branch → source/expression/impact → review decision. The
question is "where does this value come from, and what changes if this branch
changes?".

**Review — audit.** Campaign → audit task → rubric/evidence model → rubric
component or queue group → finding/decision → evidence/impact → acknowledge,
waive or decide. The question is "is this model trustworthy, and what do we do
about this finding?".

### Conceptual map

The same ladder, read as questions:

| Workspace | Task question | Model slice | Section question | Subject | Evidence | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Map | What exists and how is it connected? | topology | Which group, entity or relationship? | entity | degree, group, properties | open in Explore, review |
| Workflow | What ran, in what order, and what does it consume/produce? | execution | Which component or emitter group? | step | instruction, artifacts, connections | trace, review |
| Blueprint | What does this model mean, and what defines it? | semantics | Which parent group or entity? | node/edge | description, properties, source | open lineage, review |
| Lineage | Where does this value come from, and what changes if it changes? | provenance | Which lane or binding branch? | binding branch | source, operator, post, target | review, acknowledge |
| Review | Is this model trustworthy, and what do we do about it? | audit | Which rubric component or queue group? | finding/decision | evidence, impact, coverage | acknowledge, waive, decide |

A section that cannot fill its column in this table is not a section yet.

### Conceptual rules

1. A panel names its **model slice**, not a generic UI role. "Editor" is a
   structural placeholder; the header names the representation or subject
   scope.
2. A section states a **question or claim**, not only a category. A short label
   is allowed; the accessible name carries the question.
3. A row is a **subject that can become the next scope**. If it cannot be
   opened, inspected or decided, it is a field, not a row.
4. A field is **evidence**, not navigation. It may copy; it does not change the
   scope.
5. A control is a **decision or a one-level move**. Global commands live in the
   Window; presentation controls in the Panel header; review-state controls on
   the finding/decision row or its section.
6. The same subject keeps its identity across representations. Selection is a
   property of the subject, not of the panel.
7. Summaries flow up. A row's reviewed state updates the section count, the
   panel count, the workspace score/queue and the Window status. No level
   recomputes its own truth.
8. A level that cannot state its question in one sentence is a structural
   grouping and must be removed or merged.
9. A level may be skipped when it has one child, but the conceptual order cannot
   be reversed. A row never appears directly under a workspace.
10. The flow is bidirectional: the user can always name the parent scope and
    return without losing context.

### Example: `target.approvedSymbol`

```text
Window      dataset 26.09 · compile-only · review 0/428 · score 49
  Task      Explore → Blueprint: what does this model mean?
    Model   topology · entity group
      Scope entity target: what is this node?
        Subject property approvedSymbol: which field defines it?
          Evidence type str · binding 202 · source target.approvedSymbol
            Decision open lineage: where is it produced?
              Model  lineage · binding branch 202
                Evidence source, operator, target, post-processing
                  Decision review the branch or acknowledge a finding
                    ↑ coverage updates, panel count, Window queue and score
```

The user never leaves the campaign. Each step narrows the model slice, returns
evidence upward, and preserves the selected subject.

## Surface and rhythm

Boundaries come from **surface steps and a dark seam**, not from a grid of grey
hairlines. A region is a rounded plate; a section is a rounded band inside it; a
row is a text line with a hover fill.

| Level | Surface | Size | Separation | Radius |
| --- | --- | ---: | --- | ---: |
| Window header | `inset` `#1c1c1c` | 32px | 1px bottom `line-soft` | 0 |
| Window status | `inset` | 28px | 1px top `line-soft` | 0 |
| Region | `panel` `#262626`, canvas `abyss` `#171717` | fills the task | 2px `gutter` `#0c0c0c` between regions | 4 |
| Panel header | `panel-raised` `#313131` | 32px | 1px bottom `line-soft` | 4 top |
| Section | body `#232323`, header `panel-raised` | 28px header, 6px margin | 1px `line-soft` around the band | 4 |
| Row | transparent | 26px | no hairline; hover `#343434` | 3 |
| Field | transparent | 2-column, 4px 10px | none | 0 |
| Control | `panel-soft` / transparent | 26px | 1px `line` | 4 |
| Canvas overlay | `panel` at 96 % + shadow | content-sized | 1px `line-soft` | 4 |

- **Type:** window title 12.5/600; panel title 11.5/600; section title 11/600;
  row label 12/400; row meta 10/400 mono; field label 10.5/500; field value
  11.5/400 mono for identifiers; status 10/400 mono. Sentence case everywhere;
  no uppercase micro labels.
- **Fields:** label column right-aligned, 82–88px, value left-aligned. Evidence
  wraps; it is never truncated to fit.
- **Spacing scale:** 2, 4, 6, 8, 12, 16. No 10/14/20 one-offs.
- **Radius scale:** 3 rows, 4 regions, sections, controls, overlays and cards;
  0 only for full-bleed seams.
- **Shadows:** canvas overlays, menus, popovers and dialogs. Never a region, a
  section or a row.
- **Borders:** a region edge is a surface step plus the 2px gutter. `line-soft`
  marks a band or control; `line` is only for an input or a hovered control;
  `line-strong` is a hover highlight.
- **Colour budget:** blue is active/selected/primary; orange is graph selection;
  semantic colours appear as 6px dots, bars or a single small chart mark, never
  as coloured text chips repeated down a list.

### Reading order

Heading levels follow the information structure, not the desired font size.
At each level the eye lands in this order:

| Level | First | Second | Third |
| --- | --- | --- | --- |
| Window | active workspace | search | status |
| Panel | model-slice title | count/context | primary panel action |
| Section | question/label | count | disclosure or section action |
| Row | subject | evidence/meta | row action |
| Field | label | value | copy |

- One primary action per level. Everything else is visibly weaker and
  right-aligned.
- No two levels compete for the same focal point. The active workspace, the
  selected row and the selected graph item may all exist, but only one is the
  brightest thing on screen at a time.
- The panel title is never the largest type in the body; the content is.

## State grammar

| State | Lists and navigation | Graph and canvas |
| --- | --- | --- |
| Hover | `panel-soft` background, text becomes `text` | blue `accent` stroke/ring |
| Focus-visible | 2px blue outline | 1px blue ring |
| Selected | blue `accent-soft` background + accent text | orange `selection` outline/rail |
| Active/primary | blue outline/tint text | blue frame/control |
| Dimmed | opacity 0.35 | opacity 0.12 for context |
| Disabled | opacity 0.45, no hover | same |

- One selection colour per context. Blue means "this row is current"; orange
  means "this graph item is selected". They do not mix in the same list.
- Hover previews; click commits. A drag never selects.
- Motion is for HTML controls only: 150–220ms on background, border, colour,
  opacity, transform. SVG graph geometry has no transitions or filters.

## Content and feedback

- Counts live in the header of the level they count. `7 cards · 24 props` sits in
  the parent-group section label, not in a separate card.
- Empty state sits in the body of the level that is empty. It names the missing
  selection and offers one action.
- Loading state sits in the body of the level that is waiting. One line plus
  progress, never skeleton cards.
- Errors appear at the level that failed. Toasts are only for transient global
  feedback.
- Bounded lists are a section behaviour: 120 coverage rows, 60 decisions, 40
  findings, with `Show all` / `Show less` in the section label row.

## Density and grouping

Cards are allowed only when elevation communicates real hierarchy — a dialog, a
popover, a floating canvas widget. In this viewer, panels and sections are flat;
a card inside a panel is always a nesting error.

This is a dense operational UI, so rows are the product, not decoration:

- Group rows into sections by a real conceptual question, not by alphabet or
  file order.
- Show the aggregate or most important rows first; the rest follow in the same
  section.
- Bound a long list at a known count and offer `Show all` in the section label;
  never render an unbounded data dump.
- A section with more than one conceptual group is split. A row with more than
  one subject is split.
- Density is a property of the task. Do not reduce a reviewer's ability to scan
  hundreds of rows; remove chrome, not evidence.
- Use rules, spacing and alignment to separate items. Do not use borders plus
  shadows plus a filled surface to say "these belong together" — that is what a
  section label and a 1px rule already say.

### Graphs are not lists

A graph layout preserves rank and edge direction. Do not wrap a rank, a
neighbourhood or a composition into a new line/column to make it fit; that folds
the graph and breaks the reader's mental model of the flow.

- If the graph is wider than the viewport, focus the relevant subgraph and
  pan/zoom; do not fold it into a card grid.
- A **local focus layout** is allowed: lay out the selected group or
  neighbourhood on its own, with both endpoints of every focused edge present.
- Independent nodes with no internal edges may use a compact block, but it must
  read as a source block, not as a folded flow.
- Explicit `Fit` may show the whole graph at a small scale; it is a user action,
  not the opening layout.

## Motion

Motion follows frequency and purpose. Every animation must answer what it
communicates; if the answer is "it looks alive", remove it.

| Situation | Behaviour |
| --- | --- |
| Keyboard actions, 100+ uses/day | none |
| Graph hover, selection, filter, pan, zoom | none inside the SVG scene; pointer feedback only |
| Row hover/focus | instant, or colour only at ≤120ms |
| Panel/rail switch, section collapse | 150–220ms on opacity/transform, ease-out |
| Menus, popovers, dialogs | 150–200ms, ease-out, origin-aware |
| Canvas geometry (nodes, edges, layout) | never animates on selection or filtering |

- Do not animate layout properties. Use transform and opacity.
- Do not animate from `scale(0)`; nothing appears from nothing.
- `prefers-reduced-motion` removes non-essential motion.
- A state change must be readable at the moment it happens; a fade that delays
  the answer is worse than no fade.

### Two chrome bars, then overlays

The workbench has exactly **two** stacked chrome bars. Anything else that
changes the body is an overlay inside that body.

| Bar | Level | Answers | Example |
| --- | --- | --- | --- |
| Application header | Window | Where am I, and which task? | `Map · Explore · Review` + search/import |
| Panel header row | Panel | Which model slice, and which representation? | `Execution · Workflow | Blueprint | Lineage` + view controls |

The panel header row is the aligned set of **panel-local headers**, not a global
toolbar. Each header is rendered inside the panel it controls and owns that
panel's title, counts, representation tabs and view controls.

A control that scopes a canvas (`group by`, `collapse all`, `expand all`,
`Cards | Graph`, `whole graph`, source filter) is a **canvas overlay**:

- it floats in a corner of the canvas it changes;
- it has a compact, content-sized surface, never a full-width strip;
- it has no bar height, no second title and no panel-level border;
- it disappears with its canvas and is repeated for no other panel.

The Outliner never hosts a control that changes the canvas. It shows the
grouping read-only and lists the groups that result from it.

The vertical Properties rail is not a bar. It switches the **meaning** of the
Properties body: Definition, Production, Emission, Dependencies and, when
annotations exist, Context. Only the sections that answer the active question
are visible; the panel header states that question.

The canvas items themselves — group frames, step cards, entity cards, lineage
nodes — are not bars, sections or rows. They belong to the canvas.

## Applied hierarchy

| Window | Workspace | Panels | Sections |
| --- | --- | --- | --- |
| Main | Map | Editor, Navigator | Groups, Selection, Properties, Neighbours |
| Main | Explore | Outliner, Editor, Properties | Blueprint parent groups; Lineage receipt/impact; Workflow group frames; Properties groups |
| Main | Review | Editor (+ section rail) | Summary, Findings, Questions, Coverage, Decisions, Build, Diff, Dossier |

Panel ownership is fixed:

- **Outliner** owns the tree and filters.
- **Editor** owns the representation tabs and the canvas/list.
- **Properties** owns the selected subject's fields.
- **Navigator** owns the selected Map subject and group filters.
- **Review Editor** owns the review rail and all review sections.

## Reference boundaries

Blender is the structural reference, not a template to clone.

| Keep | Change | Do not copy |
| --- | --- | --- |
| area tiling, editor-type headers, Outliner/Properties split, flat widgets, node editor, blue active, orange graph selection | dark graphite palette, workspace names and vocabulary, dense review data, status content | Blender menus, 3D viewport, icons, branding, splash, exact keymaps, light reference theme |

The reference answers "how are regions arranged and how does an editor behave?".
It does not answer "what is the product?" — the graph, workflow, lineage and
review model does.

## DOM contract

The ladder is machine-readable. Every surface marks its levels with
`data-level`:

| Value | Meaning |
| --- | --- |
| `window` | application header |
| `workspace` | workspace row |
| `panel` | a tiled region |
| `panel-header` | its one `PanelHeader` |
| `panel-toolbar` | a filter/action row inside a list panel body, above the list |
| `canvas-overlay` | a compact control cluster floating over the canvas it changes |
| `section` | one facet of the panel |
| `row-group` | a subject row plus its evidence rows, not a section |
| `row` | one subject |
| `field` | one piece of evidence |
| `canvas-item` | a node, edge or frame inside a canvas |
| `control` | a discrete action or input |

Rules enforced by the markers:

- `.ui-section` never contains another `.ui-section`; an entity plus its
  properties is a `row-group`.
- A `row-group` contains sibling rows, not a nested row.
- Every `section` carries an `aria-label` or `title` with its question.
- `.ui-card` is banned inside a panel. It is only for overlays, menus and
  dialogs, where elevation communicates a temporary layer.
- A panel has one `.ui-panel-header`/`PanelHeader`, one scroll owner, and no
  second title.
- A `canvas-overlay` is absolutely positioned inside the canvas, content-sized,
  and never a full-width strip or a second header row.
- A `panel-toolbar` exists only above a list body (filter, counts, bulk actions),
  never above a canvas.
- Closed tree branches and collapsed section bodies do not mount their content.

These markers make the hierarchy testable: a review can count
`[data-level="section"]`, assert `.ui-section .ui-section` is zero, and check that
every section has a question.

## Quality gate

A surface is ready for review only when every P0 answer is yes:

- [ ] Every tiled region has exactly one 32px panel header and one scroll owner.
- [ ] No bordered container sits inside a panel except a field inset or a canvas.
- [ ] Every section states a question and is separated by a rule, not a card.
- [ ] Each child meaning is a refinement of its parent.
- [ ] Siblings partition the parent question without overlap; parent and
      siblings read as one sentence.
- [ ] Every row is a subject with one primary action; no row contains a row.
- [ ] Every action sits at its narrowest owner; no duplicate action labels.
- [ ] One selection colour per context: blue in lists, orange in graphs.
- [ ] Counts sit in the header of the level they count.
- [ ] Empty, loading and error states exist at the level where they occur.
- [ ] Motion follows the frequency/purpose table; graph geometry does not animate.
- [ ] Graphs preserve rank and edge direction; no rank wrapping or forced grid,
      and every focused edge has both endpoints in the focused graph.
- [ ] `npx tsc --noEmit`, `npm run test` and the production build pass; no overflow at 1280 or 1920.
- [ ] No literal hex, local palette or one-off header/card recipe.

Read the result as the chain Window → Workspace → Panel → Section → Row → Field.
If a level cannot state its question in one sentence, delete or merge it.

## Review checklist

Read the screen as a chain, not as a set of components:

- **Window:** the campaign and the active task are unambiguous.
- **Panel:** its model slice is named; one header, one scroll owner.
- **Section:** its question is answerable from its rows; separated by a rule.
- **Row:** the subject is obvious, the evidence is adjacent, the action is
  singular.
- **Field:** read as evidence, not as a place to go.

Then ask the conceptual questions:

- Can every level state its question in one sentence?
- Does descending narrow the question, and does ascending return a result?
- Does the same subject keep its identity across representations?
- Is exactly one thing the focal point at this level?
- Is anything here a card that is only pretending to be a section?

A change that needs a new level, a new header height, a local palette or a new
card recipe is a change to this document first, not a component-local exception.
