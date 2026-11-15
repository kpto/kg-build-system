from __future__ import annotations

import unittest

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetProfile,
)
from kg_build_system.generation import (
    AssetGenerationOptions,
    GenerationError,
    asset_generation,
)
from kg_build_system.generation import code_generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


def _options() -> AssetGenerationOptions[DataContractInferenceConfig]:
    return AssetGenerationOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(mode="source_relation"),
        package="project.tables",
    )


class GenerationRequestTests(unittest.TestCase):
    def test_an_asset_generation_is_inert_and_stored_on_the_asset(self) -> None:
        options = _options()

        @asset_generation(options)
        class Contracted(Asset):
            options = AssetOptions(
                profile=AssetProfile(
                    subject="records",
                    coverage="one file",
                    authority=AssetAuthority.PRIMARY,
                    basis="test",
                ),
            )

        self.assertIs(Contracted._asset_generation, options)
        self.assertIs(options.provider, InferDataContractProvider)
        self.assertEqual(options.configuration.mode, "source_relation")
        self.assertEqual(options.package, "project.tables")

    def test_the_decorator_is_exported_from_both_frontends(self) -> None:
        self.assertIs(code_generation.asset_generation, asset_generation)
        self.assertIs(code_generation.AssetGenerationOptions, AssetGenerationOptions)

    def test_the_decorator_rejects_a_non_asset_class(self) -> None:
        with self.assertRaises(TypeError):
            asset_generation(_options())(dict)  # type: ignore[arg-type]

    def test_the_decorator_rejects_a_mismatched_configuration(self) -> None:
        with self.assertRaises(TypeError):
            asset_generation(
                AssetGenerationOptions(
                    provider=InferDataContractProvider,
                    configuration="not a configuration",  # type: ignore[arg-type]
                    package="project.tables",
                ),
            )

    def test_the_decorator_rejects_an_invalid_package(self) -> None:
        with self.assertRaises(ValueError):
            asset_generation(AssetGenerationOptions(
                provider=InferDataContractProvider,
                configuration=DataContractInferenceConfig(mode="source_relation"),
                package="not a package",
            ))

    def test_the_removed_generation_names_are_absent(self) -> None:
        self.assertFalse(hasattr(code_generation, "generation"))
        self.assertFalse(hasattr(code_generation, "Generation"))
        self.assertTrue(issubclass(GenerationError, ValueError))


if __name__ == "__main__":
    unittest.main()
