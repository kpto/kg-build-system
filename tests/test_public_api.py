from __future__ import annotations

import unittest

import kg_build_system


class PublicApiTests(unittest.TestCase):
    def test_every_export_resolves(self) -> None:
        for name in kg_build_system.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(kg_build_system, name))

    def test_compile_is_the_function_not_the_package(self) -> None:
        self.assertTrue(callable(kg_build_system.compile))
        from kg_build_system.compile.models import BuildBlueprint

        self.assertEqual(BuildBlueprint.__module__, "kg_build_system.compile.ir")


if __name__ == "__main__":
    unittest.main()
