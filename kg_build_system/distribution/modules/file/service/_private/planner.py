"""Plan the JSON Lines file target's one deferred write step."""
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
    RuntimeField,
    Step,
)

from ...model.public import FileConfiguration

RECORDS_INPUT = "records"


class FilePlanner:
    """Emit the deferred step that writes graph records to a JSON Lines file."""

    component_id = "file"
    version = "2"
    runtime_fields = (
        RuntimeField(
            "relative_path",
            "Optional runtime replacement for the relative output path.",
            required=False,
        ),
    )

    def __init__(self, configuration: FileConfiguration) -> None:
        self.configuration = configuration

    def plan(self, model: Any, context: PlanContext) -> tuple[Step, ...]:
        """Return the one deferred file-write step.

        Example:
            ```python
            (step,) = FilePlanner(configuration).plan(blueprint, PlanContext())
            ```
        """
        opening = self.configuration.opening
        name = self.configuration.name
        component = f"{self.component_id}.{name}" if name else self.component_id
        return (
            Step(
                component=component,
                name=f"write.{name or opening or 'graph'}",
                inputs=(
                    Input(
                        ArtifactPattern.of("core", "graph", "**"),
                        Key((opening,)) if opening else None,
                        RECORDS_INPUT,
                    ),
                ),
                outputs=(
                    Publication(
                        ArtifactType.of(component, "write_result"),
                        Key((name or "result",)),
                    ),
                ),
                instruction=Instruction(
                    InstructionKind("file", "default"),
                    {"relative_path": self.configuration.relative_path},
                ),
                assembly_preference="deferred",
            ),
        )


__all__ = ["FilePlanner", "RECORDS_INPUT"]
