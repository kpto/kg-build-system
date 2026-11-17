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
- `test_project.py` MUST prove the blueprint and plan compile and the fixture
  builds.
- `test_input_adapter.py` MUST prove the hello-world adapter has one no-input
  step, provides the declared relation and reads back its one row.
- `test_hello_expression.py` MUST prove both authoring forms of a project value
  operation and its use in the fixture build.
- `test_relation_operation.py` MUST prove a project relation operation compiles,
  executes and publishes through a matching `DerivedRelation`.
- A rule MUST have a test. A test MUST NOT only repeat a declaration's text.

## Support

Reads `project.manifest` and the framework DTOs. No network.

## Gate

`uv run pytest` and `kbs check`. A failure is a model change; if a check is
wrong, change the check and say why.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
