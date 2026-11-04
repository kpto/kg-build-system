from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path, PurePosixPath

from kg_build_system.generation import (
    GenerationError,
    GenerationStatus,
    discover,
    discover_file,
    generate,
)
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.generation.code_generation.model._private.generated import (
    GeneratedAsset,
    GeneratedClass,
    GeneratedFile,
    GeneratedPackage,
)
from kg_build_system.generation.code_generation.model.internal import (
    DiscoveredGeneration,
    GenerationLocation,
    ProviderContext,
)
from kg_build_system.generation.code_generation.model.public.requests import (
    GenerationRequest,
)
from kg_build_system.generation.code_generation.service._private.rendering import (
    render_package,
)


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def _asset_source(
    *,
    package: str,
    class_name: str,
    options: str,
    configuration: str,
    guard: bool = False,
) -> str:
    guard_line = (
        '\nraise RuntimeError("discovery must not import the asset module")\n'
        if guard else ""
    )
    return f'''
from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetSemantics,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig({configuration}),
    package="{package}",
))
class {class_name}(Asset):
    """The asset the generated tables belong to."""

    options = AssetOptions(
        {options}
    )
{guard_line}
'''


def _estate_options(locator: str = "/data/estate", *, named: bool = True) -> str:
    name = 'name="estate",\n        ' if named else ""
    return f'''{name}semantics=AssetSemantics(
            subject="records",
            coverage="one directory",
            authority=AssetAuthority.PRIMARY,
            basis="test",
        ),
        layout=AssetLayout(
            kind="json",
            locator={locator!r},
            format="json",
            members={{"sites": "sites.json"}},
        ),'''


class CodegenDiscoveryTests(unittest.TestCase):
    def test_discovery_finds_the_decorated_asset_without_importing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root, "sample/__init__.py", "")
            path = _write(root, "sample/assets.py", _asset_source(
                package="sample.tables",
                class_name="Estate",
                options=_estate_options(),
                configuration=(
                    'mode="table_group", layout="files", '
                    'override={"surveys.surveyed_on": {"type": "timestamp"}}'
                ),
                guard=True,
            ))

            requests = discover(root)

            self.assertEqual(len(requests), 1)
            request = requests[0]
            self.assertEqual(request.location.request_id, "estate")
            self.assertEqual(request.location.source_path, path)
            self.assertEqual(request.request.package, "sample.tables")
            self.assertEqual(request.request.asset_module, "sample.assets")
            self.assertEqual(request.request.asset_qualname, "Estate")
            self.assertEqual(len(request.request.asset_digest), 64)
            self.assertEqual(request.request.provider_module, (
                "kg_build_system.generation.code_generation.builtins"
            ))
            self.assertEqual(request.request.provider_qualname, "InferDataContractProvider")
            self.assertEqual(request.request.configuration, {
                "mode": "table_group",
                "layout": "files",
                "override": {"surveys.surveyed_on": {"type": "timestamp"}},
            })
            self.assertEqual(request.product_path, Path("sample/tables/estate"))
            self.assertEqual(request.package_import, "sample.tables.estate")
            self.assertEqual(discover_file(root, path), requests)

    def test_an_undecorated_asset_is_ignored(self) -> None:
        undecorated = f'''

class Plain(Asset):
    """An asset without a generation contract."""

    options = AssetOptions(
        {_estate_options(named=False)}
    )
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root, "sample/__init__.py", "")
            _write(root, "sample/assets.py", _asset_source(
                package="sample.tables",
                class_name="Estate",
                options=_estate_options(),
                configuration='mode="table"',
            ) + undecorated)

            requests = discover(root)

            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].location.request_id, "estate")
            self.assertEqual(requests[0].request.asset_qualname, "Estate")

    def test_the_package_renderer_uses_the_generic_asset_base(self) -> None:
        request = DiscoveredGeneration(
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
        declaration = GeneratedClass(
            name="SitesTable",
            base="Table",
            asset=GeneratedAsset("project.assets", "Estate"),
            declaration_name="sites",
        )
        package = GeneratedPackage((
            GeneratedFile(
                Path("__init__.py"),
                declarations=(declaration,),
                exports=("SitesTable",),
            ),
        ))

        rendered = render_package(request, package, "fingerprint")

        self.assertIn(
            "class SitesTable(Table[Estate]):",
            rendered[PurePosixPath("__init__.py")],
        )
        self.assertIn(
            "from project.assets import Estate",
            rendered[PurePosixPath("__init__.py")],
        )

    def test_the_asset_name_defaults_to_snake_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root, "sample/__init__.py", "")
            _write(root, "sample/assets.py", _asset_source(
                package="sample.tables",
                class_name="EstateData",
                options=_estate_options(named=False),
                configuration='mode="table"',
            ))

            request = discover(root)[0]

            self.assertEqual(request.location.request_id, "estate_data")
            self.assertEqual(request.product_path, Path("sample/tables/estate_data"))

    def test_a_package_root_is_not_repeated_in_the_product_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "reference_project"
            root.mkdir()
            _write(root, "__init__.py", "")
            _write(root, "assets.py", _asset_source(
                package="reference_project.tables",
                class_name="Estate",
                options=_estate_options(),
                configuration='mode="table"',
            ))

            request = discover(root)[0]

            self.assertEqual(request.request.asset_module, "reference_project.assets")
            self.assertEqual(request.product_path, Path("tables/estate"))
            self.assertEqual(request.package_import, "reference_project.tables.estate")

    def test_a_decorated_class_must_be_an_asset(self) -> None:
        source = '''
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(mode="table"),
    package="sample.tables",
))
class NotAnAsset:
    pass
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root, "sample/__init__.py", "")
            _write(root, "sample/assets.py", source)

            with self.assertRaises(GenerationError):
                discover(root)

    def test_the_provider_refuses_a_request_without_a_source_or_layout(self) -> None:
        context = ProviderContext(
            Path("."), Path("assets.py"), "sample",
            DataContractInferenceConfig(mode="table"),
        )
        with self.assertRaisesRegex(GenerationError, "source= or an asset layout"):
            asyncio.run(InferDataContractProvider.generate(context))

    def test_generation_uses_the_asset_layout_and_renders_the_asset_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(root, "codegen_project/__init__.py", "")
            _write(root, "codegen_project/data.json", json.dumps({"id": 1, "name": "x"}))
            _write(root, "codegen_project/assets.py", _asset_source(
                package="codegen_project.tables",
                class_name="CodegenSample",
                options=_estate_options(
                    str(root / "codegen_project" / "data.json"), named=False,
                ),
                configuration='mode="table"',
            ))
            sys.path.insert(0, str(root))
            try:
                result = asyncio.run(generate(root))
                self.assertIs(result.status, GenerationStatus.CHANGED)
                product = (
                    root / "codegen_project" / "tables" / "codegen_sample"
                    / "__init__.py"
                )
                rendered = product.read_text(encoding="utf-8")
                self.assertIn("from codegen_project.assets import CodegenSample", rendered)
                self.assertIn("class CodegenSampleTable(Table[CodegenSample]):", rendered)
                self.assertIs(
                    asyncio.run(generate(root, check=True)).status,
                    GenerationStatus.CURRENT,
                )
            finally:
                sys.path.remove(str(root))
                sys.modules.pop("codegen_project.assets", None)
                sys.modules.pop("codegen_project", None)


if __name__ == "__main__":
    unittest.main()
