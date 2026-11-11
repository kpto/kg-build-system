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
  - docs/developer/index.md
  - STYLE.md
subject: verification
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/subjects/verification">Overview</a><a href="/review/drift">Guide</a><a href="/spec/verification">Spec</a><a href="/reference/failures">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/decisions" class="active">Review</a></div>
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

A drifted page is a review candidate, not automatically false. The change may touch an unrelated line. Regenerate evidence, re-read the source, then correct the claim or move `verified` forward. A limit removed in code without a docs change remains a review defect. The measurement side is [Verification](/review/verification).

## Rules

- Every page names one to five real source paths; a missing path fails validation.
- `verified` is the date of the check, not the date of publication.
- Move `verified` only after re-reading the source and regenerating evidence.
- Never move `verified` to silence drift without a check.
- Review a drifted page against its claim; rewrite the claim or the date, not both blindly.
- A code change that removes a documented limit without a docs change is a defect.
- Generated blocks are measured when generated; they do not inherit `verified`.
- A directory source includes every commit under it.
- An untracked source path counts as unverified.

## Evidence

<!-- BEGIN GENERATED:drift -->
Source HEAD: 77f008e · 2026-11-10. Pages checked: 90; clean: 90; drifted: 0.

No page has a source commit after its `verified` date.
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

[Design notes](/review/design-notes) — why the guide is shaped this way.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | `AGENTS.md#rule-promotion` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/developer/index.md` |
