# Start here: the design record

Answer these before writing a declaration, and **keep the answers**. This file
is the model a cold reader reads before the code: the directory briefs and the
declarations assume it. The project starts with placeholder answers, and
`uv run pytest` fails until this file and the graph declaration are answered.

## 1. Why does this graph exist?

- What decision or question should it support?
- For whom?
- What is it explicitly not for?

> Replace this with the project's answer.

## 2. What exists?

- Which record kinds does the graph assert?
- For each record, what does one record mean?
- What identifies it, and what may a consumer not infer from it?
- Which reference tables or controlled vocabularies are records, and which are
  values? If a consumer needs a name, category or threshold, where does it live?
- If a site and a station, or two similar kinds, share a use, is that a category,
  a template, or two unrelated records? State why.

> Replace this with the project's answer.

## 3. What supplies them?

- Which domain relations does the graph read?
- For each relation: what is one row, what identifies it, and what does it not
  guarantee?
- Which relation is reused by several records?
- Which computation is private and should be a stage rather than a relation?
- Which source format needs an adapter, and what schema, null assumptions, grain
  and identity must that adapter preserve without transforming?
- Which value calculation is missing from the shipped operation set, and what
  are its argument and result types?
- Which calculation changes the row count or grain, and therefore needs a
  relation operation and a matching `Definition` grain?
- For each threshold or comparison, which direction is adverse: a minimum or a
  maximum? The number alone does not say.
- What makes a row a valid measurement? If a row carries a blank value, is it a
  reading, an analysed sample, or neither? Which count would a reader expect?
- Which source is semi-structured or irregular, and which nested or optional
  fields must be preserved rather than flattened or inferred?

> Replace this with the project's answer.

## 4. How does each relation fulfil each record?

For each binding:

- Which record use does the relation answer?
- At what grain and identity?
- What coverage does the relation actually supply?
- Where does it fall short?
- What can a cold reader verify from the graph alone: which result or reading
  supports each conclusion, and where is that path?

> Replace this with the project's answer.

## 5. What is the first slice?

The first slice is the smallest set of record and relation kinds that makes one
real question explainable end to end; it is not a fixed count. Write the graph
declaration and its meanings first, then the one relation and binding that
answer the question. Run `uv run pytest` and `uv run pyright`. A project with no
derived relation, stage, adapter or operation is valid when the domain does not
need one.
