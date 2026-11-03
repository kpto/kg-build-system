"""Execution of the Neo4j import bundle."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from .....kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
    StepStatus,
)
from ...service.paths import validate_relative_path
from ...service.relations import (
    artifact_of, input_values, output_path,
)
from ...service.runtime import (
    as_mapping, execution_services, output_name, skipped,
)
from .export import (
    Neo4jComponentExport,
    export_component,
    select_sql,
)
from .instruction_dto import (
    Neo4jComponentImportDTO,
    Neo4jExportInstructionDTO,
    Neo4jScriptInstructionDTO,
    decode_neo4j_instruction,
)
from .script import render_import_script

_COMPONENTS_INPUT = "components"


def executor_for(context: Any) -> Neo4jExecutor:
    """Create the Neo4j executor from one module factory context."""
    return Neo4jExecutor(context.runtime_configuration)


class Neo4jExecutor:
    def __init__(self, runtime_configuration: Any) -> None:
        self._runtime_configuration = dict(as_mapping(
            runtime_configuration, context="Neo4j runtime configuration",
        ))

    def handle(self, context: ExecutionContext, services: Any = None) -> StepOutcome:
        services = execution_services(context, services)
        instruction = decode_neo4j_instruction(self._instruction(context))
        bundle_path = output_path(services, self._relative_directory(context))
        bundle_path.mkdir(parents=True, exist_ok=True)
        if isinstance(instruction, Neo4jExportInstructionDTO):
            return export_component(
                context, bundle_path, instruction.component, services,
            )
        return self._write_script(context, bundle_path, instruction)

    def _relative_directory(self, context: ExecutionContext) -> str:
        compiled = as_mapping(
            context.module.reference.configuration,
            context="Neo4j compiled configuration",
        )
        value = self._runtime_configuration.get(
            "relative_directory", compiled.get("relative_directory"),
        )
        if not isinstance(value, str):
            raise TypeError("runtime Neo4j output directory must be a string")
        validate_relative_path(value, context="Neo4j output directory")
        return value

    @staticmethod
    def _instruction(context: ExecutionContext) -> Any:
        variables = as_mapping(
            context.variables, context="Neo4j module variables",
        )
        instructions = as_mapping(
            variables.get("instructions"), context="Neo4j instructions",
        )
        return instructions[context.step.name]

    @staticmethod
    def _write_script(
        context: ExecutionContext,
        bundle_path: Path,
        instruction: Neo4jScriptInstructionDTO,
    ) -> StepOutcome:
        expected = {
            (item.kind, item.component): item for item in instruction.components
        }
        exports: dict[tuple[str, str], Neo4jComponentExport] = {}
        for contribution in input_values(context, _COMPONENTS_INPUT):
            artifact = artifact_of(contribution)
            if artifact is None:
                continue
            if not isinstance(artifact.value, Neo4jComponentExport):
                raise TypeError(
                    "Neo4j script inputs must contain component export results"
                )
            result = artifact.value
            key = (result.kind, result.component)
            if key not in expected or result.relative_path != expected[key].relative_path:
                raise RuntimeError(f"unexpected Neo4j component export {key}")
            if key in exports:
                raise RuntimeError(f"duplicate Neo4j component export {key}")
            exports[key] = result

        missing = set(expected) - set(exports)
        if missing:
            names = ", ".join(f"{kind}:{name}" for kind, name in sorted(missing))
            raise RuntimeError(f"missing Neo4j component exports for {names}")

        node_paths = tuple(
            item.relative_path for item in instruction.components if item.kind == "node"
        )
        relationship_paths = tuple(
            item.relative_path for item in instruction.components if item.kind == "edge"
        )
        script_path = bundle_path / instruction.script_name
        script_path.write_text(render_import_script(
            node_paths=node_paths,
            relationship_paths=relationship_paths,
            default_database=instruction.default_database,
        ), encoding="utf-8", newline="\n")
        if os.name != "nt":
            script_path.chmod(script_path.stat().st_mode | 0o111)

        counts: dict[Literal["node", "edge"], int] = {"node": 0, "edge": 0}
        for result in exports.values():
            counts[result.kind] += result.rows
        summary = {
            "directory": str(bundle_path),
            "script": str(script_path),
            "nodes": counts["node"],
            "edges": counts["edge"],
            "node_files": list(node_paths),
            "relationship_files": list(relationship_paths),
        }
        output = context.step.outputs[0]
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(Artifact(output_name(output), output.type, summary),),
        )

    @staticmethod
    def _select_sql(
        specification: Neo4jComponentImportDTO, relation_sql: str,
    ) -> str:
        return select_sql(specification, relation_sql)

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


__all__ = ["Neo4jExecutor", "executor_for"]
