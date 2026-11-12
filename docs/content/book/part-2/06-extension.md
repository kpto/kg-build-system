---
title: "9. Extending the semantics model"
summary: "A shipped operation set is a baseline; a domain rule becomes graph meaning only when it is named, referenced and given semantics."
section: book
perspective: book
part: II
chapter: 9
order: 26
status: normative
verified: 2026-11-11
sources:
  - docs/content/appendix/reference/ingest.md
  - docs/content/appendix/reference/expressions.md
  - docs/content/appendix/reference/projections.md
  - docs/content/appendix/developer/data-and-expressions.md
  - kg_build_system/distribution/languages/expressions/service/internal/operations/spec.py
---

## The operation the domain needs is not shipped

A survey reports a defect with `condition_rating` as text: `poor`, `fair`. Triage needs a severity rank, a small integer that orders those labels. The expression surface offers `equals`, `add`, `sub`, `to_string`, separator helpers and array transforms. It has no conditional, no ordering comparison and no `severity_rank`. Composing the shipped methods does not produce a rank from a label without inventing a meaning for arithmetic on booleans.

That absence is ordinary. The shipped expression surface is a baseline, not a complete domain language; it cannot know a domain's vocabulary. A graph project should expect to write extensions and some of its own semantics. The useful question is not whether to extend, but which object carries the extension.

An extension is part of the semantic model, not a patch around it. It is a statement the model publishes: an operation specification, a named projection, an attached claim. The same severity calculation can be a private convenience or a graph fact, and the two are different objects even when they compute the same number. This chapter is about choosing between them, and about the cost of each choice.

## A source reader stops at the relation

The estate export carries sites, equipment, surveys and readings in one directory. `Estate` names the logical source unit; `SitesTable`, `EquipmentTable` and `SurveysTable` name row shapes read from it. A source planner resolves a compatible `AssetLayout` and produces a relation with the declared columns. `AssetLayout` is descriptive metadata: it names a `format`, a `locator`, `members` and reader hints. It opens no file, validates no column and proves no relation exists. The build checks the source before it reads rows, because the layout cannot promise what the bytes contain. The full resolution order and the format table are in [Ingest](/appendix/reference/ingest).

The source layer adapts a format to the neutral relation plan and the SQL/emitter boundary. Nothing further is a source concern.

Suppose a partner sends a semicolon-delimited export: a header `site_id;site_name;unit_refs`, one record per site, with `unit_refs` holding values such as `U-1;U-2`. The built-in reader understands `parquet`, `json` and `csv`, and the CSV reader sniffs its delimiter, so a whole-file semicolon export is often CSV with another separator. If that reader handles the file, the right answer is a `csv` layout and no extension at all. The sketch below covers the case where it does not: a distinct format that needs its own planner and executor. The layout names `semicolon`; the planner claims it; no registry is edited and no adapter is registered.

The planner shape is small. This is an internal extension point, sketched rather than imported:

```python
from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.distribution.service.internal import asset_tables
from kg_build_system.kernel import (
    Instruction, InstructionKind, Output, PlanContext, Step,
)

SEMICOLON_SOURCE = InstructionKind("source_relation", "semicolon")


class SemicolonSourcePlanner:
    """Plan one relation-producing step for a semicolon-delimited asset."""

    component_id = "semicolon"
    version = "1"
    runtime_fields = ()

    def plan(
        self, model: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        del context
        return tuple(
            Step(
                component=self.component_id,
                name=f"source.{table.relation_name}",
                inputs=(),
                outputs=(
                    Output(CoreArtifactTypes.table(table.relation_name)),
                ),
                instruction=Instruction(
                    SEMICOLON_SOURCE,
                    {
                        "relation": table.relation,
                        "location": location,
                    },
                ),
            )
            for table in asset_tables(model)
            if (location := semicolon_location(table.asset.layout)) is not None
        )
```

`semicolon_location` is a local helper over the same `members`, `selector` and `locator` order the generic planner uses; it is not part of the extension's contract.

The executor claims the same exact kind, opens the location, reads the header, splits each record on `;`, casts the fields to the declared logical types and publishes the relation `sites(site_id, site_name, unit_refs)`. Then it stops.

The stopping point is the argument. The adapter does not split `unit_refs` into units. It does not decide that `U-1` in this file denotes the same equipment as `unit_ref` in `equipment.json`. It does not join surveys to sites, aggregate readings, resolve duplicate evidence, vote on conflicting sources, translate a local identifier into a registry identifier, or infer that one source is authoritative over another. Those are domain decisions, not decoding.

The distinction is not cosmetic. A reader that split `unit_refs` would have turned one site row into several unit rows before the graph declared a grain. A reader that matched units to sites would have embedded a join in a format flag. A reader that translated identifiers would have made provenance depend on a loader rather than on an asset. In each case the layout would mean two things: where the bytes are, and what the rows mean. The first belongs to ingest; the second belongs to the data model.

Splitting a delimited value into an array is a value operation, and expanding that array into one row per item is a grain decision that belongs to a row source or a named projection. Matching units to sites is a join. Reconciling two identifier schemes is identity translation, which is a graph fact or a module, never a reader. The source layer adapts a physical format to a relation and stops. [The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) places that object on the extension ladder; this chapter places the domain rule it must not absorb.

## A domain calculation belongs in the expression language

The severity rank reads one text value and returns one integer for the row it receives. That is a value operation. The expression language owns it, and the object that declares it is an `OperationSpec`: a name, an arity, one `ArgumentSpec` per positional argument, optional named parameters, a result type and a row-effect declaration.

```python
from kg_build_system import INT, STR
from kg_build_system.distribution.languages.expressions.service.internal.operations import (
    ArgumentSpec, OperationSpec,
)

SEVERITY_RANK = OperationSpec(
    name="severity_rank",
    arity=1,
    arguments=(
        ArgumentSpec(expected=STR, description="survey condition"),
    ),
    result_type=INT,
)
```

The authoring function beside it calls the spec:

```python
from typing import cast

from kg_build_system import Selection
from kg_build_system.distribution.languages.expressions.service._private.selections import (
    selection_from_node,
)


def severity_rank(value: Selection[str]) -> Selection[int]:
    """Rank a recorded survey condition as a severity value."""
    return cast(
        Selection[int],
        selection_from_node(SEVERITY_RANK.apply(value).model),
    )
```

The spec validates at the moment the expression is written. Wrong arity, an argument of another logical type, a missing required parameter or an unknown parameter is refused before a row exists. The authoring method is thin; the declaration is the spec. An expression DTO records the operator name, its arguments, its parameters and its result type, so the plan carries the calculation without carrying the Python function.

The default row effect is `RowSemantics()`: the operation preserves the row count and computes one value for the row it receives. That is the right constraint for a domain calculation. A severity rank does not remove a defect because its rating is absent; the projection decides that with `drop_null`. If an operation declares `expand` or `filter`, it has become a row decision dressed as a calculation. Row effects are declared, reached through `alter_rows()` and visible to the planner. Keep them separate: the operation computes a value, the row effect decides what the row becomes.

The shipped registry is a baseline. It composes `add`, `sub`, `concat`, `append`, `equals`, `replace`, `to_string`, the separator helpers, the array operations, boolean combinators, `zip` and the row-effect operations. It is a useful set, not a domain language. It has no conditional, no ordering comparison, no date arithmetic and no vocabulary for conditions, quantities or identifiers. The built-in set is where a project starts.

Burying the calculation elsewhere does not remove the need for that floor. A `CASE` expression inside a source reader, a SQL string inside a planner, or an inline lambda that one binding can use hides the operation from the vocabulary and from review. The result may be correct for one pipeline and unavailable to the next consumer. If the value belongs in the language, declare it as an operation.

Adding an operation is an expression-language extension, not a runtime registration. There is no public `register_operation` function, and inventing one would misdescribe the model: an operation is part of a language's vocabulary, not a switch on a running build. The operation set belongs to the expressions language; the SQL operator set belongs to the engine that executes it. The exact internal interface, including the `OperationSpec`, `ArgumentSpec` and `OperationRegistry` values, is stated in [Data and expressions](/appendix/developer/data-and-expressions).

Every operation also needs an emitter in the engine that runs it. The severity operation renders as a SQL `CASE`; this is the same internal sketch, not a public extension API:

```python
from sqlglot import exp


class SeverityRank:
    """Emit the severity_rank operator as a SQL CASE expression."""

    operator = "severity_rank"

    def emit(self, expression, operands, context):
        del context
        if len(operands) != 1:
            raise ValueError("severity_rank requires one argument")
        rating = operands[0].sql()
        return exp.Case(
            ifs=[
                exp.If(
                    this=rating.copy().eq("poor"),
                    true=exp.Literal.number(4),
                ),
                exp.If(
                    this=rating.copy().eq("fair"),
                    true=exp.Literal.number(2),
                ),
            ],
            default=exp.Literal.number(1),
        )
```

A spec without an emitter type-checks and fails at emission. An operation that no engine can express is not an expression operation; it is a step with its own executor, and it belongs to the workflow model in Part IV. Portability is a property of the spec and emitter pair, not of the name. This is also why a value operation is a poor hiding place for aggregation: a count or a vote needs the whole relation, not one row, and the grouped-row algebra already says that aggregation belongs to a later module rather than to a value method.

The operation is a declaration, so the blueprint can name it through an `OperationRef`. Its application is an inline fragment, so the expression `severity_rank(condition_rating)` has no identity of its own. That is the hinge of the chapter: a calculation can be part of the vocabulary and still not be part of the graph's meaning until something names the relation it produces.

## Naming is what turns the operation into meaning

A projection is a named logical relation pinned to exactly one row-source value. It publishes typed outputs with `computed_field`, it is a row-source provider itself, and its outputs share one row plan. The name is part of the contract: it is unique among tables and projections because both are logical source names in one namespace. Chapter 8 established the grain; this chapter uses the name for a different purpose, which is to carry a domain claim into the blueprint. A projection is the framework's semantics unit for a derived relation: a relation with a name, a grain, typed outputs and meaning a consumer can read.

```python
from kg_build_system import (
    Claim, Frame, Limitation, Projection, ProjectionOptions, Semantics,
    computed_field,
)

# The operation above; the existing defect grain.
from reference_project.table.projections.defects import DefectProjection


class ConditionSeverityProjection(Projection(DefectProjection.row_source())):
    """One row per defect, with a severity rank for its condition."""

    options = ProjectionOptions(
        name="condition_severity",
        semantics=Semantics(
            claims=(
                Claim(
                    "A severity rank summarises the recorded condition "
                    "of one defect."
                ),
            ),
            frames=(
                Frame(
                    text="Survey condition only.",
                    limitations=(
                        Limitation(
                            "The rank is not a probability of failure."
                        ),
                    ),
                ),
            ),
        ),
    )

    defect_id = computed_field(DefectProjection.defect_id)
    severity = computed_field(
        severity_rank(
            DefectProjection.condition_rating.alter_rows().drop_null()
        )
    )
```

Four decisions are visible in one declaration. The projection pins the defect grain, so a defect is not re-expanded from the survey document here; that expansion is already `DefectProjection`'s job. The rating is nullable, so `drop_null` removes a defect whose condition was never recorded: that is a statement about which rows this relation contains, and it belongs in the projection rather than inside the operation. The rank is computed by the extension operation and published as a present integer. The `Semantics` fragment states what the relation claims and what it excludes, read under the graph's one purpose.

The promotion is justified by use, not by taste. Triage and reporting both need the defect grain with a severity, and the graph is asked to state what the rank means. A calculation that only one property needed would have stayed in the binding. This one is expected to be shared, so it gets a name and a claim.

The exact projection surface, including the naming and dependency rules, is in [Projections](/appendix/reference/projections).

The name does the work that an expression cannot. Outside this pipeline, a binding writes `rows=ConditionSeverityProjection.row_source()` and inherits the grain, the computation and the claim. Another projection can pin it. A `lookup` can read it by key. In the blueprint, the projection is published as a named relation with its outputs and its pinned row plan, so a consumer reads the name, the types, the grain and the semantics without importing the authoring class. A reviewer reads one declaration and sees the whole decision.

The projection also gives the operation a place to change. When the severity formula is revised, one declaration changes and every consumer sees the new relation. When a second domain operation joins it, the projection either gains an output on the same grain or becomes two projections with two names. The name keeps that choice reviewable.

There is a reachability condition of a different kind. A projection that no binding and no other projection reads is a name without a consumer: it may appear in the model, but nothing in the graph depends on it, and its claim explains a grain that populates no record. Naming is necessary for a semantics unit, not sufficient; the name must also be available to a consumer that reads the relation.

## A private expression is a data operation

Put the same call inside a binding's `bind` lambda, feeding a `severity` property on a defect node. The calculation is valid. It has no relation name, no grain of its own, no `Semantics`, and no reader outside that binding. It is a data operation applied to a record property. That is often exactly right: a property calculation does not need a relation, and not every number deserves a claim.

Now suppose the same rank is computed in a planner and published as a private relation. The step has a name such as `derive.condition_severity`, and that name is a `StepId`. It is not a `RelationRef`. The blueprint has no `ProjectionDTO` for it, no output field is addressable through a `FieldRef`, no `Semantics` attaches to it, and no `lookup` can target it. A consumer cannot ask what the graph claims about severity, because the graph claims nothing. The step exists; the meaning does not.

A private expression is not wrong because it is private. It is wrong when it is described as a projection. The model's shape makes the masquerade hard to complete. `Semantics` attaches to declarations such as `ProjectionOptions`, `TableOptions` and `NodeOptions`, not to expressions or steps. A binding reads a row source, and a step output is not a row source. `lookup` targets a `Table` or a `Projection`, not a step. The blueprint publishes projections and relations, not intermediate plan nodes. There is nowhere to hang the claim and no reference that can point at the private relation.

So the choice is stated plainly. If the operation is an implementation detail of one consumer, keep it in the executor, the source adapter or the binding where it is used. If it is part of what the graph means, promote it to a named projection with identity and semantics. Promotion has a real cost: a name in the relation namespace, at least one computed output, a claim, a consumer that makes it reachable, and a contract test that the output and the meaning are published. That cost is the price of asking a consumer to rely on the relation.

## Five places a domain rule can live

The same domain sentence can be implemented at five levels. The level is chosen by the kind of fact being added, not by convenience.

| The work | The object | It may decide | It may not decide | The cost |
| --- | --- | --- | --- | --- |
| Physical read and decoding | A source planner and executor, with an exact instruction kind | Location, format, header, field decoding, checked casts to declared types | Joins, identity, aggregation, grain changes, graph meaning | A module, an exact kind, a resource, decoding tests |
| One value per row | An expression operation: `OperationSpec` plus an engine emitter | A typed calculation, its arguments, its result type and its declared row effect | Row count, a new relation, identity, a second source | A spec, an emitter, an authoring method, type and emission tests |
| A named derived relation | A `Projection` over one pinned row source | Grain, computed fields, output names, an attached `Semantics` | A second driving source, record mapping, merging | A declaration, a unique name, a claim, a contract test |
| A row-to-record mapping | A binding | Build key, properties, endpoints, one record per row | Joins, expansion, aggregation, rewriting the grain | The next chapter; mapping and guard tests |
| A whole new workflow step | A planner and executor module | A new artifact, a pass over records, consensus or a second relation | Graph meaning without a model change; a named relation without a projection | Component identity, exact kind, artifact and provenance tests |

The first three are the subject of this chapter. The fourth is the next one. The fifth is Part IV, and it is the most expensive because it adds an artifact, a component, a resource obligation and a provenance surface.

Choosing is mostly a matter of asking what the rule produces. A rule that turns bytes into typed fields belongs in the reader. A rule that turns one row into one value belongs in an operation. A rule that produces a relation several consumers must agree on belongs in a projection. A rule that turns a row into a record belongs in a binding. A rule that needs to see many records at once, or produce a separate artifact, belongs in a planner and executor.

Three mistakes are common, and each hides a decision. The first puts a join, an identifier translation or an aggregation in a source reader, where it becomes invisible to the graph and impossible to review as topology or grain. The second puts a grain inside a binding, where it cannot be expressed and, if forced, becomes a planner in disguise. The third gives a plan-local relation a human name and discusses it as a projection, although no consumer can name or reference it. Each mistake buys local convenience by moving meaning out of the place a reader inspects.

## The judgement rule

If a claimed projection cannot be named and referenced outside the pipeline, it is not a projection.

The test has three parts, and all three are read from the delivered blueprint rather than from the source text. It has a name in the relation namespace, unique among tables and projections. It can be referenced by a binding or by another projection, so a consumer outside the producing pipeline can read it. It carries a `Semantics` fragment that states its claim or its frame. A relation with a name and no consumer is a draft. A relation with a consumer and no claim is a computation that has not said what it means. A computation with a claim but no name has nowhere to publish the claim.

A projection that exists only inside a plan, cannot be named in the blueprint and cannot be referenced outside that pipeline is not a semantics unit. It is a data operation, and presenting it as a projection is wrong modelling.

Name it, give it identity and semantics, or keep the operation out of the model. The framework should not let a pipeline-local operation masquerade as graph meaning, and by and large it does not: an expression fragment has no name, a step id is not a relation reference, and a claim attaches only to a declaration. The remaining risk is editorial. A design note can call a private relation a projection, and a reader can believe it. The blueprint is the correction: it either contains the projection or it does not.

An extension is therefore part of the semantic model when it survives that test. The operation spec says what the domain computes. The projection says which relation the computation produces, for which rows, under which claim. The binding later says which record those rows populate. Each layer states one fact and stops. The next chapter takes the named relation and maps it to a node or an edge, where the grain becomes a record count and the claim becomes something a consumer can query.

## Next

[10. A workflow is a chain of reactions](/book/part-2/07-composition) — from a domain operation to the reactions that carry its result.
