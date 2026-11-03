"""Execution of the JSON Lines file target."""
from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from ......kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
    StepStatus,
)
from kg_build_system.kernel.service.internal.types import canonical_value_text
from ...service.paths import validate_relative_path
from ...service.relations import (
    artifact_of,
    input_values,
    output_path,
    query,
    reference,
)
from ...service.runtime import (
    as_mapping,
    execution_services,
    output_name,
    skipped,
)
from .....model.public.artifacts import CoreArtifactTypes

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


def executor_for(context: Any) -> FileExecutor:
    """Create the file executor from one module factory context."""
    return FileExecutor(as_mapping(
        context.runtime_configuration, context="file runtime configuration",
    ))


class FileExecutor:
    """Write every graph-record relation the step receives, in one pass."""

    def __init__(self, configuration: Any) -> None:
        self._configuration = dict(as_mapping(
            configuration, context="file runtime configuration",
        ))

    def _relative_path(self, context: ExecutionContext) -> str:
        compiled = as_mapping(
            context.module.reference.configuration,
            context="file compiled configuration",
        )
        configured_path = compiled.get("relative_path")
        if not isinstance(configured_path, str):
            raise RuntimeError(
                "file module requires a compiled relative output path"
            )
        runtime_path = self._configuration.get("relative_path")
        relative_path = runtime_path if runtime_path is not None else configured_path
        if not isinstance(relative_path, str):
            raise TypeError("runtime file output path must be a string")
        validate_relative_path(relative_path, context="file output path")
        return relative_path

    def handle(self, context: ExecutionContext, services: Any = None) -> StepOutcome:
        services = execution_services(context, services)
        relative_path = self._relative_path(context)
        path = output_path(services, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        node_count = 0
        edge_count = 0
        with path.open("w", encoding="utf-8") as stream:
            for contribution in input_values(context, _RECORDS_INPUT):
                artifact = artifact_of(contribution)
                if artifact is None:
                    continue
                identity = CoreArtifactTypes.graph_record_identity(artifact.type)
                if identity is None:
                    continue

                relation = reference(services, artifact.value)
                result = query(services, f"SELECT * FROM {relation}")
                columns = tuple(column[0] for column in result.description)
                while batch := result.fetchmany(1_000):
                    for row in batch:
                        record = dict(zip(columns, row, strict=True))
                        record.update(
                            build_key=str(
                                _canonical_property_value(record["build_key"])
                            ),
                            type=identity.component,
                            kind=identity.kind,
                        )
                        if identity.kind == "node":
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
        output = context.step.outputs[0]
        artifact = Artifact(output_name(output), output.type, summary)
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext, services: Any = None,
    ) -> StepOutcome:
        return skipped(context)


__all__ = ["FileExecutor", "executor_for"]
