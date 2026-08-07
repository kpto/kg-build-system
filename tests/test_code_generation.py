from __future__ import annotations

import importlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from kg_build_system.code_generation import (
    DummyGenerationConfig,
    DummyProvider,
    GenerationError,
    GenerationSession,
    GenerationStatus,
    ProviderGenerationConfig,
    discover,
    generate,
    generated,
)


DECLARATION = '''from kg_build_system import Table, generated
from kg_build_system.code_generation import DummyGenerationConfig, DummyProvider


@generated(DummyProvider, DummyGenerationConfig(source="../schema.json"))
class TargetTable(Table):
    """Handwritten documentation."""
'''


class CodeGenerationTests(unittest.TestCase):
    def test_provider_configs_are_keyword_only_and_runtime_checked(self) -> None:
        with self.assertRaises(TypeError):
            DummyGenerationConfig("schema.json")  # type: ignore[call-arg]

        class OtherConfig(ProviderGenerationConfig):
            source: str

        with self.assertRaisesRegex(TypeError, "requires DummyGenerationConfig"):
            generated(DummyProvider, OtherConfig(source="schema.json"))  # type: ignore[arg-type]

    def _project(self, directory: str) -> Path:
        root = Path(directory)
        (root / "contracts").mkdir()
        (root / "contracts" / "__init__.py").write_text("", encoding="utf-8")
        (root / "contracts" / "target.py").write_text(DECLARATION, encoding="utf-8")
        (root / "schema.json").write_text(
            '{"fields": ['
            '{"name": "id", "type": "string"},'
            '{"name": "approvedSymbol", "type": "string", "nullable": true}'
            ']}',
            encoding="utf-8",
        )
        return root

    def test_first_generation_is_runtime_python_and_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            result = generate(root)
            self.assertEqual(result.status, GenerationStatus.CHANGED)
            authored = (root / "contracts" / "target.py").read_text(encoding="utf-8")
            sidecar = (root / "contracts" / "_generated" / "target.py").read_text(encoding="utf-8")
            self.assertIn("from ._generated.target import G_TargetTable", authored)
            self.assertIn("class TargetTable(G_TargetTable, Table):", authored)
            self.assertIn("approved_symbol: Field[str | None]", sidecar)
            self.assertIn("name='approvedSymbol'", sidecar)
            self.assertEqual(generate(root).status, GenerationStatus.CURRENT)

            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module("contracts.target")
                self.assertEqual(tuple(module.TargetTable._fields), ("id", "approved_symbol"))
                self.assertEqual(module.TargetTable.__doc__, "Handwritten documentation.")
            finally:
                sys.path.remove(str(root))
                for name in tuple(sys.modules):
                    if name == "contracts" or name.startswith("contracts."):
                        del sys.modules[name]

    def test_check_reports_missing_and_stale_outputs_without_writing(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            before = (root / "contracts" / "target.py").read_text(encoding="utf-8")
            result = generate(root, check=True)
            self.assertEqual(result.status, GenerationStatus.STALE)
            self.assertTrue(result.diagnostics)
            self.assertEqual((root / "contracts" / "target.py").read_text(encoding="utf-8"), before)
            self.assertFalse((root / "contracts" / "_generated").exists())

    def test_schema_change_regenerates_sidecar(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            generate(root)
            schema = root / "schema.json"
            schema.write_text('{"fields": [{"name": "score", "type": "number"}]}', encoding="utf-8")
            self.assertEqual(generate(root, check=True).status, GenerationStatus.STALE)
            generate(root)
            sidecar = (root / "contracts" / "_generated" / "target.py").read_text(encoding="utf-8")
            self.assertIn("score: Field[float]", sidecar)

    def test_watch_session_regenerates_only_schema_dependants(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            (root / "other_schema.json").write_text(
                '{"fields": [{"name": "name", "type": "string"}]}', encoding="utf-8"
            )
            (root / "contracts" / "other.py").write_text(
                'from kg_build_system import Table, generated\n\n'
                'from kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n\n'
                '@generated(DummyProvider, DummyGenerationConfig(source="../other_schema.json"))\n'
                'class OtherTable(Table):\n    pass\n',
                encoding="utf-8",
            )
            session = GenerationSession(root)
            session.start()
            other_sidecar = root / "contracts" / "_generated" / "other.py"
            other_before = other_sidecar.read_text(encoding="utf-8")
            (root / "schema.json").write_text(
                '{"fields": [{"name": "score", "type": "number"}]}', encoding="utf-8"
            )
            result = session.handle((Path("schema.json"),))
            self.assertEqual(result.status, GenerationStatus.CHANGED)
            self.assertEqual(
                result.changed_paths,
                (Path("contracts/_generated/target.py"),),
            )
            self.assertEqual(other_sidecar.read_text(encoding="utf-8"), other_before)

    def test_watch_session_ignores_sidecar_and_unknown_input_changes(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            session = GenerationSession(root)
            session.start()
            sidecar = root / "contracts" / "_generated" / "target.py"
            sidecar.write_text("# manual intermediate edit\n", encoding="utf-8")
            sidecar_result = session.handle((sidecar.relative_to(root),))
            unknown_result = session.handle((Path("unrelated.json"),))
            self.assertEqual(sidecar_result.status, GenerationStatus.CURRENT)
            self.assertEqual(unknown_result.status, GenerationStatus.CURRENT)
            self.assertEqual(sidecar.read_text(encoding="utf-8"), "# manual intermediate edit\n")

    def test_direct_qualified_and_aliased_decorators_are_discovered(self) -> None:
        statements = (
            "from kg_build_system import generated\nfrom kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n",
            "import kg_build_system as kbs\nimport kg_build_system.code_generation as codegen\n",
            "from kg_build_system.code_generation import generated as codegen, DummyGenerationConfig as Config, DummyProvider as ProviderType\n",
            "from kg_build_system.code_generation.decorator import generated as implementation_generated\nfrom kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n",
        )
        decorators = (
            'generated(DummyProvider, DummyGenerationConfig(source="schema.json"))',
            'kbs.generated(codegen.DummyProvider, codegen.DummyGenerationConfig(source="schema.json"))',
            'codegen(ProviderType, Config(source="schema.json"))',
            'implementation_generated(DummyProvider, DummyGenerationConfig(source="schema.json"))',
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "schema.json").write_text('{"fields": [{"name": "id"}]}', encoding="utf-8")
            for index, (statement, decorator) in enumerate(zip(statements, decorators, strict=True)):
                (root / f"case_{index}.py").write_text(
                    statement + f'@{decorator}\nclass C{index}:\n    pass\n',
                    encoding="utf-8",
                )
            self.assertEqual(len(discover(root)), 4)

    def test_misplaced_or_dynamic_decorator_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.py").write_text(
                'from kg_build_system import generated\n'
                'from kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n'
                '@staticmethod\n@generated(DummyProvider, DummyGenerationConfig(source=find_schema()))\nclass Bad:\n    pass\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(GenerationError, "topmost"):
                discover(root)

    def test_provider_config_constructor_requires_keyword_arguments(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.py").write_text(
                'from kg_build_system import generated\n'
                'from kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n'
                '@generated(DummyProvider, DummyGenerationConfig("schema.json"))\n'
                'class Bad:\n    pass\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(GenerationError, "keyword arguments only"):
                discover(root)

    def test_discovery_does_not_enter_dot_directories_or_read_dot_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            hidden_directory = root / ".environment"
            hidden_directory.mkdir()
            (hidden_directory / "invalid.py").write_text("this is not python", encoding="utf-8")
            (root / ".invalid.py").write_text("this is not python", encoding="utf-8")
            (root / "valid.py").write_text("value = 1\n", encoding="utf-8")
            self.assertEqual(discover(root), ())

    def test_discovery_does_not_parse_unmarked_python_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "temporarily_invalid.py").write_text("this is not python", encoding="utf-8")
            self.assertEqual(discover(root), ())

    def test_failure_does_not_write_any_requested_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            (root / "other.py").write_text(
                'from kg_build_system import Table, generated\n'
                'from kg_build_system.code_generation import DummyGenerationConfig\n'
                '@generated(Table, DummyGenerationConfig(source="schema.json"))\nclass Other:\n    pass\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TypeError, "not a code-generation Provider"):
                generate(root)
            self.assertFalse((root / "contracts" / "_generated").exists())

    def test_stacked_decorators_comments_bases_and_body_are_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "schema.json").write_text('{"fields": [{"name": "id"}]}', encoding="utf-8")
            source = (
                'from kg_build_system import generated\n\n'
                'from kg_build_system.code_generation import DummyGenerationConfig, DummyProvider\n\n'
                'class HandwrittenMixin:\n    pass\n\n'
                '# Public declaration comment.\n'
                '@generated(DummyProvider, DummyGenerationConfig(source="schema.json"))\n'
                '@staticmethod\n'
                'class TargetTable(HandwrittenMixin):\n'
                '    custom = 42\n'
            )
            path = root / "target.py"
            path.write_text(source, encoding="utf-8")
            generate(root)
            result = path.read_text(encoding="utf-8")
            self.assertIn("# Public declaration comment.\n@generated", result)
            self.assertIn('@generated(DummyProvider, DummyGenerationConfig(source="schema.json"))\n@staticmethod', result)
            self.assertIn("class TargetTable(G_TargetTable, HandwrittenMixin):", result)
            self.assertIn("    custom = 42", result)

    def test_refuses_to_overwrite_an_unowned_sidecar(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            sidecar = root / "contracts" / "_generated" / "target.py"
            sidecar.parent.mkdir()
            sidecar.write_text("# handwritten\n", encoding="utf-8")
            with self.assertRaisesRegex(GenerationError, "unowned"):
                generate(root)
            self.assertEqual(sidecar.read_text(encoding="utf-8"), "# handwritten\n")


if __name__ == "__main__":
    unittest.main()
