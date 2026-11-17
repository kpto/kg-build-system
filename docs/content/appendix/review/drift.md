---
title: Drift
summary: How to tell a stale claim from a false one, and when a page returns to review.
section: review
order: 60
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - FRAMEWORK_STATE.md
  - DESIGN_ISSUES.md
  - docs/content/appendix/developer/index.md
  - STYLE.md
subject: verification
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A page is verified on a date against named sources. Drift is the latest commit that touched one of those sources after that date: a reason to look, not a verdict.

## What it is

| Term | Meaning |
| --- | --- |
| `verified` | The date a claim was last checked against the page's `sources`. |
| Source | One of the one to five repository paths named in front matter. |
| Drift | The latest commit touching any source path after `verified`. |
| Clean page | No source path has a later commit. |
| Review candidate | A drifted page; its claim may still be true. |
| Code source | A source outside `docs/`, `specs/` and the root Markdown briefings. |

A drifted page is a review candidate, not automatically false. The change may touch an unrelated line. Regenerate evidence, re-read the source, then correct the claim or move `verified` forward. A limit removed in code without a docs change remains a review defect. The measurement side is [Verification](/appendix/review/verification).

Drift is computed from code sources: a path under `kg_build_system/`, `tests/`, `reference_project/` or a packaging file. A documentation path is a cross-reference, not code drift; review it through the link and its own `verified` date.

## Rules

- Every page names one to five real source paths; a missing path fails validation.
- `verified` is the date of the check, not the date of publication.
- Move `verified` only after re-reading the source and regenerating evidence.
- Never move `verified` to silence drift without a check.
- Review a drifted page against its claim; rewrite the claim or the date, not both blindly.
- A code change that removes a documented limit without a docs change is a defect.
- Generated blocks are measured when generated; they do not inherit `verified`.
- A directory source includes every commit under it.
- A documentation source does not trigger drift; it is a cross-reference.
- An untracked source path counts as unverified.

## Evidence

<!-- BEGIN GENERATED:drift -->
Source HEAD: 65778ec · 2026-11-17. Pages checked: 97; clean: 16; drifted: 81.

| Page | Verified | Latest source change | Action |
| --- | --- | --- | --- |
| `appendix/developer/data-and-expressions` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/developer/philosophy` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/developer/project-structure` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/developer/relation-contract` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/developer/system-design` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/developer/testing` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/kernel/boundaries` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/kernel/model` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/kernel/protocols` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/philosophy/anti-patterns` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/philosophy/binding-is-fulfilment` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/philosophy/design-in-meaning` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/philosophy/explainability-is-authored` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/philosophy/meaning-first` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/philosophy/review-top-down` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/reference/annotations` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/api` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/assets` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/bindings` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/cli` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `appendix/reference/compile` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/declarations` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/reference/derived-relations` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/reference/documents` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/expressions` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/failures` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/generation` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/glossary` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/ingest` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/planners-and-executors` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/row-sources` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/topology` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/reference/types` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/review/architecture` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/review/contracts` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/review/limits` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/review/verification` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/architecture` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/asset` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/binding` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/data` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/execution` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/extension` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/generation` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/grain` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/identity` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/linking` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/meaning` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/modules` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/plan` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/selection` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/spec/topology` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/spec/verification` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `appendix/subjects/architecture` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/asset` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/binding` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/data` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/execution` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/extension` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/generation` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/grain` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/identity` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/linking` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/meaning` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/modules` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/plan` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/selection` | 2026-11-10 | 2026-11-16 | 2026-11-16 > 2026-11-10 |
| `appendix/subjects/topology` | 2026-11-15 | 2026-11-16 | 2026-11-16 > 2026-11-15 |
| `appendix/subjects/verification` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-1/01-the-build` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-1/02-a-first-build` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-1/03-a-project` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-3/01-linking-and-blueprint` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-3/02-planning` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-3/03-execution-and-outputs` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-3/04-quality-and-failure` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-3/05-shipping` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-4/01-the-kernel-and-extension` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-4/02-the-default-distribution` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-4/03-architecture-and-tests` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
| `book/part-4/04-limits-and-evidence` | 2026-11-11 | 2026-11-16 | 2026-11-16 > 2026-11-11 |
<!-- END GENERATED:drift -->

The block lists the page, its verified date, the latest source change and the action.

## Limits

- A commit date is not a semantic diff; a formatting change or a test move flags drift without changing the claim.
- Only named sources are watched. A claim that depends on an unnamed path is invisible.
- Git history can be rewritten; the signal is only as good as the dates it carries.
- A clean block proves no source commit is newer, not that the claim is true.
- Drift is computed when `generate` or `check` runs; without CI it can be stale.
- A page whose sources are all untracked never shows drift.

## Next

[Design notes](/appendix/review/design-notes) — why the book is shaped this way.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | `AGENTS.md#rule-promotion` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
