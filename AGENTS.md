# Agent notes

This is the entry point for working in this repository. It has two domains: how
an agent works, and the framework model the work is reviewed against.

Domain boundary: a rule about how the work is done belongs to agent behaviour; a
rule about what the framework is belongs to the framework model.

## Agent behaviour

### Working

- Understand the current model before changing it.
- Think from the author's and the graph consumer's perspective: why the framework
  exists, what the author gains, and what a consumer can rely on. Do not reduce
  the work to code mechanics.
- Act as a product owner: challenge, remove, merge or reshape a feature when the
  model is incoherent.
- If the model is wrong, change the model rather than building around it.

### Writing

- A document states the current model as if it were the only one.
- Write for a reviewer who has not seen the conversation, an earlier version or
  the review: define terms, name the interface, file or type, and state the
  decision.
- State the decision, not the route to it.
- Write in point form, finalised and succinct; prefer a short signature and a
  concrete example to a narrative.
- Anything that only makes sense as a change, comparison or reply belongs in the
  change report.

### Review

- A change that crosses a subpackage boundary is proposed as an interface change
  before it is implemented.
- Author-facing interfaces are reviewed through the docs under `docs/`; internal
  interfaces are reviewed through the spec MD files.
- Docs are author-facing, not simplified. Include anything an author might need
  to know: semantics, edge cases, limits, examples and the reasons behind a
  rule. Structure makes them readable, not the amount of detail.
- Docs and specs may cover the same subject for different readers; they are not
  alternates.
- A spec states the interface: names, signatures, invariants, allowed
  dependencies and the authoring surface. Implementation detail is out of scope.
- The interface is the review surface; implementation is not. When the code and
  the spec disagree, the spec is the decision and one of them changes.
- A plan or a changelog is a change report, not a spec.
- The proposal is read in one screen:

| Field | Meaning |
| --- | --- |
| Responsibility | The subpackage or module that owns the decision |
| Interface delta | Public names, signatures and invariants, before and after |
| Dependency delta | Imports added or removed, and the direction |
| Authoring delta | What an author writes differently; the typecheck fixture |
| Deletions | Features removed or merged; no compatibility path |
| Contract tests | The tests that now guard the interface |
| Verification | Tests, type checker and any document build |

| Surface | Reader | What it states |
| --- | --- | --- |
| `docs/` | graph author | what to write, what the graph does, and the semantics and limits an author needs |
| spec MD | framework reviewer | internal interface, boundaries and invariants |

- If the interface delta does not explain the change, the change is not ready.
- End every change report with the rule-promotion result: none, refined or
  added.

### Rule promotion

- At the end of every change, and after a correction that applies beyond it,
  check for a rule that is general enough to govern future work.
- General means: it applies to a different task or subpackage and does not name
  the incident that produced it.
- Place it in the domain it governs: agent behaviour or framework model.
- Refine an existing point instead of adding a case; keep this file small.
- The point is a rule, not a record of the work. The main agent may add or refine
  it directly and report the result.
- Only the main agent edits this file; a subagent reports a proposed rule to the
  main agent.

### Verification

- Run the tests and the type checker for the area changed.
- Update the contract test and the authoring typecheck fixture with the
  interface.
- Do not rebuild the graph or regenerate artifacts unless asked.

---

## Framework model

### Semantics as contract

- The graph's meaning is part of the delivered contract, not a comment or an
  implementation detail.
- A node or edge type states its meaning, direction, identity, absence and limits.
- The build preserves those statements and publishes them for consumers.
- A meaning that cannot be stated is recorded as a limit; it is not invented.

### Experimental

- The API is not stable; breaking changes are expected.
- The framework has no schema versions and no compatibility negotiation or
  migration path.
- If an artifact needs an identity, derive it from its content.

### Interfaces

- A **subpackage** is a directory that owns one responsibility.
- An **interface** is the set of names another subpackage may use: types,
  protocols, functions, errors and their invariants.
- The interface is not `__all__`; it is the surface designed to be depended on.
- The reviewer supervises interfaces; implementation is replaceable behind them.
- An implementation detail is sampled only when it suggests the interface or the
  responsibility is wrong.
- An interface change is a model change, visible before implementation.

### Separation of responsibilities

- One module owns one decision; its path and name tell the reviewer which one.
- If the purpose needs "and", it is more than one module.
- The test is local change: a join-semantics change lives in the row-source
  algebra and does not require editing table declarations, the compiler and the
  authoring API.
- A small feature that forces edits across several subpackages means the boundary
  is wrong; fix the boundary, not the call sites.
- Avoid god modules, duplicated plan models, duplicated codecs, and helpers that
  exist only because two modules could not agree on an interface.

### Explicit boundaries

- Each subpackage declares its responsibility, its interface and the subpackages
  it may import.
- Other subpackages import the interface, never a private implementation module.
- The dependency direction is one graph; a cycle or a new edge is a model change.
- A new edge may be right, but it is proposed with its reason; the reviewer
  decides whether the model changes.
- A join change belongs to the row-source package. If the compiler needs a
  generated join shape, the row-source interface exposes that shape; the compiler
  does not import a private module to find it.

### The authoring API is the guard

- The **authoring API** is what a graph author writes; it is the product model,
  not a convenience layer over internals.
- It makes the intended use easy and the wrong use impossible.
- It exposes only what an author may write; internal types stay internal.
- A feature that cannot be expressed cleanly through it is probably wrong.
- Typecheck fixtures exercise the public surface and guard it.

### Models are anaemic and amnesic

- The framework uses anaemic models deliberately: a model is frozen data holding
  the facts it owns, not a service object.
- Behaviour that needs more than those facts is a function beside the data.
- This keeps the data portable, the tests local and the location of behaviour
  explicit.
- A model has no reference to an owner or a wider context and stores no identity
  that can be derived.
- Anaemic is about behaviour; amnesic is about ownership and identity. Both are
  deliberate.
