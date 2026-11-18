# Tests

**BLUF:** The tests are the philosophy gate, not a coverage target.

## Situation

The declarations can be structurally valid and still state a recipe, a
record-shaped relation, or no purpose. The gate reads the declarations and the
blueprint to refuse those shapes.

## Mission

Own `test_philosophy.py`, the smoke test and the input-adapter contract test. Do
not own declarations.

## Execution

- `test_philosophy.py` MUST check facades, import direction, stage privacy,
  derived contracts, binding purposes and the graph purpose.
- `test_project.py` MUST prove the blueprint and plan compile and the project
  builds. It reads the release files as inputs; it does not edit them.
- `test_input_adapter.py` proves the example adapter only while the example is
  present. A project with no custom source format may delete it.
- `test_hello_expression.py` proves both authoring forms of a value operation
  only while the project has a value operation. A project with no missing value
  calculation may delete it; do not invent an operation to keep a test.
- `test_relation_operation.py` proves a relation operation only while the
  project has one. A project with no grain-changing calculation may delete it;
  do not invent an operation to keep a test.
- A rule MUST have a test. A test MUST NOT only repeat a declaration's text.
- `START-HERE.md` is the design record, not a fixture; a test MAY check that its
  placeholder answers were replaced, but a new project starts with the fixture
  and a passing gate.

## Support

Reads `project.manifest` and the framework DTOs. No network.

## Gate

`uv run pytest` and `uv run pyright`; `uv run kbs check --project project`
prints the authored argument for review. A failure is a model change; if a check
is wrong, change the check and say why.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
