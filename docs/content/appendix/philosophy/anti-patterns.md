---
title: Anti-patterns
summary: "Design smells that pass the compiler and fail the model, with the move that corrects each one."
section: philosophy
order: 70
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/intent.md
  - reference_project/build.py
---

> [!lede]
> An anti-pattern here is not a crash. It is a design that compiles, executes and publishes, and still fails the reader. The compiler checks structure; this page names the structure that should have been intended.

## What it is

- **Source-shaped graph** — nodes mirror source relations; properties mirror columns; names are `Row1`, `col_a`. **Move:** start from the consumer and the domain noun; let the relation supply it.
- **Purpose-free graph** — no `Graph`; every declaration is locally reasonable; no published “why”. **Move:** add one `Graph` with a purpose and claims, or record the absence as a limit.
- **Meaning as comment** — the reason lives in a docstring, a comment or a ticket. **Move:** put the claim in `Meaning`; keep the docstring for developers.
- **SQL-named model** — edges named `JOIN`, relations named after expansions. **Move:** name the assertion and the grain; keep SQL names in the plan.
- **Relation purpose under the graph** — a relation purpose is written as a narrower copy of the graph purpose. **Move:** state the relation's domain purpose; let the binding state how it serves this graph.
- **Record-shaped relation** — a published relation names the record's properties, key or endpoints. **Move:** remove the record nouns; publish the domain grain, and let the binding map it.
- **Fat binding** — joins, expansions and defaults hide inside `bind=`. **Move:** move the grain to a `DerivedRelation`; keep the binding a total mapping plus a fulfilment statement.
- **Vacuous binding** — a one-to-one rename that adds no grain, identity, coverage or meaning decision, because the relation already chose the record's shape. **Move:** move the record decisions back to the record; keep the relation domain-level.
- **Stage leak** — a binding or another package imports a private `Stage`, or a stage carries a contract purpose. **Move:** bind the published `DerivedRelation`; keep the stage inside its package.
- **DerivedRelation dumping ground** — one relation “does everything” and four bindings read it. **Move:** name the grain each binding needs; split the relation or add a stage.
- **Orphan meaning** — a purpose contradicts the side it belongs to, or a limitation sits outside a purpose. **Move:** move the statement to the level where it is true; change the design if it conflicts.
- **Limit-free graph** — every absence is implicit; the graph claims more than it can answer. **Move:** add the limitation under the purpose where it holds.
- **Model-the-file** — nested JSON becomes nested properties or a 1:1 tree of nodes. **Move:** model the domain; flatten only what the consumer needs.
- **Defaulted identity** — `build_key=row.id.default_to("unknown")`. **Move:** drop the row or fail; a placeholder collapses distinct records into one identity.

## Rules

- Test each smell against the consumer: can a reader answer “what is this and why?” without opening the pipeline?
- Prefer a missing declaration to a misleading one. A named limit is better than invented precision.
- Keep the design above the binding and the SQL below it. A technical name is fine in a plan step; it is a leak in the blueprint.
- A source-shaped graph is legitimate only when the source is the domain and you say so. It is a choice, not a default.
- A relation may expand several levels through private stages; a binding may not hide that expansion.
- A relation is record-agnostic and a binding is its fulfilment. If the relation already made the record's decisions, the axes have collapsed.
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
- A smell is not a defect in the framework. It is a mismatch between the language's expressive power and the design's use of it.
- No checklist replaces reading the blueprint and the meta-graph.

## Next

[Author](/book/part-2/index) — apply the lens to the declarations.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md` |
