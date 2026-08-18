from __future__ import annotations

import ast
import unittest
from dataclasses import fields
from pathlib import Path

import kg_build_system
from kg_build_system import value_expression
from kg_build_system.expressions.ir import ExpressionIRBase
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.models import WorkflowStep, WorkflowStepDraft
from kg_build_system.workflow.services import ExecutionServices


class DomainBoundaryTests(unittest.TestCase):
    def test_modules_receive_relation_services_not_duckdb_storage_policy(self) -> None:
        service_fields = {item.name for item in fields(ExecutionServices)}
        self.assertIn("relations", service_fields)
        self.assertNotIn("duckdb", service_fields)
        self.assertNotIn("duckdb_compression", service_fields)

    def test_compilation_irs_are_not_exported_by_public_facades(self) -> None:
        self.assertNotIn("BuildBlueprint", kg_build_system.__all__)
        self.assertFalse(any(name.endswith("IR") for name in kg_build_system.__all__))

    def test_authoring_expressions_retain_domain_models_not_irs(self) -> None:
        self.assertNotIsInstance(value_expression(1).model, ExpressionIRBase)

    def test_public_api_exposes_only_the_selection_expression_model(self) -> None:
        self.assertFalse(any(
            name.endswith("ValueExpression") and name != "ValueExpression"
            for name in kg_build_system.__all__
        ))
        self.assertIn("ValueSelection", kg_build_system.__all__)
        self.assertIn("ValueExpression", kg_build_system.__all__)

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

    def test_workflow_does_not_depend_on_compile(self) -> None:
        package = Path(kg_build_system.__file__).parent
        for path in (package / "workflow").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(
                any(module == "compile" or module.startswith("compile.") for module in imports),
                f"{path} depends on the compile domain",
            )

    def test_compile_does_not_depend_on_concrete_modules(self) -> None:
        package = Path(kg_build_system.__file__).parent
        for path in (package / "compile").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(
                any(module.startswith("modules.") for module in imports),
                f"{path} imports a concrete module",
            )

    def test_assembly_inputs_do_not_leak_into_executable_workflow_models(self) -> None:
        self.assertNotIn(
            "assembly_preference", {item.name for item in fields(WorkflowStep)}
        )
        self.assertIn(
            "assembly_preference", {item.name for item in fields(WorkflowStepDraft)}
        )

    def test_workflow_contract_has_only_workflow_semantics_and_provenance(self) -> None:
        self.assertEqual(
            set(WorkflowContractIR.model_fields),
            {"schema_version", "workflow", "workflow_fingerprint", "provenance"},
        )


if __name__ == "__main__":
    unittest.main()
