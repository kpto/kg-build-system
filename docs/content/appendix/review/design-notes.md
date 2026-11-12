---
title: Design notes
summary: The book's layout, visual system and evidence model, and the trade-offs each choice accepts.
section: review
order: 70
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - STYLE.md
  - docs/content/appendix/developer/index.md
  - FRAMEWORK_STATE.md
  - README.md
---

> [!lede]
> This page records why the book is shaped as it is. It is a design rationale, not a style guide: each choice answers a reader problem and accepts a cost.

## What it is

The book serves two jobs: an author builds a graph without reading the implementation; a reviewer judges the model and its evidence. The [home page](/index) is a cover and a route into one argument, not a dashboard of parallel views. The [contents](/book/index) names four parts and twenty-one chapters; the [appendices](/appendix/index) hold the exact material. A chapter can repeat an idea when the argument needs it. An appendix states the same idea precisely. Every chapter starts with a problem and ends with one next chapter.

## Rules

The layout follows the Laws of UX, attributed to Jon Yablonski at <https://lawsofux.com>. The table paraphrases; it does not quote definitions.

| Law | Choice | Cost accepted |
| --- | --- | --- |
| Hick's Law | Two primary surfaces: the book and the appendices. The four-part contents is the only reading tree. | The reference tail is behind one appendices entry; search and the appendix map carry it. |
| Miller's Law / chunking | Four parts and twenty-one chapters; each chapter is one movement of the argument. | A chapter may be longer; it must earn its length. |
| Jakob's Law | Familiar book frame: explorer, search, breadcrumb, chapter title, right contents. | It must beat other books on content, not chrome. |
| Common region / proximity | Parts, chapters and appendix groups are separated by boundary and spacing. | Grouping needs whitespace; density erases it. |
| Similarity | One concept colour and glyph across plates, badges, tables and cards. | A large palette is noise; colour stays inside plates. |
| Aesthetic-usability effect | A calm reading surface; limits stay visually distinct. | Polish implies completeness; ochre and Limits resist it. |
| Cognitive load | A chapter states the problem first; exact signatures live in appendices. | Exact names require a lookup. |
| Doherty Threshold | Static HTML, SPA navigation, SVG plates, no client fetch. | No live graph view or interactive filtering. |
| Tesler's Law | Generated API and document shapes absorb complexity. | Blocks lag until the next `make generate`. |
| Pareto Principle | The book covers the common build; the appendices serve the exact tail. | Meaning and generation require a later chapter. |
| Von Restorff Effect | One accent for the current chapter and decisions; ochre for limits. | Only one thing can stand out. |
| Serial position effect | A chapter opens with a question and closes with one next chapter. | Repetition costs words. |
| Peak-end rule | Every chapter ends with a named next step. | A weak next step is visible. |
| Occam's Razor | Parallel subject views removed; specs and reference demoted to appendices. | Some readers lose a familiar hub. |
| Paradox of the active user | A first build runs before the authoring theory. | Theory-first readers skip forward. |
| Goal-gradient effect | Numbered chapters and parts show progress. | Numbers imply one order. |

Three conflicts matter. Hick's Law and Pareto pull opposite ways: a short contents hides the exact tail, so the appendix map and search absorb it. Aesthetic-usability and honest limits conflict: a calm surface can read as a guarantee, so limits get a separate appendix. Von Restorff and similarity conflict: if every concept colour competed, the current chapter would vanish; concept colour stays in plates, and the accent is reserved for navigation and decisions.

**Visual system.** Paper `#f7f3ea` and ink `#1d232a`, graphite in dark mode. The concept registry gives each concept a colour and glyph. Plates are static SVG with a fixed light palette. Schibsted Grotesk headings, Source Sans Pro body, IBM Plex Mono names. A 47rem article sits between a left explorer and right contents. Feedback is 120-180ms ease-out on hover and focus only; reduced motion removes movement; print keeps plates and tables together and expands links.

## Evidence

<figure class="kb-plate">
  <img src="/_assets/review-loop.svg" alt="A claim is tied to sources, verified on a date, and turned into generated evidence that can expose drift.">
  <figcaption>A chapter is a dated claim, not an approval. The loop closes when a generated block contradicts it.</figcaption>
</figure>

`verified` dates the claim against its `sources`; it replaces human approval. Generated blocks cover status, API, code-map, decisions, drift and reference. `make check` validates structure, links, decisions, word limits and marker integrity; `make generate` rewrites the blocks. Measured status is on [Verification](/appendix/review/verification).

## Limits

- Laws are heuristics, not measurements.
- Plates show the model.
- `make check` validates shape and links, not truth. A green run can contain a wrong sentence.
- Generated blocks can lag the source; drift makes that visible.
- Tuned for one framework.
- Print and reduced motion are CSS contracts, not browser tests.

See [Framework philosophy](/appendix/developer/philosophy).

## Next

[Drift](/appendix/review/drift) — where a dated claim is checked against source history.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | `AGENTS.md#rule-promotion` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md`; `specs/README.md` |
