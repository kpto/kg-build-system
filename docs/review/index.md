---
title: Review
summary: Judge the model through its boundaries, invariants, limits, decisions and generated evidence.
section: review
order: 0
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - docs/developer/
  - FRAMEWORK_STATE.md
---

<div class="kb-section-head">
  <p class="kb-kicker">05 · Review</p>
  <p class="kb-lede">The review surface is the interface, not the implementation. Read the boundary first, then the invariants it protects, then the limits it accepts. The evidence tables are generated from the source checkout.</p>
</div>

<div class="kb-steps">
  <a class="kb-step" href="/review/architecture"><span>01</span><strong>Architecture</strong><p>Kernel, distribution, zones and the dependency spine.</p></a>
  <a class="kb-step" href="/review/contracts"><span>02</span><strong>Contracts</strong><p>The invariants a change must not break.</p></a>
  <a class="kb-step" href="/review/limits"><span>03</span><strong>Limits</strong><p>The product boundary a consumer must accept.</p></a>
</div>

## In this section

| Page | Reader question |
| --- | --- |
| [Architecture](/review/architecture) | Where does code belong, and which edge would be a model change? |
| [Contracts](/review/contracts) | What must remain true across the three verbs? |
| [Limits](/review/limits) | What does the framework deliberately not do? |
| [Decisions](/review/decisions) | Which dated decision governs this page? |
| [Verification](/review/verification) | What was measured on this checkout, and where do docs disagree? |
| [Drift](/review/drift) | Which claims have outlived their sources? |
| [Design notes](/review/design-notes) | Why does this guide look and read the way it does? |

## Pages

Read [Philosophy](/philosophy/index) first; it is the lens for the review order. The [spec index](/spec/index) is the normative view, and the [subject map](/subjects/index) links each spec to its guide, API and review. Start with [Architecture](/review/architecture). The contracts assume its boundaries; the limits explain where the boundaries stop. [Verification](/review/verification) and [Drift](/review/drift) are evidence, not opinion.

## Next

[Architecture](/review/architecture) — the kernel and distribution in one plate.
