---
title: Appendix D · Review and evidence
summary: Judge the model through its boundaries, invariants, limits, decisions and generated evidence.
section: review
order: 0
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - docs/appendix/developer/
  - FRAMEWORK_STATE.md
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix D · Review and evidence</p>
  <p class="kb-lede">The review surface is the interface, not the implementation. Read the boundary first, then the invariants it protects, then the limits it accepts. The evidence tables are generated from the source checkout.</p>
</div>

<div class="kb-steps">
  <a class="kb-step" href="/appendix/review/architecture"><span>01</span><strong>Architecture</strong><p>Kernel, distribution, zones and the dependency spine.</p></a>
  <a class="kb-step" href="/appendix/review/contracts"><span>02</span><strong>Contracts</strong><p>The invariants a change must not break.</p></a>
  <a class="kb-step" href="/appendix/review/limits"><span>03</span><strong>Limits</strong><p>The product boundary a consumer must accept.</p></a>
</div>

## In this section

| Page | Reader question |
| --- | --- |
| [Architecture](/appendix/review/architecture) | Where does code belong, and which edge would be a model change? |
| [Contracts](/appendix/review/contracts) | What must remain true across the three verbs? |
| [Limits](/appendix/review/limits) | What does the framework deliberately not do? |
| [Decisions](/appendix/review/decisions) | Which dated decision governs this page? |
| [Verification](/appendix/review/verification) | What was measured on this checkout, and where do docs disagree? |
| [Drift](/appendix/review/drift) | Which claims have outlived their sources? |
| [Design notes](/appendix/review/design-notes) | Why does this book look and read the way it does? |

## Pages

Read [Philosophy](/appendix/philosophy/index) first; it is the lens for the review order. The [spec index](/appendix/spec/index) is the normative view. The [book](/book/index) explains the model in order; this appendix holds the evidence. Start with [Architecture](/appendix/review/architecture). The contracts assume its boundaries; the limits explain where the boundaries stop. [Verification](/appendix/review/verification) and [Drift](/appendix/review/drift) are evidence, not opinion.

## Next

[Architecture](/appendix/review/architecture) — the kernel and distribution in one plate.
