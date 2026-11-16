# Agent notes

In this file and the directory directives, the key words MUST, MUST NOT, SHOULD,
SHOULD NOT and MAY are used as defined in RFC 2119.

## The model in one screen

A graph is an argument, not a pipeline. It has two axes:

```text
records (graph/)                         relations (relation/)
what the graph asserts                   what the domain contains
  purpose, claims, limitations             contract: definition + meaning
        ▲                                        │
        └──────────── binding ───────────────────┘
                     fulfilment
```

- A **purpose** is one expected use; a **claim** is a contextless assertion; a
  **limitation** is what the purpose does not authorize. A definition is a claim;
  a prohibition is a limitation. Do not invent a purpose to fill a shape.
- A **relation is not an operator**. State it with no graph nouns and no operator
  verbs. A join or a filter is a row source; keep it private.
- A **binding states the fulfilment**: name the record's use in a clause, then say
  how the relation answers it — grain, identity, coverage — and where it falls
  short. "Supply X edges from each row's y" is a recipe, not a fulfilment.
- A **published relation must not know the record**. If it names the record's key,
  properties or endpoints, it is a stage in disguise.
- The **declaration is the product**; the build is replaceable.
- **Prefer inline.** Write an expression at the field or declaration that uses
  it. A one-use module-level helper, selection alias or meaning constant is
  forbidden. Name a value only when it is itself a declaration, or when several
  declarations genuinely share it.
- **Inline the meaning.** `Meaning`, `Contract` and `FieldDefinition` belong at
  the declaration. Do not introduce a module-level meaning constant, a lookup
  table or a helper that assembles purpose, claim or limitation text.
- **A declaration has no docstring.** Its `Meaning` is its documentation. A
  module docstring MAY state the file's role, but it MUST NOT restate the
  declaration's meaning.

## First task

1. Read `START-HERE.md` and answer it. Do not write a declaration first.
2. Read the `README.md` in the directory you are about to change.
3. Replace the conformance fixture, or keep its shape and change the names and
   meanings.
4. Run `uv run pytest`. A failing philosophy check means the model, not the test.

## Reading order

1. `START-HERE.md` — the intention interview.
2. `README.md` — the project and the fixture.
3. `graph/README.md`, `relation/README.md`, `binding/README.md` — the axes.
4. `tests/test_philosophy.py` — the gate you must pass.
5. The kg-build-system book for the long argument.

## Rules that are easy to get wrong

- A source field declares a value type; it never declares absence. Source access
  is nullable; a computed output follows its selection.
- A derived relation is a package: `relation.py` publishes, `_stage.py` composes.
- The identity in a `Definition` names outputs and must be true of the plan.
- A binding MUST read a published relation, never a stage.
- A missing value is a design decision, not a default hidden in a binding.
- A declaration MUST attach its meaning inline. A meaning that lives in a table
  or a helper is not attached to the declaration it governs.
- A one-use expression MUST be inlined. A module-level selection used by one
  stage or relation is a second place to read, and it hides the grain.

The stranger test: could a reviewer who has not seen the code say what a
declaration is for, what it asserts and what it excludes? If not, the meaning is
missing.
