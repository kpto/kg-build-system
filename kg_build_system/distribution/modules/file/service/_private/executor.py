"""Execute the JSON Lines file target."""
from __future__ import annotations

import datetime
import json
import uuid
from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.model.public.artifacts import (
    graph_record_artifact,
)
from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    InstructionKind,
    StepOutcome,
)
from kg_build_system.kernel.service.internal.types import canonical_value_text

from ....runtime import (
    instruction_payload,
    skipped,
    succeeded,
)
from kg_build_system.distribution.modules.runtime import OutputStorage
from kg_build_system.distribution.service.internal.relations import RelationService
from kg_build_system.distribution.service.internal.execution import (
    artifact_of,
    input_values,
    output_path,
    query,
    reference,
)

_RECORDS_INPUT = "records"


def _canonical_property_value(value: Any) -> Any:
    """The canonical form of one property value as it reaches the graph file."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time, uuid.UUID)):
        return canonical_value_text(value)
    if isinstance(value, dict):
        return {
            key: _canonical_property_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_property_value(item) for item in value]
    raise TypeError(
        f"graph property of type {type(value).__qualname__} has no canonical"
        " form in the file target"
    )


def _runtime_values(
    configuration: Mapping[str, Any],
    context: ExecutionContext | DisruptedExecutionContext,
) -> Mapping[str, Any]:
    """Merge executor defaults with the runtime values the kernel supplied."""
    values = dict(configuration)
    supplied = getattr(context, "runtime_configuration", None)
    if isinstance(supplied, Mapping):
        values.update(supplied)
    return values


def _configuration_mapping(configuration: Any) -> Mapping[str, Any]:
    """Read executor configuration from a mapping or its configuration value."""
    if configuration is None:
        return {}
    if isinstance(configuration, Mapping):
        return configuration
    relative_path = getattr(configuration, "relative_path", None)
    if relative_path is None:
        return {}
    return {"relative_path": relative_path}


class FileExecutor:
    """Write every graph-record relation the step receives, in one pass."""

    kinds = (InstructionKind("file", "default"),)
    resources = (RelationService, OutputStorage)

    def __init__(self, configuration: Any = None) -> None:
        self._configuration = _configuration_mapping(configuration)

    def _relative_path(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> str:
        payload = instruction_payload(instruction)
        configured_path = payload.get("relative_path")
        if not isinstance(configured_path, str):
            raise RuntimeError(
                "file instruction requires a compiled relative output path"
            )
        runtime_path = _runtime_values(
            self._configuration, context,
        ).get("relative_path")
        relative_path = runtime_path if runtime_path is not None else configured_path
        if not isinstance(relative_path, str):
            raise TypeError("runtime file output path must be a string")
        from kg_build_system.distribution.model.public.paths import (
            validate_relative_path,
        )

        validate_relative_path(relative_path, context="file output path")
        return relative_path

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Write the received graph records and return the summary artifact.

        Example:
            ```python
            outcome = FileExecutor().execute(context, instruction)
            ```
        """
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        resources = context.resources
        relative_path = self._relative_path(context, instruction)
        path = output_path(resources, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        node_count = 0
        edge_count = 0
        with path.open("w", encoding="utf-8") as stream:
            for contribution in input_values(context, _RECORDS_INPUT):
                artifact = artifact_of(contribution)
                if artifact is None:
                    continue
                identity = graph_record_artifact(artifact.type)
                if identity is None:
                    continue
                kind, component = identity.kind, identity.component

                relation = reference(resources, artifact.value)
                result = query(resources, f"SELECT * FROM {relation}")
                columns = tuple(column[0] for column in result.description)
                while batch := result.fetchmany(1_000):
                    for row in batch:
                        record = dict(zip(columns, row, strict=True))
                        record.update(
                            build_key=str(
                                _canonical_property_value(record["build_key"])
                            ),
                            type=component,
                            kind=kind,
                        )
                        if kind == "node":
                            node_count += 1
                        else:
                            edge_count += 1
                        stream.write(
                            json.dumps(
                                record,
                                sort_keys=True,
                                default=_canonical_property_value,
                            ) + "\n"
                        )

        summary = {
            "nodes": node_count,
            "edges": edge_count,
            "location": str(path),
        }
        return succeeded(context, summary)


__all__ = ["FileExecutor"]
