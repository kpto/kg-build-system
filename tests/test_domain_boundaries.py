from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system
from kg_build_system import value_expression
from kg_build_system.expressions.ir import ExpressionIRBase


class DomainBoundaryTests(unittest.TestCase):
    def test_compilation_irs_are_not_exported_by_public_facades(self) -> None:
        self.assertNotIn("BuildBlueprint", kg_build_system.__all__)
        self.assertNotIn("BuildContract", kg_build_system.__all__)
        self.assertFalse(any(name.endswith("IR") for name in kg_build_system.__all__))

    def test_authoring_expressions_retain_domain_models_not_irs(self) -> None:
        self.assertNotIsInstance(value_expression(1).expression, ExpressionIRBase)

    def test_domain_model_modules_do_not_import_compilation_irs(self) -> None:
        package = Path(kg_build_system.__file__).parent
        model_modules = (
            package / "annotations" / "models.py",
            package / "binding" / "models.py",
            package / "expressions" / "models.py",
            package / "table" / "models.py",
            package / "topology" / "models.py",
            package / "types" / "models.py",
            package / "workflow" / "models.py",
        )
        for path in model_modules:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(
                any(module == "ir" or module.endswith(".ir") for module in imported),
                f"{path} imports a compilation IR module",
            )


if __name__ == "__main__":
    unittest.main()
