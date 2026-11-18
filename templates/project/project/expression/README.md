# Expression operations

**BLUF:** A project-local expression operation is one `OperationSpec` plus a
typed `Operation` handle. The engine emitter is a module; the composition is
`manifest.py`.

## Situation

The shipped expression vocabulary is a baseline. A project adds a domain
calculation when the calculation is part of the value language: one row in, one
value out, with no change to the row count.

## Mission

Own project-local `OperationSpec` declarations and their typed handles. Do not
own relation shapes, records or engine emitters.

## Execution

- One operation MUST own one file and state `name`, `arity`, `arguments` and
  `result_type` in an `OperationSpec`.
- The typed handle MUST carry the argument and result types:
  `hello: Operation[[Selection[str]], str] = Operation(HELLO)`.
- Both authoring forms MUST use the same handle:
  `hello(value)` and `value.custom_op(hello)`.
- The operation MUST be a value operation. A row effect, a grain change or a
  relation aggregate is not an expression operation; use a `DerivedRelation`, a
  `Stage`, or the relation-operation guide in `../modules/count_rows.py`.
- A threshold is not just a number. If a reference supplies a bound but not the
  adverse direction, make the direction a named operation or a stated assumption
  and say which records carry it. Do not compare every analyte or parameter with
  the same operator; a dissolved-oxygen minimum and a turbidity maximum are not
  the same calculation.
- The engine emitter MUST live in `modules/` and be composed into the engine in
  `manifest.py`. It MUST NOT import the project's declarations.
- The language MUST be composed with the operation set:
  `ExpressionsLanguage((*DEFAULT_OPERATIONS, HELLO))`. There is no registry and
  no `register_operation`.
- A declaration MUST NOT have a docstring; the spec's names and argument
  descriptions are its vocabulary. The computed field states the value meaning.

## Support

Imports the framework only. Read `../modules/README.md` for the emitter, then
`../manifest.py` for the composition.

## Gate

`tests/test_hello_expression.py` and the framework typecheck fixture. An
operation whose result is not used at a field or declaration is an unused
vocabulary item, not a relation.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
