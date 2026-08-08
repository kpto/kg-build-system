from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from typing import ClassVar

from kg_build_system.code_generation import (
    GeneratedClass, GeneratedField, GeneratedFieldKind, GeneratedFile, GeneratedPackage,
    Generation, GenerationError, GenerationStatus, Provider, ProviderContext,
    ProviderGenerationConfig, discover, discover_file, generate, generation,
)


class FixtureConfig(ProviderGenerationConfig):
    source: str
    shape: str = "one"


class FixtureProvider(Provider[FixtureConfig]):
    ID: ClassVar[str] = "fixture"
    VERSION: ClassVar[str] = "1"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = FixtureConfig

    @classmethod
    def dependencies(cls, context: ProviderContext[FixtureConfig]) -> tuple[Path, ...]:
        return (context.resolve_path(context.config.source),)

    @classmethod
    def generate(cls, context: ProviderContext[FixtureConfig]) -> GeneratedPackage:
        field = GeneratedField("id", "id", GeneratedFieldKind.SCALAR, "str")
        root_name = "".join(part.title() for part in context.request_id.split("_")) + "Table"
        files = [GeneratedFile(Path("__init__.py"), (GeneratedClass(root_name, (field,), base="Table", declaration_name=context.request_id),), (root_name,))]
        if context.config.shape == "two":
            files.append(GeneratedFile(Path("extra.py"), (GeneratedClass("ExtraTable", (field,), base="Table"),), ("ExtraTable",)))
        return GeneratedPackage(tuple(files))


def request_source(source: str = "schema.json", *, name: str = "release", shape: str = "one") -> str:
    return (
        "from kg_build_system.code_generation import generation\n"
        "from tests.test_code_generation import FixtureConfig, FixtureProvider\n\n"
        f"{name} = generation(FixtureProvider, FixtureConfig(source={source!r}, shape={shape!r}))\n"
    )


class GeneratedPackageTests(unittest.TestCase):
    def _project(self, directory: str) -> Path:
        root = Path(directory)
        (root / "schema.json").write_text("{}", encoding="utf-8")
        package = root / "contracts"; package.mkdir()
        (package / "__init__.py").write_text(request_source("../schema.json"), encoding="utf-8")
        return root

    def test_generation_request_is_typed_and_inert(self) -> None:
        request = generation(FixtureProvider, FixtureConfig(source="missing.json"))
        self.assertIsInstance(request, Generation)
        self.assertEqual(request.configuration.source, "missing.json")

    def test_direct_qualified_and_aliased_generation_calls_are_discovered(self) -> None:
        forms = (
            request_source(),
            "import kg_build_system.code_generation as cg\nimport tests.test_code_generation as f\nrelease = cg.generation(f.FixtureProvider, f.FixtureConfig(source='schema.json'))\n",
            "from kg_build_system.code_generation import generation as make\nfrom tests.test_code_generation import FixtureConfig as C, FixtureProvider as P\nrelease = make(P, C(source='schema.json'))\n",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, source in enumerate(forms):
                package = root / f"p{index}"; package.mkdir(); (package / "__init__.py").write_text(source, encoding="utf-8")
            self.assertEqual(len(discover(root)), 3)

    def test_invalid_request_locations_and_shapes_are_rejected(self) -> None:
        bad = (
            ("request.py", request_source(), "must be in __init__"),
            ("__init__.py", request_source().replace("release =", "release, other ="), "plain assignment"),
            ("__init__.py", request_source().replace("release =", "owner.release ="), "plain assignment"),
            ("__init__.py", request_source().replace("FixtureConfig(source='schema.json', shape='one')", "make_config()"), "statically imported"),
            ("__init__.py", request_source(name="_hidden"), "invalid generation request"),
        )
        for filename, source, message in bad:
            with self.subTest(message=message), TemporaryDirectory() as directory:
                path = Path(directory) / filename; path.write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(GenerationError, message): discover_file(directory, path)

    def test_assignment_name_controls_package_and_complete_declaration(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            result = generate(root)
            self.assertEqual(result.status, GenerationStatus.CHANGED)
            product = root / "contracts" / "release"
            self.assertTrue((product / ".kbs-generation.json").is_file())
            generated_source = (product / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("class ReleaseTable(Table):", generated_source)
            self.assertIn("id: Field[str] = field(name='id')", generated_source)
            self.assertIn("# fmt: off", generated_source)
            self.assertIn("# isort: skip_file", generated_source)
            self.assertNotIn("G_", generated_source)
            self.assertEqual(generate(root).status, GenerationStatus.CURRENT)

    def test_generated_final_declaration_imports_directly(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module("contracts.release")
                self.assertEqual(tuple(module.ReleaseTable._fields), ("id",))
            finally:
                sys.path.remove(str(root))
                for name in tuple(sys.modules):
                    if name == "contracts" or name.startswith("contracts."): del sys.modules[name]

    def test_check_detects_missing_stale_and_orphaned_products(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            generated = root / "contracts" / "release" / "__init__.py"
            generated.unlink()
            self.assertEqual(generate(root, check=True).status, GenerationStatus.STALE)
            generate(root)
            (root / "contracts" / "__init__.py").write_text("", encoding="utf-8")
            self.assertEqual(generate(root, check=True).status, GenerationStatus.STALE)

    def test_refuses_to_overwrite_unrecognized_or_altered_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            product = root / "contracts" / "release"; product.mkdir(); (product / "__init__.py").write_text("# mine\n", encoding="utf-8")
            with self.assertRaisesRegex(GenerationError, "unrecognized"): generate(root)
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            path = root / "contracts" / "release" / "__init__.py"
            path.write_text(path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
            with self.assertRaisesRegex(GenerationError, "unexpectedly modified"): generate(root)

    def test_shape_change_prunes_only_owned_obsolete_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            init = root / "contracts" / "__init__.py"
            init.write_text(request_source("../schema.json", shape="two"), encoding="utf-8")
            generate(root); product = root / "contracts" / "release"
            (product / "notes.md").write_text("keep", encoding="utf-8")
            init.write_text(request_source("../schema.json"), encoding="utf-8")
            generate(root)
            self.assertFalse((product / "extra.py").exists())
            self.assertEqual((product / "notes.md").read_text(), "keep")

    def test_deletion_and_rename_preserve_unrecognized_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            old = root / "contracts" / "release"; (old / "notes.md").write_text("keep", encoding="utf-8")
            (root / "contracts" / "__init__.py").write_text(request_source("../schema.json", name="renamed"), encoding="utf-8")
            generate(root)
            self.assertEqual((old / "notes.md").read_text(), "keep")
            self.assertFalse((old / ".kbs-generation.json").exists())
            self.assertTrue((root / "contracts" / "renamed" / "__init__.py").exists())

    def test_pruning_removes_owned_python_bytecode_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            init = root / "contracts" / "__init__.py"
            init.write_text(request_source("../schema.json", shape="two"), encoding="utf-8")
            generate(root)
            product = root / "contracts" / "release"
            cache = product / "__pycache__"; cache.mkdir()
            owned_cache = cache / "extra.cpython-312.pyc"
            unrelated_cache = cache / "handwritten.cpython-312.pyc"
            owned_cache.write_bytes(b"owned")
            unrelated_cache.write_bytes(b"keep")

            init.write_text(request_source("../schema.json"), encoding="utf-8")
            generate(root)

            self.assertFalse(owned_cache.exists())
            self.assertEqual(unrelated_cache.read_bytes(), b"keep")

    def test_request_deletion_removes_nested_generated_bytecode(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            product = root / "contracts" / "release"
            cache = product / "__pycache__"; cache.mkdir()
            (cache / "__init__.cpython-312.pyc").write_bytes(b"owned")

            (root / "contracts" / "__init__.py").write_text("", encoding="utf-8")
            generate(root)

            self.assertFalse(product.exists())

    def test_manifest_is_machine_independent(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); generate(root)
            manifest = json.loads((root / "contracts" / "release" / ".kbs-generation.json").read_text())
            self.assertEqual(manifest["request_id"], "release")
            self.assertEqual(manifest["request_source_package"], "contracts")
            self.assertTrue(all(not Path(path).is_absolute() for path in manifest["owned_files"]))


if __name__ == "__main__": unittest.main()
