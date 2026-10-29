# Writing style for this guide

- Write for a competent Python developer who has never seen kg-build-system.
  Start from why and what for: the problem the author has, what the framework
  promises and what changes for them. Explain the idea before the API.
- Preserve the framework's values: semantics as contract, explicit assumptions,
  typed authoring, reproducible builds, and separation of meaning from
  execution.
- Write from the author's perspective. Explain an internal mechanism only when
  it changes what the author writes or observes; do not describe internals for
  their own sake.
- Prefer one continuous explanation with code examples over a list of function
  signatures. A reference table is fine when the reader already understands the
  concept.
- Every code block must use the current public API from `kg_build_system` and
  should be valid Python. Keep examples small and realistic.
- State null behaviour and row behaviour explicitly. Those are the two things
  authors get wrong.
- Use admonitions for warnings and rules:
  `!!! warning "..."`, `!!! note "..."`, `!!! tip "..."`.
- Link to related pages with relative Markdown links.
- A page covers one concept. Split when it covers two; length follows the detail
  an author needs. Do not duplicate another page; link to it.
- Use sentence case headings. Tables for short comparisons.
- Do not invent features. If unsure, inspect the framework source or
  `reference_project/` and omit rather than guess.

## Teach, don't just specify

- Depth is welcome. Do not simplify by omitting what an author needs; make it
  readable by structure, order and examples.
- Write as a teacher walking beside the reader. Introduce the problem a feature
  solves before its syntax.
- Carry one running example through a page. Return to it as each new idea is
  added, so the reader sees the graph grow rather than a sequence of unrelated
  snippets.
- Explain *why* a rule exists in terms the author can act on: what goes wrong
  without it, what error appears, what changes in the graph.
- Use short narrative paragraphs between examples. Do not dump a signature and
  leave the reader to infer when to use it.
- End each page with a short "What to remember" list and a link to the next
  natural page.
- Prefer a worked explanation over a shallower summary.
