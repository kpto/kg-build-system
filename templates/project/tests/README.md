# Tests

**BLUF:** The tests are the philosophy gate, not a coverage target.

## Situation

The declarations can be structurally valid and still state a recipe, a
record-shaped relation, or no purpose. The gate reads the declarations and the
blueprint to refuse those shapes.

## Mission

Own `test_philosophy.py` and the smoke test. Do not own declarations.

## Execution

- `test_philosophy.py` MUST check facades, import direction, stage privacy,
  derived contracts, binding purposes and the graph purpose.
- `test_project.py` MUST prove the blueprint and plan compile and the fixture
  builds.
- A rule MUST have a test. A test MUST NOT only repeat a declaration's text.

## Support

Reads `project.build` and the framework DTOs. No network.

## Gate

`uv run pytest` and `kbs check`. A failure is a model change; if a check is
wrong, change the check and say why.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
