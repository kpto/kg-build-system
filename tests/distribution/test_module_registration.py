from __future__ import annotations

import unittest

from kg_build_system.distribution import (
    CollapseExactDuplicatesModule,
    CoreModule,
    FileModule,
    FileModuleConfiguration,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    MetaGraphModule,
    MetaGraphModuleConfiguration,
    Neo4jModule,
    Neo4jModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
    register_module,
)


class ModuleRegistrationTests(unittest.TestCase):
    def test_registration_pairs_the_class_with_its_configuration(self) -> None:
        configuration = FileModuleConfiguration("graph.jsonl")
        registration = register_module(FileModule, configuration)
        self.assertIs(registration.module_class, FileModule)
        self.assertIs(registration.configuration, configuration)

    def test_registration_constructs_a_default_configuration(self) -> None:
        registration = register_module(MetaGraphModule)
        self.assertIsInstance(
            registration.configuration, MetaGraphModuleConfiguration,
        )
        self.assertEqual(
            registration.configuration.relative_path, "meta_graph.json",
        )

    def test_registration_rejects_a_foreign_configuration(self) -> None:
        with self.assertRaises(TypeError):
            register_module(FileModule, MetaGraphModuleConfiguration())

    def test_registration_is_inert_and_serialisable(self) -> None:
        registration = register_module(
            RejectConflictingNonNullValuesModule,
            RejectConflictingNonNullValuesConfiguration(fail_on_error=False),
        )
        self.assertEqual(
            registration.configuration.to_json(), {"fail_on_error": False},
        )


class ModuleIdentityTests(unittest.TestCase):
    def test_supplied_module_ids_and_versions_are_stable(self) -> None:
        expected = {
            CoreModule: ("core", "3"),
            CollapseExactDuplicatesModule: ("collapse_exact_duplicates", "1"),
            MergeCompatibleFactsModule: ("merge_compatible_facts", "1"),
            RejectConflictingNonNullValuesModule: (
                "reject_conflicting_non_null_values", "1",
            ),
            FileModule: ("file", "1"),
            MetaGraphModule: ("meta_graph", "2"),
            Neo4jModule: ("neo4j", "2"),
        }
        for module_class, identity in expected.items():
            with self.subTest(module=module_class.__name__):
                self.assertEqual((module_class.ID, module_class.VERSION), identity)

    def test_each_module_declares_its_configuration_type(self) -> None:
        self.assertIs(CoreModule.CONFIGURATION_TYPE().__class__, CoreModule.CONFIGURATION_TYPE)
        self.assertIsInstance(
            MergeCompatibleFactsModule.CONFIGURATION_TYPE(),
            MergeCompatibleFactsModuleConfiguration,
        )
        self.assertIsInstance(
            Neo4jModule.CONFIGURATION_TYPE(), Neo4jModuleConfiguration,
        )


if __name__ == "__main__":
    unittest.main()
