from __future__ import annotations

import unittest
from unittest.mock import patch

from kg_build_system.declaration.blueprint import GraphBlueprint
from kg_build_system.declaration.languages.table.internal.dto import DataPartDTO
from kg_build_system.declaration.languages.topology.internal.dto import GraphPartDTO
from kg_build_system.pipeline.compilation import compile_blueprint
from kg_build_system.pipeline.contract import WorkflowContractDTO


def _blueprint() -> GraphBlueprint:
    return GraphBlueprint(
        graph=GraphPartDTO(),
        data=DataPartDTO(
            structs=(),
            relations=(),
            projections=(),
            sources=(),
        ),
        bindings=(),
        sources=(),
    )


class CompileReadsBlueprintTests(unittest.TestCase):
    def test_compile_blueprint_does_not_call_create_blueprint(self) -> None:
        def refuse(*args: object, **kwargs: object) -> object:
            raise AssertionError("compile_blueprint must not create a blueprint")

        with (
            patch("kg_build_system.api.create_blueprint", side_effect=refuse),
            patch(
                "kg_build_system.declaration.blueprint.create_blueprint",
                side_effect=refuse,
            ),
            patch(
                "kg_build_system.declaration.blueprint.public.service.create.create_blueprint",
                side_effect=refuse,
            ),
        ):
            contract = compile_blueprint(_blueprint(), modules=())

        self.assertEqual(contract.contributions, ())

    def test_compile_blueprint_accepts_an_existing_blueprint(self) -> None:
        blueprint = _blueprint()

        contract = compile_blueprint(blueprint, modules=())

        self.assertIsInstance(contract, WorkflowContractDTO)
        self.assertEqual(contract.contributions, ())


if __name__ == "__main__":
    unittest.main()
