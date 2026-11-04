"""Plan the meta-graph document's one deferred step."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    Input,
    Instruction,
    InstructionKind,
    Key,
    PlanContext,
    Publication,
    Step,
)

from ...model.internal.instruction_dto import MetaGraphDocumentDTO
from ...model.public import MetaGraphConfiguration
from .instruction_codec import encode_meta_graph_instruction
from .topology import component_entries

_RECORDS_INPUT = "records"


class MetaGraphPlanner:
    """Emit the deferred step that writes the meta-graph document."""

    component_id = "meta_graph"
    version = "2"
    runtime_fields = ()

    def __init__(self, configuration: MetaGraphConfiguration | None = None) -> None:
        self.configuration = configuration or MetaGraphConfiguration()

    def plan(self, model: Any, context: PlanContext) -> tuple[Step, ...]:
        """Return the one deferred meta-graph document step.

        Example:
            ```python
            (step,) = MetaGraphPlanner(configuration).plan(blueprint, PlanContext())
            ```
        """
        entries = component_entries(model)
        payload = encode_meta_graph_instruction(MetaGraphDocumentDTO(
            relative_path=self.configuration.relative_path,
            example_limit=self.configuration.example_limit,
            include_html=self.configuration.include_html,
            html_relative_path=self.configuration.html_relative_path,
            components=entries,
        ))
        return (
            Step(
                component=self.component_id,
                name="document",
                inputs=(
                    Input(
                        ArtifactPattern.of("core", "graph", "**"),
                        None,
                        _RECORDS_INPUT,
                    ),
                ),
                outputs=(
                    Publication(
                        ArtifactType.of(
                            self.component_id, "meta_graph_document",
                        ),
                        Key(("result",)),
                    ),
                ),
                instruction=Instruction(
                    InstructionKind("meta_graph", "default"), payload,
                ),
                assembly_preference="deferred",
            ),
        )


__all__ = ["MetaGraphPlanner"]
