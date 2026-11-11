---
title: kg-build-system
summary: A book about declaring, compiling and running a knowledge-graph build whose meaning survives it.
section: meta
order: 0
status: normative
verified: 2026-11-11
sources:
  - README.md
  - reference_project/
  - docs/book/index.md
---

<div class="kb-hero">
  <p class="kb-kicker">kg-build-system · a book</p>
  <div class="kb-display">Build a graph whose meaning survives the build.</div>
  <p class="kb-lede">Typed Python declarations become a checked blueprint, a workflow plan and published records. This book follows one estate graph from the first source file to the published result, and then into the machine that builds it.</p>
  <div class="kb-actions">
    <a class="kb-button kb-button-primary" href="/book/index">Read the book</a>
    <a class="kb-button" href="/appendix/index">Use the appendices</a>
    <a class="kb-button" href="/appendix/reference/api">Look up a name</a>
  </div>
</div>

<!-- BEGIN GENERATED:status-strip -->
<div class="kb-stats"><span><b>354</b> tests</span><span><b>1957</b> subtests</span><span><b>1 error</b> pyright</span><span><b>edeb2fc</b> source</span><span><b>2026-11-11</b> checked</span></div>
<!-- END GENERATED:status-strip -->

## One argument, four parts

The book has one argument and four parts. It starts with what a build is, then how to author the declarations it consumes, then how those declarations become records, and finally how the machinery can be extended and reviewed. Chapters return to the same estate example and repeat a rule when the argument needs it; a later chapter does not send you to a separate subject page to understand the earlier idea.

Exact signatures, requirement tables and refusal messages live in the **appendices**. They are written for lookup, not for reading from front to back. The book can state a rule in context; the appendix states the same rule precisely.

## The four parts

| Part | Question | Chapters |
| --- | --- | --- |
| [I — The build](/book/part-1/index) | What does a build produce, and what does it mean to run one? | 1–3 |
| [II — Authoring a graph](/book/part-2/index) | How do meaning and topology frame the data and binding that implement them? | 4–10 |
| [III — From declarations to records](/book/part-3/index) | How does a declaration become a checked plan and a published result? | 11–15 |
| [IV — Extending and reviewing](/book/part-4/index) | How does the kernel carry a new capability, and how is a change judged? | 16–19 |

## How to read it

- **First time through.** Read in order. The running example grows from one table to a published graph; each chapter assumes the previous decisions.
- **You need to build now.** Start with [A first build](/book/part-1/02-a-first-build), then [A project](/book/part-1/03-a-project). Return to the authoring part when the reference project stops being enough.
- **You need an exact name.** Use [Reference](/appendix/reference/index) or [API surface](/appendix/reference/api).
- **You need a normative requirement.** Use [Specifications](/appendix/spec/index).
- **You are reviewing the framework.** Read Part IV, then [Architecture](/appendix/review/architecture), [Contracts](/appendix/review/contracts) and [Limits](/appendix/review/limits).

> [!note] What this book is not
> It describes one checkout, not a compatibility promise. The framework is experimental; there is no schema version, migration path or stable plan format. Recompile when a declaration, planner or executor changes.

<p class="kb-attribution">Interface choices follow <a href="https://lawsofux.com">Laws of UX</a> (Jon Yablonski). The mapping is in <a href="/appendix/review/design-notes">Design notes</a>.</p>
