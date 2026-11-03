from __future__ import annotations

import unittest

from kg_build_system.generation.code_generation import generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


class GenerationRequestTests(unittest.TestCase):
    def test_a_generation_request_is_inert(self) -> None:
        request = generation(
            InferDataContractProvider,
            DataContractInferenceConfig(source="input.json", mode="table"),
        )
        self.assertIs(request.provider, InferDataContractProvider)
        self.assertEqual(request.configuration.source, "input.json")


if __name__ == "__main__":
    unittest.main()
