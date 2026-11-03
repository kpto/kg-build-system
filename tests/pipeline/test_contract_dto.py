from __future__ import annotations

import unittest

from kg_build_system.pipeline.execution.service.internal.contract_codec import (
    contract_from_document,
    contract_to_document,
)
from kg_build_system.pipeline.contract.model.public import (
    ArtifactTypeDTO,
    ConnectionDTO,
    ContributionDTO,
    InputDTO,
    InstructionDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    OutputDTO,
    PublicationDTO,
    StepDTO,
    WorkflowContractDTO,
)


def _module(module_id: str, import_module: str) -> ModuleDefinitionDTO:
    return ModuleDefinitionDTO(
        reference=ModuleReferenceDTO(
            module_id=module_id,
            import_module=import_module,
            class_qualname="Module",
            implementation_version="1",
            configuration={"setting": ["value", 1, True, None]},
        ),
    )


def _contract() -> WorkflowContractDTO:
    text = ArtifactTypeDTO("test", "text")
    return WorkflowContractDTO(
        contributions=(
            ContributionDTO(
                module=_module("source", "example.source"),
                steps=(
                    StepDTO(
                        name="emit",
                        inputs=(),
                        outputs=(OutputDTO(text, "value"),),
                        instruction=InstructionDTO(
                            "python",
                            {
                                "callable": "example.source.emit",
                                "arguments": {"count": 1, "flag": False},
                            },
                        ),
                    ),
                ),
            ),
            ContributionDTO(
                module=_module("sink", "example.sink"),
                steps=(
                    StepDTO(
                        name="consume",
                        inputs=(InputDTO(text, None, "value"),),
                        outputs=(PublicationDTO(text, "published"),),
                        instruction=InstructionDTO(
                            "sql",
                            {
                                "sql": "SELECT * FROM input",
                                "parameters": [1, "two"],
                            },
                        ),
                        assembly_preference="deferred",
                    ),
                ),
            ),
        ),
        connections=(
            ConnectionDTO("sink::consume.value", "source::emit.value"),
        ),
        provenance={"source": "codec-test", "nested": {"ok": True}},
    )


class ContractCodecTests(unittest.TestCase):
    def test_round_trip_preserves_both_instruction_kinds(self) -> None:
        contract = _contract()

        document = contract_to_document(contract)

        self.assertEqual(
            document["contributions"][0]["steps"][0]["instruction"],
            {
                "kind": "python",
                "payload": {
                    "callable": "example.source.emit",
                    "arguments": {"count": 1, "flag": False},
                },
            },
        )
        self.assertEqual(
            document["contributions"][1]["steps"][0]["instruction"],
            {
                "kind": "sql",
                "payload": {
                    "sql": "SELECT * FROM input",
                    "parameters": [1, "two"],
                },
            },
        )
        self.assertEqual(contract_from_document(document), contract)


if __name__ == "__main__":
    unittest.main()
