from __future__ import annotations

import ast
import unittest
from dataclasses import fields
from pathlib import Path

import kg_build_system
from kg_build_system import value_expression
from kg_build_system.expressions.ir import ExpressionIRBase
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.interfaces import (
    DefinedStep, WorkflowContribution, WorkflowStep,
)
from kg_build_system.workflow.interfaces import ExecutionServices

PACKAGE = Path(kg_build_system.__file__).parent


def _top_level_imports(path: Path) -> set[str]:
    """Every other subsystem a module imports, resolved through relative imports.

    ``from ...modules.core import x`` has to read as a dependency on ``modules``;
    matching the raw module string would miss it, and that is how the edit-time
    subsystem once reached into a runtime module unnoticed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    own_package = path.relative_to(PACKAGE).parts[:-1]
    if path.name == "__init__.py":
        own_package = path.relative_to(PACKAGE).parts[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif not isinstance(node, ast.ImportFrom):
            continue
        elif node.level == 0:
            if node.module:
                found.add(node.module.split(".")[0])
            continue
        else:
            depth = node.level - 1 if path.name != "__init__.py" else node.level - 2
            base = own_package[: len(own_package) - depth] if depth else own_package
            target = ".".join([*base, *([node.module] if node.module else [])])
            found.add(target.split(".")[0] if target else "")
    return {name for name in found if name}


class DomainBoundaryTests(unittest.TestCase):
    def test_code_generation_does_not_depend_on_the_build_pipeline(self) -> None:
        """Edit-time generation may use an engine, but never a runtime subsystem.

        A shared Parquet-metadata reader belongs with the engine that provides
        ``parquet_schema()``, not with the module that happens to want it at build
        time; otherwise authoring depends on execution.
        """
        forbidden = {"compile", "workflow", "modules", "api"}
        for path in (PACKAGE / "code_generation").rglob("*.py"):
            offenders = _top_level_imports(path) & forbidden
            self.assertFalse(
                offenders, f"{path} depends on the build pipeline: {sorted(offenders)}",
            )

    def test_engines_do_not_depend_on_higher_layers(self) -> None:
        """An engine is a leaf: authoring and execution may both reach down to it."""
        forbidden = {"code_generation", "compile", "workflow", "modules", "api", "cli"}
        for path in (PACKAGE / "engines").rglob("*.py"):
            offenders = _top_level_imports(path) & forbidden
            self.assertFalse(
                offenders, f"{path} is not a leaf layer: {sorted(offenders)}",
            )

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
        """Only the downward wire-up direction is legal: compile reads workflow IR."""
        for path in (PACKAGE / "workflow").rglob("*.py"):
            offenders = _top_level_imports(path) & {"compile"}
            self.assertFalse(
                offenders, f"{path} depends on the compile domain: {sorted(offenders)}",
            )

    def test_compile_does_not_depend_on_concrete_modules(self) -> None:
        for path in (PACKAGE / "compile").rglob("*.py"):
            offenders = _top_level_imports(path) & {"modules"}
            self.assertFalse(
                offenders, f"{path} imports a concrete module: {sorted(offenders)}",
            )

    def test_only_executing_lanes_may_import_engines(self) -> None:
        """Engine knowledge stays in the lanes that actually execute against one.

        ``engines`` may be reached by the engine itself, the edit-time generation
        lane (``code_generation``), the runtime host (``workflow`` — the layer that
        opens the DuckDB connection), and ``modules`` (DuckDB-bound execution).
        Everything below those lanes — the declarative IR subsystems and the
        package-private helpers — must stay engine-agnostic.
        """
        forbidden_subsystems = (
            "types", "annotations", "expressions", "table", "topology",
            "binding", "relational", "compile",
        )
        scanned = [path for sub in forbidden_subsystems for path in (PACKAGE / sub).rglob("*.py")]
        scanned += [PACKAGE / "_frozen_json.py", *(PACKAGE / "_support").rglob("*.py")]
        for path in scanned:
            offenders = _top_level_imports(path) & {"engines"}
            self.assertFalse(
                offenders, f"{path} must not depend on a concrete engine: {sorted(offenders)}",
            )

    def test_package_never_imports_itself_by_absolute_name(self) -> None:
        """Every internal dependency is a relative import.

        The boundary walks resolve relative imports to owning subsystem names; an
        absolute ``kg_build_system.x`` import collapses to the package root and
        slips past all of them, so absolute self-imports are banned outright.
        """
        root = PACKAGE.name
        for path in PACKAGE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            absolute: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    absolute += [
                        alias.name
                        for alias in node.names
                        if alias.name == root or alias.name.startswith(f"{root}.")
                    ]
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.level == 0
                    and node.module
                    and (node.module == root or node.module.startswith(f"{root}."))
                ):
                    absolute.append(node.module)
            self.assertFalse(
                absolute, f"{path} imports the package by absolute name: {sorted(set(absolute))}",
            )

    def test_assembly_inputs_do_not_leak_into_executable_workflow_models(self) -> None:
        """Eagerness places a step while assembling and is gone from the assembled workflow."""
        self.assertIn("assembly_preference", {item.name for item in fields(WorkflowStep)})
        self.assertNotIn("assembly_preference", {item.name for item in fields(DefinedStep)})

    def test_declared_models_hold_no_reference_to_their_owner(self) -> None:
        """Domain models are amnesic: nothing on a step or an opening names what holds it."""
        from kg_build_system.workflow.interfaces import Input, Output, Publication, TakenInput

        forbidden = {"module_id", "step_id", "workflow", "owner", "parent"}
        for model in (WorkflowStep, Input, Output, Publication, DefinedStep, TakenInput):
            held = {item.name for item in fields(model)}
            self.assertFalse(
                held & forbidden, f"{model.__name__} reaches outside itself: {sorted(held & forbidden)}",
            )

    def test_a_declared_step_holds_its_openings_and_eagerness_only(self) -> None:
        """A step declares what it takes, gives out and when it runs; nothing else.

        Per-step data is the contributing module's own, filed in the variables beside its
        steps, which no rule of the workflow reads.
        """
        self.assertEqual(
            {item.name for item in fields(WorkflowStep)},
            {"inputs", "outputs", "name", "assembly_preference"},
        )
        self.assertIn("variables", {item.name for item in fields(WorkflowContribution)})

    def test_workflow_contract_has_only_workflow_semantics_and_provenance(self) -> None:
        self.assertEqual(
            set(WorkflowContractIR.model_fields),
            {"workflow", "workflow_fingerprint", "provenance"},
        )


    def test_every_domain_subpackage_declares_its_three_surfaces(self) -> None:
        """Authoring, the framework interface and IR are separate modules.

        ``cli`` is an entry point, not a domain: it has an author command and no
        internal interface or IR.
        """
        domains = (
            "annotations", "binding", "code_generation", "compile", "engines",
            "expressions", "modules", "relational", "table", "topology",
            "types", "workflow",
        )
        for name in domains:
            directory = PACKAGE / name
            self.assertTrue(
                (directory / "__init__.py").is_file(),
                f"{name} has no authoring facade",
            )
            self.assertTrue(
                (directory / "interfaces.py").is_file(),
                f"{name} has no framework interface",
            )
            self.assertTrue(
                (directory / "ir.py").is_file(),
                f"{name} has no IR",
            )

    def test_cross_subpackage_imports_use_a_declared_surface(self) -> None:
        """Only a package's facade, interface, protocols and IR are importable.

        A subpackage may import another subpackage by its ``__init__`` names,
        its ``interfaces`` names, its ``protocols`` names or its ``ir`` names.
        Importing an implementation module makes the boundary accidental again.
        """
        kernel = {"_frozen_json", "_relations", "_support"}
        declared = {"interfaces", "ir", "protocols", "__init__"}
        for path in PACKAGE.rglob("*.py"):
            relative = path.relative_to(PACKAGE)
            if relative.parts[0] in kernel or len(relative.parts) < 2:
                continue
            own = relative.parts[0]
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level == 0:
                    continue
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                target = base.joinpath(*(node.module or "").split("."))
                try:
                    target_relative = target.relative_to(PACKAGE)
                except ValueError:
                    continue
                if target_relative.parts[0] == own:
                    continue
                if target_relative.parts[0] in kernel:
                    continue
                if (target / "__init__.py").is_file():
                    continue
                self.assertIn(
                    target_relative.parts[-1], declared,
                    f"{relative} imports implementation module {target_relative}",
                )

    def test_ir_models_hold_no_instance_behavior(self) -> None:
        """IR is frozen data: no method reads ``self`` and no property derives."""
        for path in PACKAGE.rglob("ir.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        arguments = {item.arg for item in member.args.args}
                        self.assertNotIn(
                            "self", arguments,
                            f"{path}:{node.name}.{member.name} is behavior on IR",
                        )
                        self.assertFalse(
                            any(
                                isinstance(decorator, ast.Name)
                                and decorator.id == "property"
                                for decorator in member.decorator_list
                            ),
                            f"{path}:{node.name}.{member.name} is a derived IR property",
                        )

    def test_authoring_facades_export_no_internal_models(self) -> None:
        forbidden = {
            "Binding", "BuildBlueprint", "CompilationContext", "ExpressionNode",
            "FieldMetadata", "LogicalType", "ModuleCompiler", "ModuleExecutor",
            "Nullable", "RowSemantics", "RowSourcePlanIR", "WorkflowContractIR",
        }
        for name in kg_build_system.__all__:
            self.assertNotIn(name, forbidden)
            self.assertFalse(name.endswith("IR"))

    def test_workflow_models_hold_no_execution_services(self) -> None:
        from kg_build_system.workflow.models import (
            DisruptedExecutionContext, ExecutionContext, ExecutorFactoryContext,
        )

        for model in (ExecutionContext, DisruptedExecutionContext, ExecutorFactoryContext):
            held = {item.name for item in fields(model)}
            self.assertNotIn("services", held, f"{model.__name__} carries a service")


if __name__ == "__main__":
    unittest.main()
