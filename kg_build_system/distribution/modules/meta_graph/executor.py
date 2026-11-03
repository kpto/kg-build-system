"""Execution of the meta-graph description step."""
from __future__ import annotations

import json
from typing import Any

from ....kernel import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
    StepStatus,
)
from ...internal.service.paths import validate_relative_path
from ...internal.service.relations import output_path
from ...internal.service.runtime import (
    execution_services,
    instruction_payload,
    output_name,
    skipped,
)
from .document import build_document
from .instruction_dto import decode_meta_graph_instruction
from .observation import (
    _canonical_example_value,
    observed_components as _observed_components,
)
from .module import MetaGraphModule
from .render import render

_MODULE_ID = "meta_graph"
_RECORDS_INPUT = "records"


class MetaGraphExecutor:
    """Measure the received records and write the document and optional page."""

    def handle(self, context: ExecutionContext, services: Any = None) -> StepOutcome:
        services = execution_services(context, services)
        instruction = decode_meta_graph_instruction(
            instruction_payload(context),
        )
        validate_relative_path(
            instruction.relative_path, context="meta-graph document path",
        )
        path = output_path(services, instruction.relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        document = build_document(
            instruction,
            _observed_components(context, instruction, services),
            str(path),
            module_id=_MODULE_ID,
            module_version=self._module_version(context),
        )

        html_path = None
        if instruction.include_html:
            validate_relative_path(
                instruction.html_relative_path, context="meta-graph HTML path",
            )
            html_path = output_path(services, instruction.html_relative_path)
            document["summary"]["html_location"] = str(html_path)

        path.write_text(
            json.dumps(
                document, sort_keys=True, indent=2,
                default=_canonical_example_value, allow_nan=False,
            ) + "\n",
            encoding="utf-8",
        )

        if html_path is not None:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(render(document), encoding="utf-8")

        output = context.step.outputs[0]
        artifact = Artifact(
            output_name(output), output.type, dict(document["summary"]),
        )
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

    @staticmethod
    def _module_version(context: ExecutionContext) -> str:
        return (
            context.module.reference.implementation_version
            or MetaGraphModule.VERSION
        )


__all__ = ["MetaGraphExecutor"]
