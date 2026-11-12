# Writing style for this book

## The book is the primary object

- Write for a competent Python developer who has never seen kg-build-system.
  Start from the problem the author has, then the model, then the API.
- The book is read in order. Each chapter carries one movement of the argument
  and assumes the previous chapter, but it restates a rule when the reader needs
  it rather than sending them to another page.
- Repetition is allowed. A chapter may explain selection, grain or binding in its
  own words even when an earlier chapter or an appendix already did. The
  appendix states the rule exactly; the chapter explains why it matters here.
- Do not split a subject into a hub, a guide, a spec and a view unless the reader
  has a reason to switch. A chapter can cover several related ideas when they
  form one argument.
- Order an explanation from meaning and design to data and implementation where
  the model permits. Say that the order is a reading order, not a claim that a
  real project evolves one way.

## Appendices are for lookup

- Exact signatures, requirement tables, document shapes and refusal messages
  belong in `docs/content/appendix/`. They are written for checking, not for reading
  from front to back.
- An appendix may repeat a rule from the book. That is deliberate: the book
  explains it, the appendix states it precisely.
- Do not add a second explanation of the whole model to an appendix. Link back to
  the chapter that carries the argument.

## Voice

- Write as one author walking beside the reader.
- Present tense. State the current model as if it were the only one.
- No "currently", "recently", "now", "we", "our", "TODO" or "FIXME".
- Do not write a changelog or compare the book with an older version. That
  belongs in the change report.
- Name the public type when the reader can use it. Explain an internal mechanism
  only when it changes what the author writes or observes.
- State null behaviour, grain and refusal explicitly. Those are the three things
  authors get wrong.
- A green test run is evidence, not a design review.

## Chapters

- Start with a concrete question, problem or example.
- Use H2 headings that state a claim or a turn in the argument. Do not use
  `What it is`, `Rules`, `Example`, `Limits` as a fixed template.
- Carry one running example through a part. Return to it as the idea grows.
- Include code only when it is valid against the current public API. Prefer a
  small, real declaration over a signature dump.
- End with `## Next` and exactly one link to the next chapter.
- A chapter is usually 1,800–3,200 words excluding code and tables. Length
  follows the argument; do not compress by deleting what the reader needs.

## Language and links

- Use sentence case headings.
- Use Quartz callouts: `> [!note]`, `> [!warning]`, `> [!tip]`.
- Use absolute site links such as `/book/part-2/02-values-and-nullability` and
  `/appendix/reference/api`. A link to a future appendix is allowed only when the
  appendix exists in the same change.
- Do not link to an old guide route (`/author/...`, `/pipeline/...`,
  `/operate/...`, `/start/...`). The book replaced those routes.

## Teach, don't just specify

- Introduce the problem a feature solves before its syntax.
- Explain why a rule exists in terms the author can act on: what goes wrong
  without it, what error appears and what changes in the graph.
- Use short narrative paragraphs between examples. Do not dump a signature and
  leave the reader to infer when to use it.
- Prefer a worked explanation over a shallower summary. Depth is welcome.
