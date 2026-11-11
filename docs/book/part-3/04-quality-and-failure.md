---
title: "16. Quality, failures and debugging"
summary: "What the quality modules guarantee, and how to find the stage that refused a build."
section: book
perspective: book
part: III
chapter: 16
order: 34
status: normative
verified: 2026-11-11
sources:
  - docs/book/part-3/04-quality-and-failure.md
  - docs/book/part-3/04-quality-and-failure.md
  - docs/appendix/reference/failures.md
  - kg_build_system/distribution/modules/merging/service/_private/planner.py
  - kg_build_system/distribution/modules/conflict_validation/service/_private/executor.py
---

Two source relations describe the same site. One records its inventory label, the other its monitoring label. Both bind to the same `SiteNode` component and produce a row with the build key `site:1`; the labels differ. The build compiles, every step succeeds, the file target writes one record for the site, and `report.succeeded` is true. The label in that record is the alphabetically earlier string, because the merge step took `min()` of each property. Nothing in the report says a choice was made.

That is the quality boundary in one example. The framework ships three record modules — deduplication, merging and conflict validation — and each makes a narrow, exact claim. They are ordinary planners composed into the plan, not a validation layer wrapped around the build. A build can be structurally correct, execute without an unresolved failure, and still carry a record that no source row contained.

## A successful report can still contain a wrong graph

Recall what a report records. `execute` returns a `WorkflowReport` with the artifacts the plan published, the failures that remained active at a publishing step, the failures that did not, and the plan's provenance. `report.succeeded` is exactly `not report.unresolved_failures`. It is a statement about publication, not about truth.

The supplied quality modules sit between bound records and an output target. Deduplication and merging rewrite records; conflict validation reports disagreement and forwards records only when the configuration lets the run continue. All three consume and produce the same graph-record artifact types, so they compose with the core planners and with each other. A module does not know the whole graph, and it does not reach into a target. It reads one component's record stream, or every bound component's stream, and emits steps with exact instruction kinds.

The precision matters because the three names suggest a progression that the implementations do not provide. Deduplication is not key resolution. Merging is not reconciliation. Conflict validation is not a constraint that holds everywhere. Read each as a separate claim.

## Deduplication removes repeats, not disagreements

`DeduplicationPlanner()` emits one step per bound component. The executor materializes:

```sql
SELECT DISTINCT * FROM <input relation>
```

The star is the whole row. A duplicate must match the build key, every declared property, both endpoint keys on an edge, and `_kg_binding_symbol`. Only then does one of the two rows disappear. Two rows with the same build key and different labels are not duplicates, so both survive. Two rows whose only difference is the binding symbol that produced them also both survive, because that column is part of the comparison.

The binding symbol is the column that records which binding contributed a record. It exists because several bindings may target one component, and the core planners union their records into a single stream. Deduplication keeps that provenance in the comparison, which is why it removes only rows that are identical as records, not rows that describe the same key.

There is no survivor policy, no key grouping, no fuzzy matching and no cross-component pass. Deduplication has no configuration. A repeated key whose values differ is left for another module, or for a person, to resolve. Its guarantee is therefore strong where it applies and silent where it does not: exact repeats vanish, and every substantive disagreement remains.

## Merging chooses a record; it does not reconcile one

`MergingPlanner(MergingConfiguration(components=(...)))` emits one step per component in scope. The scope is a tuple of concrete `Node` or `Edge` classes, not component-name strings. `components=None` means every bound component. An abstract class, a template or a non-class raises `TypeError: components must be concrete Node or Edge classes`. A component named in the scope that is not bound produces no step, because the planner iterates the blueprint's bound record components.

The executor groups by the build key and selects `min()` for every property. For an edge it also selects `min()` for `source_build_key` and `target_build_key`. The select list does not include `_kg_binding_symbol`, so a record that passes through a merge loses that column. A file record that has been merged therefore cannot name the binding that contributed it; a record that has not been merged still can.

Three consequences follow from that one statement of the rule.

First, the surviving record need not match any input row. Each column is minimized independently within the group. If one row has label `alpha` and count `5`, and another has label `beta` and count `3`, the merged record has label `alpha` and count `3`. The pair occurred in no source row. Merging is not row selection with a deterministic winner; it is a column-wise reduction.

Second, endpoints are minimized independently too. An edge group can produce a source key taken from one input row and a target key taken from another. Nothing checks that the pair occurred together, and nothing checks that either key names a node. A merge can therefore create an edge that no source asserted.

Third, null handling follows SQL. `min()` ignores nulls, so a null beside a non-null value does not win and the value survives; a key whose values are all null keeps null. A null versus a value is not presented as a choice, and no failure is raised. For text, the minimum is the collated string order; for temporal values it is the earliest instant. Both are arbitrary semantic choices that the module does not justify.

Merging is sound only for a component whose parallel same-key rows are meant to be one fact. Edge families that deliberately keep parallel facts — several assertions between the same pair, for example — must stay outside the scope. The scope is the only control the module offers, and it is per component. It cannot preserve two intentional rows inside one component; that requires a different planner.

An explicit scope is the safe default, not the default value. `components=None` merges every bound component. Pass the tuple.

## Conflict validation finds disagreement it can see

`ConflictValidationPlanner(ConflictValidationConfiguration(fail_on_error=True))` emits one findings step per property of every bound component, plus one deferred report step. It is not scoped by component.

For each component and property, the executor groups by the build key and runs:

```sql
SELECT "build_key", count(DISTINCT "field") FROM <input>
GROUP BY "build_key"
HAVING count(DISTINCT "field") FILTER (WHERE "field" IS NOT NULL) > 1
```

A finding means one build key holds more than one distinct non-null value for that property. Nulls are filtered out of the count, so one value beside any number of nulls is not a conflict, and null versus value is invisible. The finding records the component, the build key, the property name and the number of distinct values. It does not record the competing values, the rows that carried them, or the binding symbols behind them.

The report step gathers every finding. With no findings it forwards the records and publishes nothing. With findings and `fail_on_error=True`, the step fails with `validation found <n> conflicting non-null value(s)`, publishes the report, and does not forward the records. With `fail_on_error=False`, it publishes the report, forwards the records and succeeds. The report is `ConflictingNonNullValuesReport`, whose `findings` tuple holds `ConflictingNonNullValueFinding` values. A failed run can therefore still carry the report artifact; the report is evidence, not a repair.

`fail_on_error` decides what a disagreement does to the run, not what counts as a disagreement. The blind spots are structural:

| Blind spot | Why |
| --- | --- |
| Null versus value | Nulls are removed from the distinct count. |
| Edge endpoint keys | Endpoints are binding outputs, not declared properties. |
| `_kg_binding_symbol` | The column is not checked. |
| Unbound components | They emit no findings step. |
| Extra columns | Columns outside the declaration are not read. |
| Cross-component or cross-key | No pass compares one component or key with another. |

Nothing here checks that an edge endpoint matches a node key. That failure appears when a consumer imports the graph, not during the build. Nothing checks that a key is unique across components. Nothing compares two components that describe the same real-world subject under different names. A graph that needs any of these checks needs a new planner; the supplied module is not a hook for them.

## Order is part of the guarantee

The planner tuple is the composition order. That sentence is easy to read past, because the modules all speak the same artifact types. It decides which stream each module sees.

Conflict validation must run before merging. Validation reads parallel values; a merge collapses them to one value per key. Run the merge first and the later validation usually finds nothing, not because the data agrees but because the disagreement has already been reduced. Deduplication may sit anywhere among the rewriting planners, because it only removes exact duplicates and cannot hide a differing value. Output planners come last, so each target publishes the records the final rewriting planner produced.

A rewriting planner placed after an output planner can leave two targets reading different streams: the earlier target sees the pre-rewrite records, the later one sees the post-rewrite records. The plan does not warn about this. Keep every rewriting planner before every output planner.

The composition below validates first, deduplicates, merges only the two named components, and then writes the graph:

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import (
    ConflictValidationConfiguration,
    ConflictValidationPlanner,
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MergingConfiguration,
    MergingPlanner,
)

from estate.topology import SiteNode, UnitNode

planners = (
    ConflictValidationPlanner(
        ConflictValidationConfiguration(fail_on_error=False),
    ),
    DeduplicationPlanner(),
    MergingPlanner(MergingConfiguration(components=(SiteNode, UnitNode))),
    FilePlanner(FileConfiguration("graph.jsonl")),
)
plan = compile(planners=planners)
report = execute(plan, output_directory="build")
```

A rewriting planner produces an ordinary output, and assembly refuses an ordinary output that nothing reads. If deduplication is added without a downstream reader, compilation fails with `nothing reads ...`. That refusal is a wiring statement, not a data statement: the planner is doing work nobody consumes.

## A refusal names the stage that raised it

Every refusal belongs to a stage. The stage tells you what kind of thing to change: a declaration, a reference, a planner composition, a stored document, or input data.

| Stage | Typical refusal | First artifact to open |
| --- | --- | --- |
| Authoring | `TypeError` while a declaration is written | The declaration and the value it names |
| Linking | `ValueError` raised while linking, through `create_blueprint` | The declarations and their references |
| Blueprint validation | `ValueError` from `create_blueprint` | The blueprint: graph, data, assets, bindings |
| Document decoding | `ValueError` from a codec | The stored document and its members |
| Compile and assembly | `ValueError` from `compile` | The planner composition; a plan only if compile returned |
| Execution | An unsuccessful report or a raised run error | `build_report.json`, then `workflow_plan.json` |

The order is also the order of evidence. A declaration error never reaches compile. A compile error never writes a report. Read the earliest stage whose artifact exists.

`create_blueprint` validates names and cross-layer references after assembly. It refuses duplicate component names, an edge endpoint that names no node, a relation that names an unknown asset, a binding that targets an unknown component, and a graph declaration without a purpose. Those are blueprint defects. The blueprint document exposes `graph.nodes`, `graph.edges`, `data`, `assets` and `bindings`, and `compile` records that document under `plan.provenance["blueprint"]`, so a compiled plan carries the model that produced it.

`compile` is pure. It reads the blueprint and the planner composition, reads no data, writes no files, and either returns a plan or raises. Assembly refuses an unfed input, an unread ordinary output, a dependency cycle, a duplicate step id, and planners that share a component but disagree on version or runtime fields. The first line of an assembly failure is `workflow cannot be assembled:`; the following lines name the ports. A compile failure leaves no plan to inspect, because the plan is the thing that failed to exist.

`execute` opens data and resources. It writes `workflow_plan.json` before the run starts, then runs the steps and writes `build_report.json` after the run returns. A run that raises before returning — a missing executor, a dependency cycle discovered at run time, a listener error, a runtime configuration refusal — leaves the plan document and no report. An unsuccessful run that returns normally does leave a report; an unsuccessful report is the normal evidence of a data or executor failure.

## Recovered is not resolved

A step ends with one of four statuses. `SUCCEEDED` and `WARNING` feed downstream steps. `FAILED` and `SKIPPED` disrupt them: a downstream step receives a disrupted context and the supplied executors turn that into a skipped outcome. A failed step is an outcome, not an exception. The runtime catches an executor exception and records it as a `Failure` with a message, the step id and the exception type.

The report splits failures by where they are still active. A failure is unresolved when it is active at a step that publishes an artifact. It is recovered otherwise, including a failure in a branch that reaches no publishing step. `report.succeeded` is true exactly when the unresolved tuple is empty, so a successful report can carry recovered failures. That is why a green run does not mean every step succeeded.

A failure that reaches a publishing step blocks publication of that step's ordinary outputs. Conflict validation with `fail_on_error=True` is the clearest case: the report step is itself a publishing step, so its failure is unresolved, and the conflict report is still published alongside the failure. The run fails and the evidence survives.

The report stores no traceback. It stores the message, the step id and the exception type. To see a traceback, reproduce the failing step in a test, where the exception is raised in front of pytest rather than caught by the runtime.

## Read the run before the record

An unsuccessful report is read in a fixed order.

First, list the unresolved failures and read the first one's step id. The step id is a component and a step name, not a formatted label. Then open `workflow_plan.json` and find that step. Its `instruction.kind` is the exact operation and engine pair. Check which executor claims that kind; a kind with no executor is refused before any step runs, so a missing executor normally appears as a raised error with no report rather than as a failed step.

```python
import json
from pathlib import Path

report = json.loads(Path("build/build_report.json").read_text())
for failure in report["unresolved_failures"]:
    print(
        failure["step_id"],
        failure["exception_type"],
        failure["message"],
    )
```

The same values are on the `WorkflowReport` returned by `execute`:

```python
from kg_build_system import execute

run_report = execute(plan, output_directory="build")
for failure in run_report.unresolved_failures:
    print(
        failure.step_id.component,
        failure.step_id.name,
        failure.exception_type,
        failure.message,
    )
```

Second, read the plan's provenance when the failure points at a step whose inputs look structurally wrong. The blueprint document is the declaration-level evidence; the plan document is the wiring-level evidence.

Third, read the record. A record failure has no dedicated message unless a planner or executor raised one. The report tells you which step failed, not which row was wrong.

## A refused plan is a wiring question

When `compile` refuses, do not start by reading the data. Compilation never opened it. Start with the planner composition and reduce it until the refusal disappears.

A useful minimal composition is one output planner over the core planners:

```python
from kg_build_system import compile
from kg_build_system.distribution import FileConfiguration, FilePlanner

plan = compile(planners=(FilePlanner(FileConfiguration("graph.jsonl")),))
print(len(plan.components), len(plan.steps), len(plan.connections))
```

If that compiles, the graph wiring and the core planners are sound, and the refusal belongs to a quality planner added on top. Add the quality planners back one at a time and compile after each. If the minimal composition refuses, the problem is in the declarations or in the source planner's ability to feed a relation the graph reads.

Read the message as a set of ports. `workflow cannot be assembled:` names the inputs and outputs that could not be matched. `<port> takes <type>, which no other step writes` means no planner emits that artifact type. `nothing reads <outputs>` means an ordinary output has no consumer. `duplicate step id <id>` means two steps share a component and step name. Once a plan exists, `plan.components`, `plan.steps` and `plan.connections` are the review surface: components name the planner groups and their runtime fields, steps name their exact instruction kinds, and connections resolve every input opening to one output opening.

A plan can also be refused at execution for a reason that belongs to the plan: `no executor for instruction kind(s): <kinds>` means the plan and the executor set disagree. `workflow has a dependency cycle` means no pending step became ready. Those refusals happen before data flows, so they belong in the same investigation as a compile refusal.

## A bad record is a data question

A data failure is different. The plan compiled, the steps ran, and the records that reached a target were wrong: a duplicate key, a missing value, a fan-out, a dangling endpoint. Often the report is successful, which is precisely why it cannot be the only check.

Start with counts. The meta-graph document counts the records that reached its executor for every bound component. An exact multiple of an expected count is fan-out, usually a join that matched more rows than intended. Zero is a filter that removed everything, a source that produced no rows, or a relation read from the wrong namespace. Neither symptom has a dedicated message.

Then compare keys. Read `graph.jsonl`, group the records by `type` and `build_key`, and look for repeated keys. A repeated key after deduplication means the rows differed in some column; the difference is the question. A repeated key after merging is impossible for a scoped component, because the merge groups by key. A missing key is a filter, a source or a binding question.

Conflict validation is the instrument for a disagreement you suspect but cannot see. Set `fail_on_error=False`, compose it before the merge, execute, and read the published findings. A finding names the component, key, property and count, which is enough to locate the rows in the source. It deliberately does not name the competing values. Compare the source rows for that key yourself.

Finally, turn the hypothesis into a test. Execute the plan into a temporary directory, assert the count or the key set, and let the failure show the traceback the report omitted. The repository supplies no fixture kit, so the test is ordinary Python around the public calls:

```python
import tempfile
from pathlib import Path

from kg_build_system import execute

with tempfile.TemporaryDirectory() as directory:
    report = execute(plan, output_directory=Path(directory))
    assert report.succeeded, [
        failure.message for failure in report.unresolved_failures
    ]
    assert (Path(directory) / "graph.jsonl").is_file()
```

A test that only asserts `report.succeeded` repeats the report's claim. Assert the property the report cannot see: the number of records for a component, the uniqueness of a key, the presence of an endpoint, or the value that the merge chose.

## The quality boundary is explicit

The three modules are deliberately weak, and the weakness is documented as an interface rather than hidden as a defect.

Deduplication removes only exact full-row duplicates. It does not resolve two different rows for one key, it does not prefer one binding over another, and it does not check that a key is unique after it runs. Merging assigns one record per build key per scoped component, takes a column-wise minimum, drops the binding symbol, and can synthesize a record or an edge that no input contained. It is not a conflict check and it cannot preserve intentional parallel facts inside one component. Conflict validation counts distinct non-null values per property and key, reports a count, and is blind to null versus value, endpoint keys, the binding symbol, unbound components, undeclared columns and every comparison across components or keys. It cannot repair, list or attribute the competing values.

Targets do not validate. The file target writes what it receives, the meta-graph describes what reached it, and Neo4j exports what it was given. A successful write is not a quality verdict on the records.

Two further boundaries belong here because they surface only after the build. Nothing checks that an edge endpoint matches a node key; the mismatch appears at import, in a consumer. And the grain a projection or binding declares is not checked at run time; a fan-out is a data outcome, not a plan error.

When a build needs a check outside these boundaries, the answer is a planner plus an executor, not a hidden option on an existing module. That is the same extension route as any other record operation: an exact instruction kind, an executor that claims it, and a step in the composition. The boundary stays legible because the module that owns the check is the module that refuses the unsupported case.

These limits do not disappear when the build is handed to someone else. They are part of what ships, alongside the plan, the artifacts and the report.

## Next

[17. Shipping a build](/book/part-3/05-shipping) — turn a run into a bundle another person can reproduce, with its guarantees and its limits stated.
