"""Generated package layout: facades, group modules and deterministic output."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path, PurePosixPath

from kg_build_system.generation import GenerationError, GenerationStatus, generate
from kg_build_system.generation.code_generation.model._private.generated import (
    GeneratedClass,
    GeneratedFile,
    GeneratedMember,
    GeneratedPackage,
)
from kg_build_system.generation.code_generation.model.internal import (
    DiscoveredGeneration,
    GenerationLocation,
)
from kg_build_system.generation.code_generation.model.public.requests import (
    GenerationRequest,
)
from kg_build_system.generation.code_generation.service._private.rendering import (
    render_package,
)


def _request() -> DiscoveredGeneration:
    return DiscoveredGeneration(
        GenerationRequest(
            "project.providers", "Provider",
            "project.providers", "Config",
            package="project.tables",
            asset_module="project.assets",
            asset_qualname="Estate",
        ),
        GenerationLocation(
            Path("."), Path("project/assets.py"), 1, 1,
            "estate", "project",
        ),
        Path("project/tables/estate"),
        "project.tables.estate",
    )


def _relation(name: str = "SitesSourceRelation", declaration_name: str = "sites") -> GeneratedClass:
    return GeneratedClass(
        name=name,
        base="SourceRelation",
        declaration_name=declaration_name,
    )


def _group() -> GeneratedClass:
    return GeneratedClass(
        name="EstateSourceRelationGroup",
        members=(GeneratedMember("sites", "SitesSourceRelation"),),
        base="SourceRelationGroup",
        declaration_name="estate",
    )


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def _asset_source(package: str, source: Path) -> str:
    return f'''
from kg_build_system import (
    Asset, AssetAuthority, AssetOptions, AssetProfile,
)
from kg_build_system.generation import AssetGenerationOptions, asset_generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)


@asset_generation(AssetGenerationOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(
        mode="source_relation_group", layout="files", source={str(source)!r},
    ),
    package="{package}",
))
class Estate(Asset):
    """The asset the generated package belongs to."""

    options = AssetOptions(
        name="estate",
        profile=AssetProfile(
            subject="records",
            coverage="one tree",
            authority=AssetAuthority.PRIMARY,
            basis="test",
        ),
    )
'''


class FacadeRenderingTests(unittest.TestCase):
    def test_a_declaration_free_facade_renders_only_its_header(self) -> None:
        package = GeneratedPackage((
            GeneratedFile(
                Path("sites.py"), (_relation(),), ("SitesSourceRelation",),
            ),
            GeneratedFile(Path("__init__.py"), (), ()),
        ))

        facade = render_package(_request(), package, "fingerprint")[
            PurePosixPath("__init__.py")
        ]

        self.assertNotIn("class ", facade)
        self.assertNotIn("import ", facade)
        self.assertNotIn("__all__", facade)
        self.assertTrue(
            all(not line or line.startswith("#") for line in facade.splitlines()),
            facade,
        )

    def test_a_facade_re_exports_the_group_and_the_relations(self) -> None:
        package = GeneratedPackage((
            GeneratedFile(Path("group.py"), (_group(),), ("EstateSourceRelationGroup",)),
            GeneratedFile(
                Path("sites.py"), (_relation(),), ("SitesSourceRelation",),
            ),
            GeneratedFile(
                Path("__init__.py"),
                exports=("EstateSourceRelationGroup", "SitesSourceRelation"),
            ),
        ))

        rendered = render_package(_request(), package, "fingerprint")
        facade = rendered[PurePosixPath("__init__.py")]

        self.assertNotIn("class ", facade)
        self.assertIn(
            "from project.tables.estate.group import EstateSourceRelationGroup",
            facade,
        )
        self.assertIn(
            "from project.tables.estate.sites import SitesSourceRelation",
            facade,
        )
        self.assertIn(
            "__all__ = ['EstateSourceRelationGroup', 'SitesSourceRelation']",
            facade,
        )
        self.assertIn(
            "class EstateSourceRelationGroup(SourceRelationGroup):",
            rendered[PurePosixPath("group.py")],
        )

    def test_the_renderer_refuses_a_declaration_in_a_package_initializer(self) -> None:
        package = GeneratedPackage((
            GeneratedFile(
                Path("__init__.py"), (_relation(),), ("SitesSourceRelation",),
            ),
        ))

        with self.assertRaisesRegex(GenerationError, "must be a facade"):
            render_package(_request(), package, "fingerprint")

    def test_the_renderer_refuses_a_group_outside_group_module(self) -> None:
        package = GeneratedPackage((
            GeneratedFile(
                Path("relations.py"), (_group(),), ("EstateSourceRelationGroup",),
            ),
        ))

        with self.assertRaisesRegex(GenerationError, "group.py"):
            render_package(_request(), package, "fingerprint")

    def test_one_request_renders_byte_identical_text_twice(self) -> None:
        package = GeneratedPackage((
            GeneratedFile(Path("group.py"), (_group(),), ("EstateSourceRelationGroup",)),
            GeneratedFile(
                Path("sites.py"), (_relation(),), ("SitesSourceRelation",),
            ),
            GeneratedFile(
                Path("__init__.py"),
                exports=("EstateSourceRelationGroup", "SitesSourceRelation"),
            ),
        ))

        first = render_package(_request(), package, "fingerprint")
        second = render_package(_request(), package, "fingerprint")

        self.assertEqual(
            {path: text for path, text in first.items()},
            {path: text for path, text in second.items()},
        )


class GeneratedFacadeIntegrationTests(unittest.TestCase):
    """A real generation pass writes facades, group modules and owned files."""

    def _project(self, root: Path) -> Path:
        data = root / "data"
        _write(data, "sites.json", json.dumps({"site_id": "a", "site_name": "A"}))
        _write(
            data, "readings/temperature.json",
            json.dumps({"reading_id": "t", "value": 1.0}),
        )
        _write(
            data, "readings/mechanical/vibration.json",
            json.dumps({"reading_id": "v", "value": 2.0}),
        )
        _write(root, "facade_project/__init__.py", "")
        _write(
            root, "facade_project/assets.py",
            _asset_source("facade_project.tables", data),
        )
        sys.path.insert(0, str(root))
        return root / "facade_project" / "tables" / "estate"

    @staticmethod
    def _leave(root: Path) -> None:
        sys.path.remove(str(root))
        for module in tuple(sys.modules):
            if module == "facade_project" or module.startswith("facade_project."):
                sys.modules.pop(module)

    def test_no_generated_initializer_declares_a_class(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = self._project(root)
            try:
                self.assertIs(
                    asyncio.run(generate(root)).status,
                    GenerationStatus.CHANGED,
                )

                initializers = tuple(sorted(product.rglob("__init__.py")))
                self.assertEqual(
                    [path.relative_to(product).as_posix() for path in initializers],
                    ["__init__.py", "readings/__init__.py", "readings/mechanical/__init__.py"],
                )
                for path in initializers:
                    self.assertNotIn("class ", path.read_text(encoding="utf-8"), path)

                group_modules = tuple(sorted(product.rglob("group.py")))
                self.assertEqual(
                    [path.relative_to(product).as_posix() for path in group_modules],
                    ["group.py", "readings/group.py", "readings/mechanical/group.py"],
                )
                for path in group_modules:
                    self.assertIn("class ", path.read_text(encoding="utf-8"), path)

                facade = (product / "__init__.py").read_text(encoding="utf-8")
                self.assertIn("EstateSourceRelationGroup", facade)
                self.assertIn("SitesSourceRelation", facade)
                self.assertIn("from facade_project.tables.estate.group import", facade)
                self.assertIn("from facade_project.tables.estate.sites import", facade)
                self.assertIs(
                    asyncio.run(generate(root, check=True)).status,
                    GenerationStatus.CURRENT,
                )
            finally:
                self._leave(root)

    def test_an_edited_or_missing_facade_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = self._project(root)
            facade = product / "__init__.py"
            try:
                asyncio.run(generate(root))
                original = facade.read_text(encoding="utf-8")
                facade.write_text(original + "\n# edited by hand\n", encoding="utf-8")
                self.assertIs(
                    asyncio.run(generate(root, check=True)).status,
                    GenerationStatus.STALE,
                )

                facade.unlink()
                self.assertIs(
                    asyncio.run(generate(root, check=True)).status,
                    GenerationStatus.STALE,
                )
                asyncio.run(generate(root))
                self.assertIs(
                    asyncio.run(generate(root, check=True)).status,
                    GenerationStatus.CURRENT,
                )
            finally:
                self._leave(root)

    def test_a_removed_relation_orphans_its_generated_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = self._project(root)
            stale_module = product / "readings" / "temperature.py"
            try:
                asyncio.run(generate(root))
                (root / "data" / "readings" / "temperature.json").unlink()
                result = asyncio.run(generate(root, check=True, regenerate=True))

                self.assertIs(result.status, GenerationStatus.STALE)
                self.assertTrue(
                    any(
                        "readings/temperature.py" in diagnostic
                        and "is missing, stale, altered, or orphaned" in diagnostic
                        for diagnostic in result.diagnostics
                    ),
                    result.diagnostics,
                )
                self.assertTrue(stale_module.is_file())
            finally:
                self._leave(root)

    def test_a_removed_request_orphans_its_product(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = self._project(root)
            try:
                asyncio.run(generate(root))
                _write(
                    root, "facade_project/assets.py",
                    '''
from kg_build_system import Asset, AssetOptions

class Estate(Asset):
    """An asset without a generation request."""

    options = AssetOptions()
''',
                )
                result = asyncio.run(generate(root, check=True))

                self.assertIs(result.status, GenerationStatus.STALE)
                self.assertTrue(
                    any(
                        "is missing, stale, altered, or orphaned" in diagnostic
                        for diagnostic in result.diagnostics
                    ),
                    result.diagnostics,
                )
                self.assertTrue(product.is_dir())
            finally:
                self._leave(root)


if __name__ == "__main__":
    unittest.main()
