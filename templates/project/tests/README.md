# Tests

**BLUF:** The tests are the philosophy gate, not a coverage target.

## Situation

The declarations can be structurally valid and still state a recipe, a
record-shaped relation, or no purpose. The gate reads the declarations and the
blueprint to refuse those shapes.

## Mission

Own `test_philosophy.py` and the smoke test. Do not own declarations.

## Execution

- `test_philosophy.py` checks facades, import direction, stage privacy, derived
  contracts, binding purposes and the graph purpose.
- `test_project.py` proves the blueprint and plan compile and the fixture builds.
- Add a test when you add a rule. Do not add a test that only repeats a
  declaration's text.

## Support

Reads `project.build` and the framework DTOs. No network.

## Gate

`uv run pytest` and `kbs check`. A failure is a model change; if a check is
wrong, change the check and say why.
