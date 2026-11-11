---
title: Verification specification
summary: Verification measures this checkout, records its doc/code drift and refuses to turn a green run into a design verdict.
section: spec
perspective: spec
subject: verification
spec: SPEC-016
order: 160
status: normative
verified: 2026-11-11
sources:
  - FRAMEWORK_STATE.md
  - pyproject.toml
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/api.py
  - docs/book/part-3/04-quality-and-failure.md
evidence:
  - tests/test_reference_build.py
  - tests/kernel/test_runtime_events.py
  - tests/test_architecture.py
  - tests/test_public_docstrings.py
  - tests/test_public_api.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification" class="active">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** MUST run `uv run pytest -q` before quoting any test or subtest count. The result and the count belong to the measured checkout and its source commit.
- **R2.** MUST run `uv run pyright` and report the measured error count. The checkout reports one error, in `kg_build_system/api.py`; a claim of zero contradicts the measurement.
- **R3.** MUST run `python3 scripts/kb.py check` and build the documentation with `npx quartz build -d ../kg-build-system/docs`. A structural pass in one does not verify the other.
- **R4.** MUST NOT restate a measured count as a product guarantee. Test and subtest counts, duration and reference counts are checkout properties.
- **R5.** MUST keep each measured table in a generated block owned by `scripts/kb.py generate`; prose MAY cite a value, but the block is the record and its content MUST NOT be hand-edited.
- **R6.** MUST NOT claim continuous integration. The source repository has no CI configuration; every check is manual.
- **R7.** MUST record every docs/code disagreement as a drift row naming the doc claim and the measured source value. It MUST NOT silently choose a winner.
- **R8.** MUST classify the Open Targets suite as external evidence. It exercises another checkout and is not a check on this repository.
- **R9.** MUST NOT treat a green pytest, pyright or documentation build as a design review. The run proves execution, types and page assembly, not grain, duplicate keys, dangling edges or model quality.
- **R10.** MUST state each limit as a normative boundary with its refusal. Removing a boundary requires the documentation change in the same change.
- **R11.** MUST attribute each failure message to the stage that raises it: authoring, linking, blueprint validation, document decoding, compile/assembly or execution. The catalogue belongs to the stage.
- **R12.** SHOULD quote the source commit and verification date beside every count so a reader can reproduce the measurement.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_reference_build.py` | The reference blueprint compiles, the report succeeds, the three publication types appear, and the plan and report are written. |
| `tests/kernel/test_runtime_events.py` | Pipeline events, halted runs, provider disposal and listener isolation are exercised through `WorkflowRuntime`. |
| `tests/test_architecture.py` | Leaf zones, public surfaces and the import matrix match the package tree. |
| `tests/test_public_docstrings.py` | Every public function and class method carries an `Example`, with named defects as exceptions. |
| `tests/test_public_api.py` | The lazy export table exposes callable wrappers from public surfaces only. |

## API

| Public name | Role |
| --- | --- |
| `uv run pytest -q` | Runs `tests/`; the pass/fail result and counts describe the checkout. |
| `uv run pyright` | Checks `kg_build_system` plus two authoring fixtures; reports one error in `api.py`. |
| `npx quartz build -d ../kg-build-system/docs` | Builds the documentation site; broken links fail the build. |
| `scripts/kb.py generate` | Rewrites generated blocks; the `check` command validates markers, links and word limits. |
| `WorkflowReport` | Frozen result of `execute`: published artifacts, failures and provenance. |
| `published_artifacts` | Tuple of `PublishedArtifact`; final artifacts only, with intermediate records excluded. |
| `recovered_failures` | Tuple of `Failure` active before a publishing step; it does not block success. |
| `unresolved_failures` | Tuple of `Failure` still active at the end; it blocks success. |
| `succeeded` | `not unresolved_failures`; it can be true while recovered failures remain. |

## Limits

- Counts and duration vary with the machine and dependency versions. The pass/fail result and the pyright error count are the stable claims.
- Pyright analyses `kg_build_system` plus two authoring fixtures, not all of `tests/`, `reference_project/` or `legacy/`.
- No CI means generated blocks can be stale between manual runs.
- Reference counts depend on the reference project and selected planners; they are not a scale benchmark.
- The Open Targets suite belongs to another checkout and is evidence about that project.
- The report stores no traceback, and a successful report records publication rather than grain, duplicate keys or dangling edges.
- A docs/code gap can be stale prose rather than a code defect; read the source before changing either side.

## Rationale

A verification claim carries a date and a commit. [Explainability is authored](/appendix/philosophy/explainability-is-authored): the generated block names the command, while the page states the claim a reader may test. [Review top-down](/appendix/philosophy/review-top-down): start from the claim, descend to the artifact, then to the command and its source. A green run answers only the question that command asks, so it cannot certify a design.

## Next

Read the [verification subject](/appendix/subjects/verification) for the measurement-level view.
