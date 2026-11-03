"""Execute the meta-graph description step."""
from __future__ import annotations

import json
from typing import Any

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    StepOutcome,
)

from ....runtime import (
    execution_services,
    instruction_payload,
    skipped,
    succeeded,
)
from .document import build_document
from .instruction_codec import decode_meta_graph_instruction
from .observation import _canonical_example_value, observed_components
from .relations import output_path
from .render import render

_MODULE_ID = "meta_graph"


class MetaGraphExecutor:
    """Measure the received records and write the document and optional page."""

    kinds = (("meta_graph", "default"),)

    def __init__(self, module_version: str = "2") -> None:
        self._module_version = module_version

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Write the document, its optional HTML page and the summary artifact.

        Example:
            ```python
            outcome = MetaGraphExecutor().execute(context, instruction)
            ```
        """
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        services = execution_services(context)
        document_instruction = decode_meta_graph_instruction(
            instruction_payload(instruction),
        )
        from kg_build_system.distribution.model.public.paths import (
            validate_relative_path,
        )

        validate_relative_path(
            document_instruction.relative_path,
            context="meta-graph document path",
        )
        path = output_path(services, document_instruction.relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        document = build_document(
            document_instruction,
            observed_components(context, document_instruction, services),
            str(path),
            module_id=_MODULE_ID,
            module_version=self._module_version,
        )

        html_path = None
        if document_instruction.include_html:
            validate_relative_path(
                document_instruction.html_relative_path,
                context="meta-graph HTML path",
            )
            html_path = output_path(
                services, document_instruction.html_relative_path,
            )
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

        return succeeded(context, dict(document["summary"]))


__all__ = ["MetaGraphExecutor"]
