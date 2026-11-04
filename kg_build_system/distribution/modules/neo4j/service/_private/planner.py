"""Plan the Neo4j component exports and the deferred import-script step."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.model.public.artifacts import (
    CoreArtifactTypes,
)
from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    Input,
    Instruction,
    InstructionKind,
    Key,
    PlanContext,
    Publication,
    Output,
    RuntimeField,
    Step,
)

from ...model.public import Neo4jConfiguration
from .export import (
    component_export_type,
    component_imports,
    component_step_name,
)

_RECORDS_INPUT = "records"
_COMPONENTS_INPUT = "components"
_SCRIPT_STEP_NAME = "script"


def _graph_record_components(
    blueprint: GraphBlueprint,
) -> tuple[Any, ...]:
    """Components with at least one binding, in graph order."""
    bound = {binding.component for binding in blueprint.bindings}
    return tuple(
        component
        for component in (*blueprint.graph.nodes, *blueprint.graph.edges)
        if component.name in bound
    )


class Neo4jPlanner:
    """Emit one export step per component and one deferred script step."""

    component_id = "neo4j"
    version = "2"
    runtime_fields = (
        RuntimeField(
            "relative_directory",
            "Optional runtime replacement for the Neo4j import-bundle directory.",
            required=False,
        ),
    )

    def __init__(self, configuration: Neo4jConfiguration | None = None) -> None:
        self.configuration = configuration or Neo4jConfiguration()

    def plan(self, model: GraphBlueprint, context: PlanContext) -> tuple[Step, ...]:
        """Return the component export steps followed by the script step.

        Example:
            ```python
            steps = Neo4jPlanner(configuration).plan(blueprint, PlanContext())
            ```
        """
        components = component_imports(_graph_record_components(model))
        exports = tuple(
            self._component_export_step(component) for component in components
        )
        script = Step(
            component=self.component_id,
            name=_SCRIPT_STEP_NAME,
            inputs=(
                Input(
                    ArtifactPattern.of(self.component_id, "component", "**"),
                    None,
                    _COMPONENTS_INPUT,
                ),
            ),
            outputs=(
                Publication(
                    ArtifactType.of(self.component_id, "import_bundle"),
                    Key(("result",)),
                ),
            ),
            instruction=Instruction(
                InstructionKind("neo4j", "default"),
                {
                    "kind": "write_script",
                    "components": [
                        item.model_dump(mode="json") for item in components
                    ],
                    "script_name": self.configuration.script_name,
                    "default_database": self.configuration.default_database,
                    "relative_directory": self.configuration.relative_directory,
                },
            ),
            assembly_preference="deferred",
        )
        return (*exports, script)

    def _component_export_step(self, component: Any) -> Step:
        return Step(
            component=self.component_id,
            name=component_step_name(component),
            inputs=(
                Input(
                    ArtifactPattern(
                        CoreArtifactTypes.graph_records(
                            component.kind, component.component,
                        ).key,
                    ),
                    None,
                    _RECORDS_INPUT,
                ),
            ),
            outputs=(
                Output(
                    component_export_type(component), Key(("result",)),
                ),
            ),
            instruction=Instruction(
                InstructionKind("neo4j", "default"),
                {
                    "kind": "export_component",
                    "component": component.model_dump(mode="json"),
                    "relative_directory": self.configuration.relative_directory,
                },
            ),
            assembly_preference="deferred",
        )


__all__ = ["Neo4jPlanner"]
