"""Execution of the Neo4j import bundle."""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    InstructionKind,
    StepOutcome,
)

from ....runtime import (
    instruction_payload,
    skipped,
    succeeded,
)
from kg_build_system.distribution.modules.runtime import OutputStorage
from kg_build_system.distribution.service.internal.relations import RelationService
from ...model.public import Neo4jConfiguration
from .export import Neo4jComponentExport, export_component
from .instruction_codec import decode_neo4j_instruction
from .instruction_dto import (
    Neo4jExportInstructionDTO,
    Neo4jScriptInstructionDTO,
)
from kg_build_system.distribution.service.internal.execution import artifact_of, input_values, output_path
from .script import render_import_script

_COMPONENTS_INPUT = "components"


class Neo4jExecutor:
    """Execute Neo4j component exports and the final import-script step."""

    kinds = (InstructionKind("neo4j", "default"),)
    resources = (RelationService, OutputStorage)

    def __init__(self, configuration: Any = None) -> None:
        if configuration is None:
            self._relative_directory_default = (
                Neo4jConfiguration().relative_directory
            )
        elif isinstance(configuration, Mapping):
            self._relative_directory_default = str(
                configuration.get("relative_directory", "neo4j-import")
            )
        else:
            self._relative_directory_default = configuration.relative_directory

    def _relative_directory(
        self,
        context: ExecutionContext,
        payload: Any,
    ) -> str:
        from kg_build_system.distribution.model.public.paths import (
            validate_relative_path,
        )

        runtime = getattr(context, "runtime_configuration", None)
        runtime_value = (
            runtime.get("relative_directory")
            if isinstance(runtime, Mapping)
            else None
        )
        payload_value = (
            payload.get("relative_directory")
            if isinstance(payload, Mapping)
            else None
        )
        value = (
            runtime_value
            if runtime_value is not None
            else payload_value
            if payload_value is not None
            else self._relative_directory_default
        )
        if not isinstance(value, str):
            raise TypeError("runtime Neo4j output directory must be a string")
        validate_relative_path(value, context="Neo4j output directory")
        return value

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Export one component or write the import script.

        Example:
            ```python
            outcome = Neo4jExecutor().execute(context, instruction)
            ```
        """
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        resources = context.resources
        payload = instruction_payload(instruction)
        value = decode_neo4j_instruction(payload)
        bundle_path = output_path(
            resources, self._relative_directory(context, payload),
        )
        bundle_path.mkdir(parents=True, exist_ok=True)
        if isinstance(value, Neo4jExportInstructionDTO):
            return export_component(
                context, bundle_path, value.component, resources,
            )
        return self._write_script(context, bundle_path, value)

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
            if (
                key not in expected
                or result.relative_path != expected[key].relative_path
            ):
                raise RuntimeError(f"unexpected Neo4j component export {key}")
            if key in exports:
                raise RuntimeError(f"duplicate Neo4j component export {key}")
            exports[key] = result

        missing = set(expected) - set(exports)
        if missing:
            names = ", ".join(f"{kind}:{name}" for kind, name in sorted(missing))
            raise RuntimeError(f"missing Neo4j component exports for {names}")

        node_paths = tuple(
            item.relative_path
            for item in instruction.components
            if item.kind == "node"
        )
        relationship_paths = tuple(
            item.relative_path
            for item in instruction.components
            if item.kind == "edge"
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
        return succeeded(context, summary)


__all__ = ["Neo4jExecutor"]
