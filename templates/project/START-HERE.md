# Start here: the intention interview

Answer these before writing a declaration. The template's fixture already
answers them for a conformance example; replace those answers with yours.

## 1. Why does this graph exist?

- What decision or question should it support?
- For whom?
- What is it explicitly not for?

> The fixture's answer: exercise the template's layers so a new project starts
> with a passing build. Replace this.

## 2. What exists?

- Which record kinds does the graph assert?
- For each record, what does one record mean?
- What identifies it, and what may a consumer not infer from it?

> The fixture's answer: items with nested parts. Replace this.

## 3. What supplies them?

- Which domain relations does the graph read?
- For each relation: what is one row, what identifies it, and what does it not
  guarantee?
- Which relation is reused by several records?
- Which computation is private and should be a stage rather than a relation?

> The fixture's answer: an `items` source relation and an `item_parts` derived
> relation with a private `part_rows` stage. Replace this.

## 4. How does each relation fulfil each record?

For each binding:

- Which record use does the relation answer?
- At what grain and identity?
- What coverage does the relation actually supply?
- Where does it fall short?

> The fixture's answer: one item row is one item; one item-part row is one part
> and one HAS_PART edge. Replace this.

## 5. What is the first slice?

Write the graph declaration first, then one asset, one source relation, one
record and one binding. Run `uv run pytest`. Do not add a second relation until
the first slice passes.
