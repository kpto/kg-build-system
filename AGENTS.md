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

### Delegation

- A subagent brief is an interface specification, not a task description.
- It names the exact exported and non-exported symbols, the allowed import
  edges, the compatibility shims that must remain, the wrapper shape and the
  command that judges the result.
- "Move the public material", "keep old paths" and "preserve behaviour" are not
  specifications; they leave the subagent to decide the interface.
- Write the acceptance test first and include it in the brief. If the brief
  cannot name what the test asserts, the interface is not decided yet.
- Reuse the subagent session for corrections. Send the same session a follow-up
  with the named defect and the acceptance command; do not spawn a new agent for
  the same component or take the edit over from the main agent. The session
  already holds the package context and the original brief.
- The reason is not agent management: a follow-up forces the correction to be
  stated as a decision. If the same session cannot apply it unambiguously, the
  decision is not precise enough.

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

### Kernel and distribution

- `kg_build_system.kernel` is domain-agnostic: language, module, build value,
  registry and the module contract. It imports no table, topology, expression,
  engine or workflow package.
- A default implementation belongs to the distribution, not the kernel. Do not
  promote a library to a capability module without a second implementation or a
  runtime configuration that selects it.
- `table`, `topology` and `binding` are languages; `expressions` contributes
  operations; `core` is a module; engines own code generation.
- An operation is one specification plus one engine lowerer. Adding one does not
  edit a dispatcher.
- A custom language and module compile and execute without the default
  distribution; a graph build is one distribution, not the kernel.

### Semantics as contract

- The graph's meaning is part of the delivered contract, not a comment or an
  implementation detail.
- A node or edge type states its meaning, direction, identity, absence and limits.
- The build preserves those statements and publishes them for consumers.
- A meaning that cannot be stated is recorded as a limit; it is not invented.
- The blueprint is the semantic model of the graph, not a snapshot of the
  declarations that produced it. Topology reads as nodes, edges, labels,
  endpoints and properties; it does not carry Python paths, declaration
  expressions or symbol IDs.
- A DTO is a member of the blueprint or the workflow contract. A value outside
  those two artifacts is in-memory: a lowered model, a plan, a render input or
  a build result. It is not a DTO and is not expected to deserialise.
- A layer DTO does not know the blueprint. It knows only the DTOs of the layers
  it depends on. The blueprint package assembles the layer DTOs into one
  semantic model.
- `compile` reads a blueprint and produces the workflow contract. It does not
  assemble a blueprint and does not call the blueprint package. The composition
  root calls `create_blueprint` and then `compile`.
- The blueprint is public: a user may obtain a blueprint handle. The layer DTOs
  it references are not exported public names. The canonical flow is the
  compile shortcut that creates and consumes the blueprint without exposing it.
- Source generation is the responsibility of the layer that owns the DTO. A
  layer renders its own DTO using its dependency layers' renderers; the
  blueprint layer only delegates to each layer and assembles the fragments.
- The blueprint must regenerate equivalent authoring source. The round trip
  `blueprint -> generated source -> blueprint` is a contract test, not a
  convenience.

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
- Every framework subpackage uses the same four-part layout:
  - `__init__.py` — the public facade; it imports only from `.public`;
  - `public/` — the public domain: names a graph author writes or reads;
  - `internal/` — the framework-internal interface, `ir.py` and adapters;
  - `_private/` — mechanisms imported only inside the package.
- `public` is the definition site for author-facing names. A public function or
  method is a thin wrapper over `_private` or `internal`; the mechanism is not in
  `public`.
- Another subpackage imports `pkg`, `pkg.internal` or `pkg.internal.ir`. It never
  imports `pkg._private`. Importing `pkg.public` directly is limited to frozen
  type vocabulary; a behaviour belongs in `internal`.
- A subpackage may have no author-facing surface when nothing in it is written by
  a graph author; its `public/` states that, it does not pretend to be a facade.
- Implementing another package's protocol is a separate file under
  `internal/adapters/<protocol>.py`. The file names the protocol and delegates to
  `_private`; it is not buried in a model or factory.
- Interface and IR values are anaemic: frozen data with no owner, no service and
  no behaviour beyond its own invariants. Derived rules are functions beside
  them.
- A protocol is the internal interface of a dependency direction: a module
  implements it, a runtime calls it. Do not carry a live service inside a data
  model.
- The dependency direction is one graph; a cycle or a new edge is a model change.
- A new edge may be right, but it is proposed with its reason; the reviewer
  decides whether the model changes.
- A join change belongs to the row-source package. If the compiler needs a
  generated join shape, the row-source interface exposes that shape; the compiler
  does not import a private module to find it.

### The authoring API is the guard

- The **authoring API** is what a graph author writes; it is the product model,
  not a convenience layer over internals.
- A public API method is a thin wrapper over an internal implementation, with a
  docstring and a runnable example. It is not a bare re-export.
- It makes the intended use easy and the wrong use impossible.
- It exposes only what an author may write; internal types stay internal.
- A type in a public signature is a public type. If the value is internal IR, the
  public function returns either an opaque token or a public view of it; it does
  not expose the IR under an internal name.
- A feature that cannot be expressed cleanly through it is probably wrong.
- Typecheck fixtures exercise the public surface and guard it.

### Names state the role

- `IR` is not a synonym for internal data. Do not use it as a module or class
  suffix.
- A serialisable model is a DTO, and its module names the artifact it belongs
  to: `blueprint_dto.py`, `contract_dto.py`, `instruction_dto.py`,
  `render_dto.py`.
- A type in a DTO module carries the `DTO` suffix: `ComponentDTO`,
  `BindingDTO`.
- A model that is not serialised is not a DTO: name it an in-memory `model` or
  an engine-neutral `plan`. A DTO whose artifact cannot be named is not a DTO.
- Use one verb per transformation. A language **transcribes** declarations to
  its DTO; the blueprint **assembles** layer DTOs; compile **compiles** a
  blueprint to a workflow contract; the engine **emits** SQL from a plan; source
  generation **renders** a DTO to authoring source. Do not use `lower` for any
  of them.
- A language transcribes declarations to its DTO and renders its DTO back to
  authoring source. `transcribe` and `render` are the two directions of the same
  language.
- A language does not encode or decode. Serialisation belongs to the DTO codec,
  which names its artifact: `to_document` / `from_document`. The blueprint codec
  composes the layer codecs.

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
