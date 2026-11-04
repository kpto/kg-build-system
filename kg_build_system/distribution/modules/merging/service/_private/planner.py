"""Compile one compatible-facts merge step per selected record component."""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.kernel import (
    ArtifactPattern,
    Input,
    Instruction,
    InstructionKind,
    Key,
    Output,
    PlanContext,
    RuntimeField,
    Step,
)
from ...model.public import MergingConfiguration
from .artifacts import component_kind, graph_record_components
from .configuration import component_name

_RECORDS_INPUT = "records"
_MERGED_OUTPUT = "merged"


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


class MergingPlanner:
    """Plan one merge step per selected record component."""

    component_id = "merging"
    version = "2"
    runtime_fields: tuple[RuntimeField, ...] = ()

    def __init__(self, configuration: MergingConfiguration) -> None:
        self._configuration = configuration

    def plan(
        self, blueprint: GraphBlueprint, context: PlanContext,
    ) -> Sequence[Step]:
        """Return one merge step for each component in the configured scope.

        Example:
            ```python
            steps = MergingPlanner(MergingConfiguration()).plan(
                blueprint, PlanContext(),
            )
            ```
        """
        del context
        steps: list[Step] = []
        scope = self._configuration.components
        scope_names = None if scope is None else {
            component_name(component) for component in scope
        }
        for component in graph_record_components(blueprint):
            if scope_names is not None and component.name not in scope_names:
                continue
            records_type = CoreArtifactTypes.graph_records(
                component_kind(component), component.name,
            )
            fields = [prop.name for prop in component.properties]
            if component_kind(component) == "edge":
                fields = ["source_build_key", "target_build_key", *fields]
            aggregates = [
                f'min("{_quote_identifier(name)}") AS "{_quote_identifier(name)}"'
                for name in fields
            ]
            select = ", ".join(['"build_key"', *aggregates])
            steps.append(Step(
                component=self.component_id,
                name=component.name,
                inputs=(
                    Input(
                        type=ArtifactPattern(records_type.key),
                        opening_name=None,
                        declared_name=_RECORDS_INPUT,
                    ),
                ),
                outputs=(
                    Output(records_type, opening_name=Key((_MERGED_OUTPUT,))),
                ),
                instruction=Instruction(
                    InstructionKind("merging", "duckdb"), {
                        "relation": f"kg_normalised_{component.name.lower()}",
                        "select": select,
                    },
                ),
            ))
        return tuple(steps)


__all__ = ["MergingPlanner"]
