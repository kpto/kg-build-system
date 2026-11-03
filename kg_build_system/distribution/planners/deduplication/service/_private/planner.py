"""Compile one exact-duplicate removal step per graph-record component."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.kernel import (
    Input,
    Instruction,
    Output,
    PlanContext,
    RuntimeField,
    Step,
)
from .artifacts import (
    CoreArtifactTypes,
    component_kind,
    graph_record_components,
)

_RECORDS_INPUT = "records"
_DISTINCT_OUTPUT = "distinct"


class DeduplicationPlanner:
    """Plan one distinct step per bound record component."""

    component_id = "deduplication"
    version = "2"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return one distinct step for each bound graph-record component.

        Example:
            ```python
            steps = DeduplicationPlanner().plan(blueprint, PlanContext())
            ```
        """
        del context
        steps: list[Step] = []
        for component in graph_record_components(blueprint):
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            steps.append(Step(
                component=self.component_id,
                name=component.name,
                inputs=(
                    Input(
                        type=records_type,
                        name=None,
                        input_name=_RECORDS_INPUT,
                    ),
                ),
                outputs=(
                    Output(records_type, name=_DISTINCT_OUTPUT),
                ),
                instruction=Instruction(
                    ("deduplication", "duckdb"),
                    {"relation": f"kg_distinct_{component.name.lower()}"},
                ),
            ))
        return tuple(steps)


__all__ = ["DeduplicationPlanner"]
