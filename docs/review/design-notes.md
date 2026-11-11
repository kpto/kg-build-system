---
title: Design notes
summary: The guide's layout, visual system and evidence model, and the trade-offs each choice accepts.
section: review
order: 70
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - STYLE.md
  - docs/developer/index.md
  - FRAMEWORK_STATE.md
  - README.md
---

> [!lede]
> This page records why the guide is shaped as it is. It is a design rationale, not a style guide: each choice answers a reader problem and accepts a cost.

## What it is

The guide serves two jobs: an author builds a graph without reading the implementation; a reviewer judges the model and its evidence. The [home page](/index) is a dashboard with three doors, a subject map, six lifecycle paths, a philosophy band and a measured status strip. Every page makes one claim, states its rules, shows its evidence and names one next step. Philosophy is a lens, not a stage: it is read before Author and applied in Review. A page is a dated claim about the source checkout, not a second implementation.

## Rules

The layout follows the Laws of UX, attributed to Jon Yablonski at <https://lawsofux.com>. The table paraphrases; it does not quote definitions.

| Law | Choice | Cost accepted |
| --- | --- | --- |
| Hick's Law | Three doors, a subject map, six lifecycle paths and a philosophy lens. | The reference tail is hidden; search and Reference carry it. |
| Miller's Law / chunking | Six lifecycle sections, one idea per page, rules in tables. | More pages; each must earn its place. |
| Jakob's Law | Familiar docs frame: left explorer, search, breadcrumb, title, right contents. | It must beat other docs on content, not chrome. |
| Common region / proximity | Cards and plate frames group by boundary and spacing. | Grouping needs whitespace; density erases it. |
| Similarity | One concept colour and glyph across plates, badges, tables and cards. | A large palette is noise; colour stays inside plates. |
| Aesthetic-usability effect | A calm surface; limits stay visually distinct. | Polish implies completeness; ochre and Limits resist it. |
| Cognitive load | Lede states the problem; top layer has no signatures; evidence at the bottom. | Exact names require scrolling or Reference. |
| Doherty Threshold | Static HTML, SPA navigation, SVG plates, no client fetch. | No live graph view or interactive filtering. |
| Tesler's Law | Generated API and document shapes absorb complexity. | Blocks lag until the next `make generate`. |
| Pareto Principle | The Start path and the core authoring chain cover the common build; Reference serves the tail. | Meaning and generation leave the common path. |
| Von Restorff Effect | One accent for current path and decisions; ochre for limits. | Only one thing can stand out. |
| Serial position effect | Start first, Next last; one rule and one next page repeated. | Repetition costs words. |
| Peak-end rule | Every page ends with a rule and a named next step. | A weak next step is visible. |
| Occam's Razor | Twins merged, generated dumps deleted, graph view removed. | Some readers lose a familiar view. |
| Paradox of the active user | Walkthrough second; theory follows a runnable build. | Theory-first readers skip forward. |
| Goal-gradient effect | Numbered Start path; authoring pages name their place in the chain. | Numbers imply one order. |

Three conflicts matter. Hick's Law and Pareto pull opposite ways: fewer doors hide the tail, so search and Reference absorb it. Aesthetic-usability and honest limits conflict: a calm surface can read as a guarantee, so limits get a separate section. Von Restorff and similarity conflict: if every concept colour competed, the current path would vanish; concept colour stays in plates, and the accent is reserved for navigation and decisions.

**Visual system.** Paper `#f7f3ea` and ink `#1d232a`, graphite in dark mode. The concept registry gives each concept a colour and glyph. Plates are static SVG with a fixed light palette. Schibsted Grotesk headings, Source Sans Pro body, IBM Plex Mono names. A 47rem article sits between a left explorer and right contents. Feedback is 120-180ms ease-out on hover and focus only; reduced motion removes movement; print keeps plates and tables together and expands links.

## Evidence

<figure class="kb-plate">
  <img src="/_assets/review-loop.svg" alt="A claim is tied to sources, verified on a date, and turned into generated evidence that can expose drift.">
  <figcaption>A page is a dated claim, not an approval. The loop closes when a generated block contradicts it.</figcaption>
</figure>

`verified` dates the claim against its `sources`; it replaces human approval. Generated blocks cover status, API, code-map, decisions, drift and reference. `make check` validates structure, links, decisions, word limits and marker integrity; `make generate` rewrites the blocks. Measured status is on [Verification](/review/verification).

## Limits

- Laws are heuristics, not measurements.
- Plates show the model.
- `make check` validates shape and links, not truth. A green run can contain a wrong sentence.
- Generated blocks can lag the source; drift makes that visible.
- Tuned for one framework.
- Print and reduced motion are CSS contracts, not browser tests.

See [Framework philosophy](/developer/philosophy).

## Next

[Drift](/review/drift) — where a dated claim is checked against source history.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | `AGENTS.md#rule-promotion` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/developer/index.md`; `specs/README.md` |
