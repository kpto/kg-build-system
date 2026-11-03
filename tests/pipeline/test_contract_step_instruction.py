from __future__ import annotations

import unittest
from dataclasses import fields

from kg_build_system.pipeline.contract.service.internal import (
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


class StepInstructionTests(unittest.TestCase):
    def test_a_step_owns_its_instruction(self) -> None:
        step = _contract().contributions[0].steps[0]

        self.assertIsInstance(step.instruction, InstructionDTO)
        self.assertEqual(step.instruction.kind, "python")

    def test_the_contract_has_no_sql_or_variables_field(self) -> None:
        for contract_type in (WorkflowContractDTO, ContributionDTO, StepDTO):
            names = {field.name for field in fields(contract_type)}
            with self.subTest(contract_type=contract_type.__name__):
                self.assertNotIn("sql", names)
                self.assertNotIn("variables", names)
        self.assertIn("instruction", {field.name for field in fields(StepDTO)})

    def test_the_codec_round_trips_sql_and_python_instructions(self) -> None:
        contract = _contract()

        document = contract_to_document(contract)

        self.assertEqual(
            document["contributions"][0]["steps"][0]["instruction"]["kind"],
            "python",
        )
        self.assertEqual(
            document["contributions"][1]["steps"][0]["instruction"]["kind"],
            "sql",
        )
        self.assertEqual(contract_from_document(document), contract)


if __name__ == "__main__":
    unittest.main()
