# Tests

**BLUF:** The tests are the philosophy gate, not a coverage target.

## Situation

The declarations can be structurally valid and still state a recipe, a
record-shaped relation, or no purpose. The gate reads the declarations and the
blueprint to refuse those shapes.

## Mission

Own `test_philosophy.py` and the build smoke test. Do not own declarations.

## Execution

- `test_philosophy.py` MUST check facades, import direction, stage privacy,
  derived contracts, binding purposes, the graph purpose and the design record.
- `test_project.py` MUST prove the blueprint and plan compile and that the empty
  graph builds. It reads the project's own inputs; it does not edit them.
- A rule MUST have a test. A test MUST NOT only repeat a declaration's text.
- `START-HERE.md` is the design record, not a comment. The gate is red until its
  placeholders and the graph purpose are replaced; that is the first task.
- `uv run pytest` on a fresh project fails two tests on purpose. Do not delete
  them to get a green run.
- Tests for a value operation, adapter or relation operation are added with the
  feature. The conformance example (`kbs init --fixture`) shows those tests.

## Support

Reads `project.manifest` and the framework DTOs. No network.

## Gate

`uv run pytest` and `uv run pyright`; `uv run kbs check --project project`
prints the authored argument for review. A failure is a model change; if a check
is wrong, change the check and say why.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
