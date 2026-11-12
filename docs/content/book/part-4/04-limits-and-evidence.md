---
title: "21. Limits and evidence"
summary: "A limit is a classified boundary, a decision is an accepted model choice, and verification and drift are dated evidence rather than approval."
section: book
perspective: book
part: IV
chapter: 21
order: 44
status: normative
verified: 2026-11-11
sources:
  - docs/content/appendix/review/limits.md
  - docs/content/appendix/review/verification.md
  - docs/content/appendix/review/decisions.md
  - docs/content/appendix/review/drift.md
  - tests/test_reference_build.py
---

## A limit is a decision with a name

A reader asks whether the framework can compute a majority vote. Three answers are possible, and they are not interchangeable. The first is "no, but a module can": the row algebra collects rows and does not aggregate them, and a planner plus an executor can add the vote. The second is "no, and no composition should": a graph property is scalar, so a nested object is reified as nodes and edges. The third is "not measured": a graph with 5.9 million annotations may be too large for the current path, but no benchmark in this checkout settles the question.

A limit page is useful only when it separates those answers. A missing feature, a deliberate semantic constraint and an unmeasured scale question all look like "the framework cannot" from the outside. Inside the framework they call for different work: a new object, a model change or a measurement.

The definition is therefore narrow. A limit is a boundary stated where a consumer meets it. The code refuses the unsupported case instead of approximating it. The limit names the kind of boundary and, where one exists, the object that replaces it. Read that way, a limit is an interface, not an apology.

## Six kinds, six answers

The framework classifies every limit as one of six kinds.

A **model rule** is a semantic constraint. Changing it is a model change, not a new composition. A graph property is scalar or a flat array of non-null scalars, so a nested object becomes nodes and edges. An edge is directed. An instruction kind is exact. A Python instruction carries a `{module, qualname}` reference rather than a live callable. An asset layout is descriptive, not an access contract. A project has one `Toolchain` and no registry. These are not gaps waiting for a plugin; they are decisions about what the graph and the workflow are allowed to mean.

A **replaceable default** is the composition's choice, replaced by another implementation of the same protocol. `DuckDbSqlEmitter` implements `SqlEmitter`; another engine supplies another emitter and an executor. The source planner resolves Parquet, JSON and CSV; another planner resolves another format. The file, meta-graph and Neo4j modules are output targets; another module publishes another artifact. The default languages and the `BlueprintLinker` are replaceable in the same way. The cost is real implementation work, but the boundary already names the object that carries it.

A **current algorithm** is the default implementation's method, replaced by another planner. `group_by` collects but does not aggregate. Deduplication removes only identical rows. Merge groups by build key, takes `min()` per property and requires an explicit component scope. Conflict checks are blind to null-versus-value, endpoints, binding symbols, unbound components and extra columns. Neo4j is export-only. Each of these is a method, not a meaning; another planner carries another method without changing the model.

**Not implemented** means the capability is absent from the current objects, and a new object carries it. There is no semicolon-list decoder, no per-step timeout, retry, cancellation or memory quota, no schema version or migration path, no network acquisition step, no built-in licence filter and no incremental update. These are not refusals of the concept. They are absences that a source planner, an executor, a runtime, a provider or a versioned codec can fill.

An **interface limit** means the public surface does not carry the concept. Public blueprint fields reference internal language DTOs that are not exported public names. The CLI offers `kbs generate` and no build subcommand. A public view, an opaque token, a new frontend or an interface change carries the concept; a new private helper does not.

An **empirical** limit is an unmeasured question, not an expressive boundary. A graph with 5.9 million annotations is unproven at scale. The repository has no CI configuration. The first is a benchmark question; the second is a delivery gap. Neither says what the framework can express, and neither is fixed by adding a protocol.

The kinds matter because they answer "why not?" differently. A model rule says the alternative would change the meaning. A replaceable default says the alternative is another implementation. A current algorithm says the alternative is another method. Not implemented says the alternative is another object. An interface limit says the alternative is a public surface. Empirical says the alternative is a measurement.

## The classified table

The canonical table collects the boundaries a consumer meets. Every row is one of the six kinds, and the last column names the replacement or the reason no composition should carry one.

| Boundary | Current choice | Kind | Extension point or model reason |
| --- | --- | --- | --- |
| Composition | `Toolchain` only; no registry | Model rule | Compose another `Toolchain`; a language, planner or executor is a value, not a registry entry; a provider is added to the runtime. |
| SQL engine | DuckDB default emitter | Replaceable default | Implement `SqlEmitter` and compose the executor. |
| Source formats | Parquet, JSON and CSV | Replaceable default | Another ordinary planner; no adapter registry. |
| Row algebra | `group_by` collects; no aggregation or majority vote | Current algorithm | A module: `Planner` plus `StepExecutor`. |
| Source decoding | No semicolon-list decoder | Not implemented | A source planner or executor, or a language operation. |
| Python instruction payload | `{module, qualname}` reference | Model rule | A new executor kind or an external service. |
| Python execution | No isolation, timeout or retry | Not implemented | A new executor or runtime. |
| Blueprint fields | Public fields use internal language DTOs | Interface limit | A public view or opaque token; an interface change. |
| Asset layout | Descriptive, not an access contract | Model rule | No extension; a planner may interpret it. |
| Struct keys | Repeated struct names take a qualified key segment | Model rule | No extension. |
| Instructions | Exact-kind map; unknown kind refused | Model rule | Another executor claims another exact kind. |
| Deduplication | Removes only identical rows | Current algorithm | Another planner. |
| Merge | Build-key groups, `min()` per property, explicit scope | Current algorithm | Another planner. |
| Conflict checks | Blind to null-versus-value, endpoints, binding symbols, unbound components and extra columns | Current algorithm | A new planner. |
| Neo4j | Export-only Parquet and import script | Current algorithm | Another output module. |
| CLI | `kbs generate` only | Interface limit | Compose Python calls; a new frontend adds commands. |
| Versioning | No schema version, plan or blueprint migration | Not implemented | A versioned codec envelope; no compatibility promise. |
| Undirected edges | Directed `Edge[Source, Target]` only | Model rule | Reify the assertion or add a language declaration kind; a model change. |
| Download and ingest | No network acquisition step | Not implemented | A `ResourceProvider` and executor, or an external script kept for reproducibility. |
| Licence enforcement | No built-in filter | Not implemented | Resource facts plus a filter module. |
| Incremental update | Whole-plan rebuild | Not implemented | A runtime or planner extension. |
| Scale | 5.9 million annotations unproven | Empirical | A benchmark question, not an expressive limit. |
| CI | No CI configuration | Empirical | A delivery gap, not a framework limit. |

The table is a review instrument, not a bug list. The first step in reading a row is to find its kind. A model rule ends the search: the next move is a developer proposal and a specification change, not a new planner. A replaceable default, a current algorithm or a not-implemented row names the object that carries the work, so the review asks whether that object is correctly composed and tested. An interface limit asks for a public surface. An empirical row asks for a measurement, not a feature.

The second step is to check the direction of the claim. A missing default is not a missing framework capability. A model rule is not an arbitrary restriction. An empirical gap is not a refusal. A reviewer who collapses the kinds will either demand a kernel change for a missing planner or accept a model change as a harmless module. Both mistakes are expensive because they move the decision to the wrong place.

The table also has a maintenance rule. A limit is removed only with the documentation change in the same change. Code that drops a limit while the documentation keeps it is a review defect. The reverse is also true: a page that states a limit the code no longer enforces sends a consumer down a path that does not exist.

## Decisions are accepted model choices

The decision register records the rules the project follows. Each row carries an id in the `D-001` to `D-039` range, a statement of the rule, its author date, its status and an evidence path. The ids are stable, and the same id must read the same on every page that carries it.

A decision is not a vote or a formal ADR status. The repository has no ADR directory and no status field beyond `accepted`. `accepted` records survival in the history window: the rule was adopted, it still matches the pages that own it, and the evidence still exists. A decision can be underspecified at its origin; the current documentation is often the clearer statement than the commit that introduced it.

The register matters to Part IV because it explains why a model rule is not arbitrary. `D-001` separates the domain-agnostic kernel from the graph distribution. `D-005` makes the workflow contract step-centric and instruction-based with exact instruction kinds. `D-030` makes core consume an engine-neutral relation plan and an injected `SqlEmitter`. `D-031` builds the blueprint from symbols and typed refs and groups feature code into modules. Those decisions are the reasons the ladder has the rungs it has.

A decision is not a compatibility promise. No plan or blueprint migration follows from it. A decision that no longer matches its sources is a drift candidate, not a permanent law. The register is a record of accepted model choices with evidence, which is exactly what a reviewer needs in order to challenge one without starting from a blank page.

## Verification is a measurement with a date

Verification is a measurement, not an approval. The verification page carries generated blocks: one reports tests, subtests, pyright errors and the source commit; one reports the reference build's components, steps, connections, records and publications; one reports pages checked, clean and drifted. A reader can reproduce the first two by running the suite, the type checker and the reference build.

The numbers belong to the checkout. Test duration and counts vary with the machine and dependency versions; the pass/fail result and the measured pyright error count are the stable claims. The reference counts depend on the reference project and the selected planners; they are not a scale benchmark. Pyright analyses the package and two authoring fixtures, not all of `tests/`, not `reference_project/` and not `legacy/`. The Open Targets suite belongs to another checkout and is not evidence about this one.

A doc/code disagreement is evidence to record, not to smooth over. If a page claims zero pyright errors and the same run reports one error in `kg_build_system/api.py`, the measured count is the claim and the page is a drift candidate. If a page states 259 tests and the checkout reports 354, the difference is a measurement, not a rounding error. A reader should quote the source commit beside every count and rerun the command before repeating it.

The same discipline applies to the documentation build. A broken link, a page outside the navigation or a malformed front matter field is a documentation defect. A green documentation build proves that the links resolve and the structure validates; it does not prove that a sentence is true.

## Drift is a reason to look

Every page names one to five source paths and a `verified` date. Drift is the latest commit touching any of those sources after the verified date. A page with no later source commit is clean. A page with one is a review candidate.

A review candidate is not automatically false. The commit may touch an unrelated line, reformat a file or move a test. The response is to regenerate the evidence, re-read the source and then either correct the claim or move the verified date. Moving the date to silence drift without a check defeats the mechanism.

Drift distinguishes code sources from documentation sources. A path under the package, the tests, the reference project or a packaging file is a code source. A documentation path is a cross-reference: it does not trigger code drift, and it is reviewed through the link and its own verified date. Generated blocks are measured when they are generated; they do not inherit `verified`. An untracked source path counts as unverified.

The drift block is a measurement with its own limits. A commit date is not a semantic diff, only named sources are watched, and a clean block proves no source commit is newer, not that the claim is true. Git history can be rewritten. A page whose sources are all untracked never shows drift. The signal is a reason to look, not a verdict.

## A green build is not a design review

The tests, the type checker, the reference build and the documentation check are a strong evidence set. They prove that the named refusals exist, that the public path composes, that the analysed types hold and that the links resolve. They do not prove that the interface is right.

A design review asks different questions. Does the change belong to this responsibility, or does it need "and" in its purpose? Does it add a public name that another package must depend on? Does it add a dependency edge, and in which direction? Does it change what an author writes? Does it delete a feature without a compatibility path? Which contract test guards the new interface? What does the verification command show?

Those questions are answered by the interface delta, not by the diff. The interface is the review surface because implementation is replaceable behind it. A green build can accompany a wrong boundary, a duplicated model, a private helper in an interface zone or a module that computes the wrong relation. The build makes the refusal visible; the reviewer decides whether the refusal is the right one.

The consensus module shows the split. Its tests can prove that a supported object wins, that a tie warns, that provenance survives and that the exact kind is unique. They cannot prove that a vote belongs in the plan, that the threshold belongs in the payload or that a tie should warn rather than fail. Those are design decisions, and they are reviewed as decisions.

## Where the argument continues

Part IV ends with the same claim it started with: the kernel defines jobs, the distribution supplies one set of workers, and the evidence states what that set does and does not do. The appendices carry the exact material behind the argument.

- Requirements and their evidence: [extension specification](/appendix/spec/extension) and [architecture specification](/appendix/spec/architecture).
- Exact public names, documents, failures and the glossary: [API reference](/appendix/reference/api).
- Internal interfaces, package tree and contract tests: [system design](/appendix/developer/system-design) and [testing](/appendix/developer/testing).
- Protocols, model values and boundaries: [kernel protocols](/appendix/kernel/protocols), [kernel model](/appendix/kernel/model) and [kernel boundaries](/appendix/kernel/boundaries).
- Architecture, contracts, limits, decisions, verification and drift: [architecture review](/appendix/review/architecture), [contracts](/appendix/review/contracts), [limits](/appendix/review/limits), [decisions](/appendix/review/decisions), [verification](/appendix/review/verification) and [drift](/appendix/review/drift).
- The distribution as a whole and the design rationale: [framework](/appendix/framework/index) and [design in semantics](/appendix/philosophy/design-in-semantics).

The subject index and the appendix map begin at [the appendix index](/appendix/index).

## Next

[Appendix index](/appendix/index) — the specifications, reference, developer interfaces and review evidence behind the book.
