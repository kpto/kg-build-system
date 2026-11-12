---
title: Anti-patterns
summary: "Design smells that pass the compiler and fail the model, with the move that corrects each one."
section: philosophy
order: 70
status: normative
verified: 2026-11-10
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - reference_project/
---

> [!lede]
> An anti-pattern here is not a crash. It is a design that compiles, executes and publishes, and still fails the reader. The compiler checks structure; this page names the structure that should have been intended.

## What it is

- **Source-shaped graph** — nodes mirror tables; properties mirror columns; names are `Row1`, `col_a`. **Move:** start from the consumer and the domain noun; let the source supply it.
- **Purpose-free graph** — no `Graph`; every declaration is locally reasonable; no published “why”. **Move:** add one `Graph` with a purpose and claims, or record the absence as a limit.
- **Semantics as comment** — the reason lives in a docstring, a comment or a ticket. **Move:** put the claim in `Semantics`; keep the docstring for developers.
- **SQL-named model** — edges named `JOIN`, projections named after expansions. **Move:** name the assertion and the grain; keep SQL names in the plan.
- **Fat binding** — joins, expansions and defaults hide inside `bind=`. **Move:** move the grain to a projection; keep the binding a total mapping.
- **Projection dumping ground** — one projection “does everything” and four bindings read it. **Move:** name the grain each binding needs; split the projection.
- **Orphan semantics** — a frame contradicts the purpose, or a limitation sits at the top. **Move:** move the statement to the level where it is true; change the design if it conflicts.
- **Limit-free graph** — every absence is implicit; the graph claims more than it can answer. **Move:** add the limitation under the frame where it holds.
- **Plan-first design** — the planner composition is designed before the topology. **Move:** design the graph; choose planners afterwards.
- **Model-the-file** — nested JSON becomes nested properties or a 1:1 tree of nodes. **Move:** model the domain; flatten only what the consumer needs.
- **Defaulted identity** — `build_key=row.id.default_to("unknown")`. **Move:** drop the row or fail; a placeholder collapses distinct records into one identity.
- **Over-modelled schema** — every column becomes a property; every join becomes an edge. **Move:** model what the consumer must know; leave the rest in the source.
- **Composition as procedure** — a dependency list, producer barrier, producer-enumerating consumer or phase-as-chain. **Move:** declare ports and patterns; let the assembler derive connections.
- **Exact artifact as an ordering device** — a consumer pins one type only to make its producer run first. **Move:** use assembly priority; an exact input seals only when one producer owns the type.
- **Same-type producer ambiguity** — two producers publish one type and priority is expected to choose. **Move:** distinguish the type or replace the producer; priority is not a tie-break.

## Rules

- Test each smell against the consumer: can a reader answer “what is this and why?” without opening the pipeline?
- Prefer a missing declaration to a misleading one. A named limit is better than invented precision.
- Keep the design above the binding and the SQL below it. A technical name is fine in a plan step; it is a leak in the blueprint.
- A source-shaped graph is legitimate only when the source is the domain and you say so. It is a choice, not a default.
- A projection may expand several levels; a binding may not hide that expansion. The seam is thin by construction.
- A workflow composes by artifact type; a dependency list, a producer-naming barrier or a consumer that enumerates producers is a composition smell, not a design.
- An anti-pattern is a review finding, not a compiler error. Do not expect `create_blueprint` to catch it.
- When two smells conflict, keep the one that preserves identity and meaning; drop the one that only preserves convenience.

## Example

A defaulted key is the clearest identity anti-pattern:

```python
# collapses every missing site into one record
build_key=row.site_id.default_to("unknown")

# keeps identity honest: the row cannot ground a site
build_key=row.site_id.alter_rows().drop_null()
```

The first compiles. It also makes every missing site the same site. The second drops the rows it cannot identify; that is a visible data decision, not a silent merge.

## Limits

- These are smells, not proofs. A graph can use one and still be the right design for its consumer.
- Some sources are genuinely flat and file-shaped; modelling them directly can be correct.
- The compiler cannot detect any of these. [Review top-down](/appendix/philosophy/review-top-down) is the detection method.
- A smell is not a defect in the framework. It is a mismatch between the language’s expressive power and the design’s use of it.
- No checklist replaces reading the blueprint and the meta-graph.

## Next

[Author](/book/part-2/index) — apply the lens to the declarations.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md` |
