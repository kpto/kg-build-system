---
title: "Part IV — Extending and reviewing"
summary: "How the kernel carries a new capability, how the default distribution composes it, and how evidence reviews the result."
section: book
perspective: meta
part: IV
order: 40
status: normative
verified: 2026-11-11
sources:
  - docs/content/appendix/kernel/index.md
  - docs/content/appendix/framework/index.md
  - docs/content/appendix/review/limits.md
  - docs/content/appendix/developer/testing.md
---

## In this part

Parts I to III build a graph. They start with a project, write declarations, link a blueprint, compile a plan and publish records. Part IV changes the object of study: the graph stays the same, and the machine that builds it becomes the subject.

The change of subject brings two readers. One wants to add a capability the shipped system does not have. The other wants to review a change to the machine without reading every implementation file. The two jobs meet at the same place: an interface. The extender needs to know which object carries the new behaviour; the reviewer needs to know which names, signatures, dependency edges and refusals the change alters.

The running example is a consensus module. The default row algebra groups rows but does not vote. A project that needs one assertion per majority of supporting sources can compose a planner and an executor; the module is plausible, small and deliberately not shipped. It returns in each chapter with a different question: how it is composed, why the default distribution does not already contain it, what its contract tests guard, and which kind of limit its absence represents.

The four chapters move from the smallest unit to the widest claim. Chapter 18 names the six kernel protocols and the values that hold a composition together. Chapter 19 reads the shipped graph distribution as one composition of those protocols rather than the edge of the framework. Chapter 20 turns to the source layout and the contract tests that make a boundary reviewable. Chapter 21 classifies limits, reads decisions as accepted model choices, and treats verification and drift as dated evidence.

<figure class="kb-plate">
  <img src="/_assets/architecture.svg" alt="The kernel sits inside its boundary; languages, the interpreter, modules and the distribution service point inward, with generation, api and cli at the outer edges.">
  <figcaption>The kernel boundary and the default distribution around it. Part IV reads the protocols first, then the composition, then the evidence.</figcaption>
</figure>

## Chapters

| Chapter | Question |
| --- | --- |
| [18. The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) | What must a composition provide before it can add a capability? |
| [19. The default distribution](/book/part-4/02-the-default-distribution) | Which parts of the shipped graph system are choices, and which are model rules? |
| [20. Architecture and tests](/book/part-4/03-architecture-and-tests) | What makes a boundary reviewable before the implementation is read? |
| [21. Limits and evidence](/book/part-4/04-limits-and-evidence) | When is a missing capability a limit, and what evidence supports the claim? |

## Next

[18. The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) — start with the six jobs a composition supplies.
