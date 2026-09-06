"""The generator's acceptance tests.

The golden input is ``tests/test_document.py``'s whole monitored-estate document, so
every requirement is proved against the shapes the UI actually produces: nested
structs, a two-level table group, a template/category/concrete topology, a coalesce
and a nullable pick-chain binding, an edge binding, a laid-out group source and
configured workflow modules.

``test_generated_project_compiles`` is the one that matters most: it writes the
project, imports every module it produced, and then runs the framework's own
``create_blueprint``/``compile`` over the namespace — the only check that the rendered
Python is legal *authoring* rather than merely legal syntax.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterator

import libcst as cst
import pytest
from kg_build_system import compile as compile_namespace
from kg_build_system import create_blueprint
from kg_build_system._support import naming as framework_naming
from kg_build_system.expressions.ir_codec import encode_expression_ir
from kg_build_system.expressions.mapping import expression_to_ir

from studio_backend.generate import render_project, write_project
from studio_backend.generate.anchors import anchors_for
from studio_backend.generate.entry import module_registrations
from studio_backend.generate.project import STATE_DIRECTORY, GenerationOutcome, OwnershipError
from studio_backend.generate.render import (
    Imports,
    GenerationError,
    declaration_name,
    literal_expression_text,
    snake_case,
)
from studio_backend.generate import topology
from studio_backend.ir.document import (
    ArrayType as DocArray,
    ProjectionField,
    Struct as DocStruct,
    StructType as DocStructType,
    Binding,
    DataField,
    FieldExpression,
    LiteralExpression,
    Module,
    NullableType as DocNullable,
    OperationExpression,
    ProjectDocument,
    PropertyBinding,
    UnitType as DocUnit,
    unit,
)

ROOT_NAME = "estate_project"
PACKAGE = "kg_project"


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def project(document: ProjectDocument, tmp_path: Path) -> GenerationOutcome:
    """The golden document, written once into a throwaway project."""
    return write_project(document, tmp_path / ROOT_NAME)


@pytest.fixture
def imported(project: GenerationOutcome) -> Iterator[GenerationOutcome]:
    """A written project whose package is importable, then forgotten completely."""
    sys.path.insert(0, str(project.project_root))
    try:
        yield project
    finally:
        sys.path.remove(str(project.project_root))
        _forget_package()


def _forget_package() -> None:
    stale = [
        name for name in sys.modules if name == PACKAGE or name.startswith(f"{PACKAGE}.")
    ]
    for name in stale:
        del sys.modules[name]


# ------------------------------------------------------------------ requirement 1


def test_every_generated_file_parses(project: GenerationOutcome) -> None:
    assert project.owned_files, "the generator produced nothing"
    for relative in project.owned_files:
        text = _read(project, relative)
        cst.parse_module(text)
        ast.parse(text)


def test_the_generated_project_imports_cleanly(imported: GenerationOutcome) -> None:
    """Import runs every class body, so this is the framework's declaration rules."""
    for relative in imported.owned_files:
        if relative.endswith(".py"):
            importlib.import_module(relative[: -len(".py")].replace("/", "."))

    sites = importlib.import_module(f"{PACKAGE}.table.sites")
    assert list(sites.SitesTable._fields) == [
        "site_id",
        "site_name",
        "premises",
        "priority_scores",
    ]
    assert sites.SitesTable._table_name == "sites"

    readings = importlib.import_module(f"{PACKAGE}.table.readings")
    temperature = importlib.import_module(f"{PACKAGE}.table.readings.temperature")
    mechanical = importlib.import_module(f"{PACKAGE}.table.readings.mechanical")
    assert readings.ReadingsTableGroup.temperature is temperature.TemperatureTable
    assert readings.ReadingsTableGroup.mechanical is mechanical.MechanicalTableGroup

    site_node = importlib.import_module(f"{PACKAGE}.topology.site").SiteNode
    assert list(site_node._properties) == ["summary", "source_version", "name", "city"]
    assert site_node._component_name == "site"


def test_the_framework_accepts_the_generated_declarations(
    imported: GenerationOutcome, document: ProjectDocument
) -> None:
    blueprint = create_blueprint(
        namespace_path=imported.project_root / document.project.package,
        modules=module_registrations(document),
    )
    assert {"site", "unit", "has_unit", "documented", "monitored_relation"} <= {
        item.name for item in blueprint.components
    }
    # Only what an expression reads reaches the blueprint: the readings catalogue and
    # the site_cities projection are declared, imported and bound, but this document
    # binds nothing that consumes them.
    assert {item.name for item in blueprint.tables} == {"sites", "equipment"}
    assert {item.name for item in blueprint.projections} == set()
    assert {item.table for item in blueprint.sources} == {"sites", "equipment"}


def test_a_projection_a_binding_reads_reaches_the_blueprint(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """The projection is a source like any other once something reads it."""
    binding = document.bindings_by_id["has_unit_binding"]
    column = FieldExpression(
        source="site_cities", path=("site_id",), logical_type=unit("str", nullable=True)
    )
    read_projection = binding.updated(
        build_key=OperationExpression(
            operator="where_present", arguments=(column,), logical_type=unit("str")
        )
    )
    mutated = document.updated(
        bindings=[
            read_projection if item.id == binding.id else item for item in document.bindings
        ]
    )
    root = tmp_path / "projection_project"
    outcome = write_project(mutated, root)
    sys.path.insert(0, str(root))
    try:
        blueprint = create_blueprint(
            namespace_path=root / mutated.project.package,
            modules=module_registrations(mutated),
        )
    finally:
        sys.path.remove(str(root))
        _forget_package()
    assert {item.name for item in blueprint.projections} == {"site_cities"}
    assert "site_cities" in {item.name for item in blueprint.tables} | {
        item.name for item in blueprint.projections
    }
    assert outcome.written


# ------------------------------------------------------------------ requirement 2


def test_generated_project_compiles(
    imported: GenerationOutcome, document: ProjectDocument
) -> None:
    """``create_blueprint`` and ``compile`` both succeed on the generated project."""
    namespace = imported.project_root / document.project.package
    modules = module_registrations(document)

    create_blueprint(namespace_path=namespace, modules=modules)
    contract = compile_namespace(namespace_path=namespace, modules=modules)

    assert contract.workflow.steps, "compilation produced no workflow steps"
    assert {"core", "collapse_exact_duplicates", "file", "meta_graph"} <= {
        item.reference.module_id for item in contract.workflow.modules
    }
    encoded = json.dumps(_jsonable(contract), sort_keys=True)
    for expected in ("sites", "equipment", "has_unit", "graph.jsonl"):
        assert expected in encoded


def test_the_generated_build_module_compiles_the_same_project(
    imported: GenerationOutcome,
) -> None:
    """The project's own ``build.py`` is a second, independent path to the contract."""
    build_module = importlib.import_module(f"{PACKAGE}.build")
    assert build_module.create_project_blueprint().bindings
    assert build_module.compile_project_build().workflow.steps


# ------------------------------------------------------------------ requirement 3


def test_rendering_twice_yields_identical_bytes(document: ProjectDocument) -> None:
    first = {item.path: item.content for item in render_project(document)}
    second = {item.path: item.content for item in render_project(document)}
    assert first and first == second


def test_the_second_write_changes_nothing(document: ProjectDocument, tmp_path: Path) -> None:
    root = tmp_path / ROOT_NAME
    first = write_project(document, root)
    before = {path: _stat(root / path) for path in _files(root)}
    manifest_before = _manifest(root)

    second = write_project(document, root)

    assert second.written == (), f"rewrote: {second.written}"
    assert second.removed == ()
    assert second.owned_files == first.owned_files
    assert {path: _stat(root / path) for path in _files(root)} == before
    assert _manifest(root) == manifest_before


def test_a_rename_prunes_the_file_it_moved(document: ProjectDocument, tmp_path: Path) -> None:
    root = tmp_path / ROOT_NAME
    first = write_project(document, root)
    # Renaming the catalogue moves the whole tree under it. Renaming a table an
    # expression reads would be a different, refused, story (see the strictness tests).
    renamed = document.updated(
        tables=[
            item.updated(name="telemetry") if item.id == "readings" else item
            for item in document.tables
        ]
    )
    second = write_project(renamed, root)

    assert "kg_project/table/readings/temperature.py" in first.owned_files
    assert "kg_project/table/readings/temperature.py" not in second.owned_files
    assert not (root / "kg_project/table/readings").exists()
    assert (root / "kg_project/table/telemetry/temperature.py").exists()
    assert (root / "kg_project/table/telemetry/mechanical/vibration.py").exists()
    assert "kg_project/table/sites/__init__.py" in second.owned_files


def test_nothing_is_written_inside_the_data_directory(
    document: ProjectDocument, tmp_path: Path
) -> None:
    root = tmp_path / ROOT_NAME
    data = root / document.project.data_directory
    data.mkdir(parents=True)
    (data / "sites.json").write_text("[]", encoding="utf-8")

    outcome = write_project(document, root)

    assert not (data / "kg_project").exists()
    assert all(not path.startswith("data/") for path in outcome.owned_files)
    assert (data / "sites.json").read_text(encoding="utf-8") == "[]"


def test_an_unowned_file_is_never_overwritten(
    document: ProjectDocument, tmp_path: Path
) -> None:
    root = tmp_path / ROOT_NAME
    occupied = root / "kg_project/topology/site/__init__.py"
    occupied.parent.mkdir(parents=True)
    occupied.write_text("# written by a person\n", encoding="utf-8")

    with pytest.raises(OwnershipError, match="topology/site/__init__.py"):
        write_project(document, root)
    assert occupied.read_text(encoding="utf-8") == "# written by a person\n"


def test_stale_byte_code_under_owned_directories_is_pruned(
    document: ProjectDocument, tmp_path: Path
) -> None:
    root = tmp_path / ROOT_NAME
    write_project(document, root)
    cache = root / "kg_project/table/sites/__pycache__"
    cache.mkdir(parents=True)
    (cache / "sites.cpython-312.pyc").write_bytes(b"stale")

    write_project(document, root)
    assert not cache.exists()


def test_an_edited_owned_file_is_reported_and_replaced(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """The file is studio's to own: the foreign edit is reported, then the document wins."""
    root = tmp_path / ROOT_NAME
    write_project(document, root)
    target = root / "kg_project/table/sites/__init__.py"
    target.write_text("# hand edited\n", encoding="utf-8")

    outcome = write_project(document, root)
    assert "kg_project/table/sites/__init__.py" in outcome.discarded_edits
    assert "Generated by kg-studio" in target.read_text(encoding="utf-8")


def test_a_package_marker_names_one_declaration_only_when_the_package_holds_one(
    project: GenerationOutcome,
) -> None:
    """A shared ``__init__.py`` must not blame one member for an error in the marker."""
    shared = _read(project, "kg_project/topology/__init__.py")
    assert "# ir:" not in shared
    single = _read(project, "kg_project/topology/site/__init__.py")
    assert "# ir: component:site" in single


# ------------------------------------------------------------------ requirement 4


def test_descriptions_are_generated_as_docstrings(project: GenerationOutcome) -> None:
    assert '"""One row per monitored site."""' in _read(project, "kg_project/table/sites/__init__.py")
    assert '"""Records which build stage produced or tracks a component."""' in _read(
        project, "kg_project/annotations.py"
    )
    common = _read(project, "kg_project/topology/common.py")
    assert '"""Topology vocabulary shared across node packages.' in common


def test_the_framework_recovers_descriptions_from_the_docstrings(
    imported: GenerationOutcome,
) -> None:
    """The docstrings are load-bearing: the framework reads them back as descriptions."""
    sites = importlib.import_module(f"{PACKAGE}.table.sites")
    assert sites.SitesTable._data_metadata["description"] == "One row per monitored site."

    common = importlib.import_module(f"{PACKAGE}.topology.common")
    documented = common.DocumentedAbstractNode
    assert documented._metadata["description"] == (
        "Category: every documented entity carries a human-readable summary."
    )


def test_a_field_description_is_written_under_the_field(
    document: ProjectDocument,
) -> None:
    from studio_backend.ir.document import DataField

    sites = document.tables_by_id["sites"]
    described = [
        field.updated(description="The registry key of the site.")
        if field.name == "site_id"
        else field
        for field in sites.fields
    ]
    mutated = document.updated(
        tables=[
            sites.updated(fields=described) if item.id == sites.id else item
            for item in document.tables
        ]
    )
    rendered = _content(mutated, "kg_project/table/sites/__init__.py")
    assert (
        "site_id: Field[str | None] = field(name='site_id')\n"
        '    """The registry key of the site."""' in rendered
    )


def test_a_projection_field_description_travels_as_an_argument(
    document: ProjectDocument,
) -> None:
    """``ProjectionField`` reads no docstring, so the argument is the only channel."""
    projection = document.projections[0]
    described = projection.updated(
        fields=[
            field.updated(description="The registry key.") if field.name == "site_id" else field
            for field in projection.fields
        ]
    )
    mutated = document.updated(
        projections=[
            described if item.id == projection.id else item for item in document.projections
        ]
    )
    rendered = _content(mutated, "kg_project/table/projections/site_cities.py")
    assert "projection_field(SitesTable.site_id, description='The registry key.')" in rendered


# --------------------------------------------------- projection_field argument form


def test_a_projection_output_hands_projection_field_a_selection(
    document: ProjectDocument,
) -> None:
    """Bug 1: a trailing ``.expression`` makes pyright bind ``ProjectionField[Unknown]``.

    The output of a stack that ends in a selection must be the selection itself —
    measured: passing ``Table.field.default_to(x).expression`` (even via a variable,
    even though its revealed type is the concrete ``StrExpression``) infers
    ``ProjectionField[Unknown]`` and poisons every binding that reads the projection,
    while the selection infers ``ProjectionField[str]``.
    """
    mutated = _document_with_coalesced_projection_key(document)
    rendered = _content(mutated, "kg_project/table/projections/site_cities.py")
    assert "projection_field(SitesTable.site_id.default_to(\"(unknown)\"))" in rendered
    assert ".expression" not in rendered


def test_a_calculation_topped_projection_output_keeps_its_mid_chain_expression(
    document: ProjectDocument,
) -> None:
    """A stack topped by a calculation stays an argument chain: measured concrete.

    ``projection_field(x.expression.append("!"))`` infers ``ProjectionField[str]``,
    so only a *trailing* ``.expression`` — the descriptor access — is forbidden;
    the one the calculation methods need in the middle of the chain stays.
    """
    mutated = _document_with_coalesced_projection_key(document)
    projection = mutated.projections[0]
    site_id = next(field for field in projection.fields if field.name == "site_id")
    topped = OperationExpression(
        operator="concat",
        arguments=(
            site_id.expression,
            LiteralExpression(value="-site", logical_type=unit("str")),
        ),
        logical_type=unit("str"),
    )
    projection = projection.updated(
        fields=[
            site_id.updated(expression=topped) if field.name == "site_id" else field
            for field in projection.fields
        ]
    )
    mutated = mutated.updated(
        projections=[
            projection if item.id == projection.id else item
            for item in mutated.projections
        ]
    )
    rendered = _content(mutated, "kg_project/table/projections/site_cities.py")
    assert (
        "    site_id = projection_field(\n"
        '        SitesTable.site_id.default_to("(unknown)").expression.append("-site"),\n'
        "    )\n"
    ) in rendered


def test_a_long_projection_chain_wraps_inside_the_call(
    document: ProjectDocument,
) -> None:
    """The wrap belongs to ``projection_field(`` — not a second pair of parentheses.

    A deep pick path cannot fit on one line; every part then sits one indent inside
    the class body, which keeps the chain's own indentation and the statement's
    aligned — the defect the old renderer left at the outer level.
    """
    projection = document.projections[0]
    scores = next(field for field in projection.fields if field.name == "score")
    deep = FieldExpression(
        source="sites",
        path=("premises", "contact", "location", "city"),
        logical_type=unit("str", nullable=True),
    )
    mutated = document.updated(
        projections=[
            projection.updated(
                fields=[
                    scores.updated(expression=deep) if field.name == "score" else field
                    for field in projection.fields
                ]
            )
            if item.id == projection.id
            else item
            for item in document.projections
        ]
    )
    rendered = _content(mutated, "kg_project/table/projections/site_cities.py")
    assert "projection_field((\n" not in rendered
    assert (
        "    score = projection_field(\n"
        "        SitesTable.premises\n"
        "        .pick(lambda value: value.contact)\n"
        "        .pick(lambda value: value.location)\n"
        "        .pick(lambda value: value.city),\n"
        "    )\n"
    ) in rendered


def test_a_literal_only_projection_output_is_annotated(
    document: ProjectDocument,
) -> None:
    """``value_expression`` returns ``ValueExpression[Any]``, so the annotation types it.

    Measured: unannotated the field infers ``ProjectionField[Any]``; the explicit
    ``ProjectionField[str]``/``ProjectionField[str | None]`` is what keeps reads
    concrete, and pyright accepts the assignment in strict mode.
    """
    projection = document.projections[0]
    pinned = ProjectionField(
        name="kind",
        expression=LiteralExpression(value="site", logical_type=unit("str")),
    )
    mutated = document.updated(
        projections=[
            projection.updated(fields=(*projection.fields, pinned))
            if item.id == projection.id
            else item
            for item in document.projections
        ]
    )
    rendered = _content(mutated, "kg_project/table/projections/site_cities.py")
    assert (
        'kind: ProjectionField[str] = projection_field(value_expression("site"))' in rendered
    )
    imports = rendered.split("class ")[0]
    assert "ProjectionField" in imports  # imported for the annotation, not only used


# ------------------------------------------------------------------ requirement 5


def test_a_group_source_renders_the_catalogue_layout(project: GenerationOutcome) -> None:
    sources = _read(project, "kg_project/sources.py")
    assert 'layout="{group_path}/{table_name}.json"' in sources
    assert "target=ReadingsTableGroup," in sources
    assert "str(DATA)," in sources


def test_a_table_source_renders_its_file_and_version(project: GenerationOutcome) -> None:
    sources = _read(project, "kg_project/sources.py")
    assert 'str(DATA / "sites.json")' in sources
    assert 'version="registry-2026-08"' in sources
    assert "equipment_source = bind_source(" in sources


# ---------------------------------------------------------------- the IR contract


def test_pick_folds_a_path_into_one_field_reference(imported: GenerationOutcome) -> None:
    """A chain of picks on a field reference records one node, with no struct_field."""
    bindings = importlib.import_module(f"{PACKAGE}.bindings.site")
    encoded = _ir(bindings.site_binding.properties.city)
    # The binding coalesces a fallback, and the value it guards is the folded path.
    assert encoded["operator"] == "coalesce"
    folded = encoded["arguments"][0]
    assert folded["kind"] == "field"
    assert folded["path"] == ["premises", "contact", "location", "city"]
    assert "struct_field" not in json.dumps(encoded)


def test_a_generated_binding_expression_matches_the_document_expression(
    imported: GenerationOutcome, document: ProjectDocument
) -> None:
    """Compiling the generated Python reproduces the document's expression IR exactly."""
    bindings = importlib.import_module(f"{PACKAGE}.bindings.site")
    site_binding = document.bindings_by_id["site_binding"]

    compiled = {
        "build_key": _ir(bindings.site_binding.build_key),
        "name": _ir(bindings.site_binding.properties.name),
        "city": _ir(bindings.site_binding.properties.city),
    }
    authored = {
        "build_key": site_binding.build_key.model_dump(mode="json"),
        "name": next(item.expression for item in site_binding.properties if item.name == "name"),
        "city": next(item.expression for item in site_binding.properties if item.name == "city"),
    }
    for key, expression in authored.items():
        expected = (
            expression.model_dump(mode="json")
            if hasattr(expression, "model_dump")
            else expression
        )
        assert compiled[key] == expected, key


def test_default_to_lowers_to_coalesce_with_the_value_first(
    imported: GenerationOutcome,
) -> None:
    bindings = importlib.import_module(f"{PACKAGE}.bindings.site")
    encoded = _ir(bindings.site_binding.properties.name)
    assert encoded["operator"] == "coalesce"
    assert encoded["arguments"][0]["path"] == ["site_name"]
    assert encoded["arguments"][1] == {
        "kind": "literal",
        "value": "Unnamed site",
        "logical_type": {"kind": "unit", "name": "str"},
    }


def test_prepend_and_append_are_concat_distinguished_by_order(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """Both spellings compile to ``concat``; only the argument order says which."""
    for which, expected_value_index in (("prefix", 0), ("suffix", 1)):
        mutated = _document_with_concat(document, which=which)
        root = tmp_path / f"concat_{which}"
        write_project(mutated, root)
        sys.path.insert(0, str(root))
        try:
            bindings = importlib.import_module(f"{PACKAGE}.bindings.site")
            encoded = _ir(bindings.site_binding.properties.name)
        finally:
            sys.path.remove(str(root))
            _forget_package()
        assert encoded["operator"] == "concat"
        literal_index = expected_value_index
        assert encoded["arguments"][literal_index]["kind"] == "literal"
        assert encoded["arguments"][literal_index]["value"] == (
            "Site: " if which == "prefix" else " Site"
        )
        # The other half is the document's own ``name`` stack: a coalesce over the
        # site_name column, which the generated code reproduced unchanged.
        other = encoded["arguments"][1 - literal_index]
        assert other["operator"] == "coalesce"
        assert other["arguments"][0]["path"] == ["site_name"]


def test_a_temporal_literal_keeps_its_unit_after_freezing_as_text() -> None:
    """The document holds canonical text; the code holds the representative class."""
    imports = Imports(PACKAGE)
    text = literal_expression_text(
        "2026-08-01T12:30:00", unit("timestamp"), imports
    )
    assert text == 'value_expression(Timestamp.fromisoformat("2026-08-01T12:30:00"))' 
    assert "from kg_build_system.types import Timestamp" in imports.block()


def test_a_null_literal_carries_its_explicit_nullable_type() -> None:
    imports = Imports(PACKAGE)
    assert literal_expression_text(None, unit("str", nullable=True), imports) == (
        "value_expression(None, logical_type=NullableType(STR))"
    )
    assert "from kg_build_system.types import NullableType, STR" in imports.block()


def test_without_nulls_compiles_to_nothing_when_items_are_already_non_null(
    document: ProjectDocument,
) -> None:
    """The contract's rule: the call is honest either way, so it is still written."""
    from studio_backend.generate.expressions import ExpressionWriter
    from studio_backend.generate.layout import Layout

    scores = FieldExpression(
        source="sites",
        path=("priority_scores",),
        logical_type=DocNullable(
            value=DocArray(item=DocNullable(value=DocUnit(name="int")))
        ),
    )
    already_clean = OperationExpression(
        operator="without_nulls", arguments=(scores,), logical_type=scores.logical_type
    )
    imports = Imports(PACKAGE)
    stack = ExpressionWriter(document, Layout(document), imports).render(already_clean)
    assert stack.text() == "SitesTable.priority_scores.without_nulls().expression"


def test_a_nullable_expression_does_not_widen_the_declaration(document: ProjectDocument) -> None:
    """A binding that can yield null is reported, not accommodated.

    Softening the slot would emit a project that compiles while permitting records
    without the property — the silent data loss the declaration exists to prevent — so
    the generated code stays faithful and the mismatch surfaces as a gap.
    """
    site = document.components_by_id["site"]
    binding = document.bindings_by_id["site_binding"]
    nullable_name = FieldExpression(
        source="sites", path=("site_name",), logical_type=unit("str", nullable=True)
    )
    mutated = document.updated(
        bindings=[
            binding.updated(
                properties=[
                    item.updated(expression=nullable_name) if item.name == "name" else item
                    for item in binding.properties
                ]
            )
            if item.id == binding.id
            else item
            for item in document.bindings
        ]
    )
    rendered = _content(mutated, "kg_project/topology/site/__init__.py")
    assert "name: PropertySlot[str] = property()" in rendered
    assert "name: PropertySlot[str | None] = property()" not in rendered

    gaps = {(gap.component, gap.property, gap.kind) for gap in topology.slot_gaps(mutated)}
    assert ("site", "name", "nullable_into_non_null") in gaps
    assert site is not None  # the declaration itself is untouched by the report


def test_a_slot_no_binding_fills_stays_required_and_is_reported(document: ProjectDocument) -> None:
    """An unfilled required slot is the author's mistake, not a licence to weaken."""
    binding = document.bindings_by_id["site_binding"]
    mutated = document.updated(
        bindings=[
            binding.updated(
                properties=[item for item in binding.properties if item.name != "summary"]
            )
            if item.id == binding.id
            else item
            for item in document.bindings
        ]
    )
    common = _content(mutated, "kg_project/topology/common.py")
    assert "summary: PropertySlot[str] = property()" in common
    assert "property(default=None)" not in common

    gaps = {(gap.component, gap.property, gap.kind) for gap in topology.slot_gaps(mutated)}
    assert ("documented", "summary", "unfilled") in gaps


def test_an_optional_slot_left_unfilled_is_not_a_gap(document: ProjectDocument) -> None:
    """``property(default=None)`` is a stated permission to state nothing."""
    site = document.components_by_id["site"]
    binding = document.bindings_by_id["site_binding"]
    mutated = document.updated(
        components=[
            site.updated(
                properties=[
                    item.updated(optional=True, logical_type=unit("str", nullable=True))
                    if item.name == "name"
                    else item
                    for item in site.properties
                ]
            )
            if item.id == site.id
            else item
            for item in document.components
        ],
        bindings=[
            binding.updated(
                properties=[item for item in binding.properties if item.name != "name"]
            )
            if item.id == binding.id
            else item
            for item in document.bindings
        ],
    )
    gaps = {(gap.component, gap.property, gap.kind) for gap in topology.slot_gaps(mutated)}
    assert ("site", "name", "unfilled") not in gaps


# ------------------------------------------------------ workflow module configuration


def _replace_module_configuration(
    document: ProjectDocument, module_id: str, configuration: Any
) -> ProjectDocument:
    """Re-point one module's configuration, as the UI or a hand-edit would."""
    return document.updated(
        modules=[
            item.updated(configuration=configuration) if item.id == module_id else item
            for item in document.modules
        ]
    )


def test_a_module_configured_with_an_empty_object_receives_no_configuration(
    document: ProjectDocument,
) -> None:
    """``configuration: {}`` registers the module bare — the argument was pure noise.

    The UI seeds ``{}`` for a module whose catalogue default is an empty object, and an
    all-defaults configuration is exactly what ``register_module`` rebuilds when the
    argument is omitted, so the faithful rendering leaves it off and, crucially, never
    imports the module's private ``_Configuration`` class.
    """
    emptied = _replace_module_configuration(document, "collapse_exact_duplicates", {})
    build = _content(emptied, "kg_project/build.py")
    assert "register_module(CollapseExactDuplicatesModule)" in build
    assert "register_module(CollapseExactDuplicatesModule," not in build
    assert "_Configuration" not in build
    assert "operators.deduplication" not in build


def test_a_configured_module_still_renders_its_configuration(
    document: ProjectDocument,
) -> None:
    """Guard 1 must not swallow real values: ``file`` and ``meta_graph`` render verbatim."""
    configured = document.updated(
        modules=[
            item.updated(
                configuration={"relative_path": "meta_graph.json", "include_html": True}
            )
            if item.id == "meta_graph"
            else item
            for item in document.modules
        ]
    )
    build = _content(configured, "kg_project/build.py")
    assert "register_module(FileModule, FileModuleConfiguration(relative_path='graph.jsonl'))" in build
    assert (
        "register_module(MetaGraphModule, "
        "MetaGraphModuleConfiguration(relative_path='meta_graph.json', include_html=True))"
    ) in build
    assert "import _Configuration" not in build


def test_the_generated_and_executed_module_lists_agree_for_an_empty_configuration(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """``build.py`` and the studio's own compile resolve ``{}`` through the same code.

    Both readings of ``document.modules`` have to produce one list; a divergence
    between what studio writes to disk and what it executes would be worse than the
    private import this replaces, so the imported ``_modules()`` must equal
    :func:`module_registrations` element for element.
    """
    emptied = _replace_module_configuration(document, "collapse_exact_duplicates", {})
    root = tmp_path / "agree_project"
    write_project(emptied, root)
    sys.path.insert(0, str(root))
    try:
        build = importlib.import_module(f"{PACKAGE}.build")
        from_source = list(build._modules())
    finally:
        sys.path.remove(str(root))
        _forget_package()
    from_execution = module_registrations(emptied)
    assert [item.module_class for item in from_source] == [
        item.module_class for item in from_execution
    ]
    assert from_source == from_execution


def test_a_private_configuration_with_values_is_refused(
    document: ProjectDocument, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A required-but-private configuration cannot be omitted, so refuse rather than lie.

    ``collapse_exact_duplicates`` has no fields, so ``{}`` is dropped (guard 1). This is
    the other half: a module whose configuration class is private *and* is handed values
    — omitting the argument there would silently build something other than the document
    says, so the generator names the module and the class and stops, writing no import.
    """
    import dataclasses

    import kg_build_system.modules as modules_package
    from kg_build_system.modules import Module as WorkflowModule
    from kg_build_system.modules import ModuleRegistrationConfiguration

    @dataclasses.dataclass(frozen=True)
    class _Secret(ModuleRegistrationConfiguration):
        limit: int

    class SecretModule(WorkflowModule):
        ID = "secret"
        VERSION = "1"
        CONFIGURATION_TYPE = _Secret

        @classmethod
        async def create_compiler(cls, context: Any) -> Any: ...

        @classmethod
        def create_executor(cls, context: Any) -> Any: ...

    monkeypatch.setattr(modules_package, "SecretModule", SecretModule, raising=False)
    monkeypatch.setattr(
        modules_package, "__all__", [*modules_package.__all__, "SecretModule"]
    )

    broken = document.updated(modules=[Module(id="secret", configuration={"limit": 3})])
    with pytest.raises(GenerationError) as refused:
        render_project(broken)
    message = str(refused.value)
    assert "secret" in message
    assert "_Secret" in message
    assert "not publicly constructible" in message

    root = tmp_path / "secret_project"
    with pytest.raises(GenerationError):
        write_project(broken, root)
    assert not (root / PACKAGE / "build.py").exists()


# ------------------------------------------------------------------------ anchors


def test_the_anchor_index_locates_the_document_in_the_code(
    project: GenerationOutcome,
) -> None:
    payload = json.loads(project.anchors_path.read_text(encoding="utf-8"))
    assert payload["format_version"] == 1
    assert payload["revision"] == project.revision
    assert payload["document_fingerprint"] == project.document_fingerprint

    anchors = payload["files"]["kg_project/bindings/site/__init__.py"]
    assert anchors[0] == {
        **anchors[0],
        "ref": "binding:site_binding",
        "node": "file",
        "line": 1,
        "column": 1,
    }
    by_ref = {(item["ref"], item["node"]): item for item in anchors}
    call = by_ref[("binding:site_binding", "call")]
    keyword = by_ref[("binding:site_binding.property.city", "keyword")]
    assert call["node"] == "call"
    assert call["line"] < keyword["line"] <= call["end_line"]
    assert keyword["node"] == "keyword"
    assert keyword["line"] == keyword["end_line"]
    assert keyword["column"] < keyword["end_column"]
    assert ("binding:site_binding.property.name", "keyword") in by_ref
    # The stack above the call is anchored too, so a type error mid-chain resolves.
    assert by_ref[("binding:site_binding.build_key", "expression")]["line"] < call["line"]


def test_the_anchor_index_locates_declarations(project: GenerationOutcome) -> None:
    files = json.loads(project.anchors_path.read_text(encoding="utf-8"))["files"]
    topology = {(item["ref"], item["node"]): item for item in files["kg_project/topology/site/__init__.py"]}
    assert ("component:site", "class") in topology
    assert topology[("component:site.property.city", "member")]["node"] == "member"

    table = {(item["ref"], item["node"]): item for item in files["kg_project/table/sites/__init__.py"]}
    assert table[("table:sites.field.premises", "member")]["node"] == "member"
    assert ("struct:premises.field.contact_name", "member") in table


def test_every_anchor_position_is_one_based_and_in_range(
    project: GenerationOutcome,
) -> None:
    files = json.loads(project.anchors_path.read_text(encoding="utf-8"))["files"]
    for relative, anchors in files.items():
        lines = _read(project, relative).splitlines()
        for anchor in anchors:
            assert 1 <= anchor["line"] <= anchor["end_line"] <= len(lines), (relative, anchor)
            assert 1 <= anchor["column"] < anchor["end_column"], (relative, anchor)
            assert anchor["ref"].count(":") == 1, anchor
            assert anchor["node"] in {
                "file",
                "class",
                "member",
                "call",
                "keyword",
                "expression",
            }, anchor


def test_the_file_node_covers_an_unlabelled_line(project: GenerationOutcome) -> None:
    rendered = [item for item in render_project(document_fixture()) if item.path.endswith("build.py")][0]
    anchors = anchors_for(rendered)
    assert anchors[0]["node"] == "file"
    assert anchors[0]["ref"] == "module:collapse_exact_duplicates"
    assert anchors[0]["line"] == 1
    assert anchors[0]["end_line"] == len(rendered.content.splitlines())


def test_the_manifest_records_what_the_project_owns(project: GenerationOutcome) -> None:
    manifest = _manifest(project.project_root)
    assert manifest["format_version"] == 1
    assert manifest["document_fingerprint"] == project.document_fingerprint
    assert manifest["owned_files"] == sorted(manifest["owned_files"])
    assert manifest["owned_files"] == list(project.owned_files)
    assert set(manifest["owned_file_hashes"]) == set(manifest["owned_files"])
    assert all(value.startswith("sha256:") for value in manifest["owned_file_hashes"].values())
    assert "kg_project" in manifest["owned_directories"]
    assert manifest["generated_at"]
    assert (project.project_root / STATE_DIRECTORY / "anchors.json").exists()


# ------------------------------------------------------------- naming and layout


def test_the_generator_names_external_things_as_the_framework_does() -> None:
    samples = (
        "SitesTable",
        "PremisesContactLocationStruct",
        "site_id",
        "mm_s",
        "readings",
        "HasUnitEdge",
        "survey_period",
        "ABCTable",
        "Unit2Table",
        "vibration",
    )
    for sample in samples:
        assert snake_case(sample) == framework_naming.snake_case(sample)
    for suffixes in (("Table",), ("Struct", "Table"), ("Edge",), ("AbstractNode", "Node")):
        for sample in samples:
            assert declaration_name(sample, suffixes=suffixes) == (
                framework_naming.declaration_name(sample, suffixes=suffixes)
            )


def test_the_layout_mirrors_the_reference_project(project: GenerationOutcome) -> None:
    assert set(project.owned_files) >= {
        "kg_project/__init__.py",
        "kg_project/build.py",
        "kg_project/sources.py",
        "kg_project/annotations.py",
        "kg_project/table/__init__.py",
        "kg_project/table/sites/__init__.py",
        "kg_project/table/equipment/__init__.py",
        "kg_project/table/readings/__init__.py",
        "kg_project/table/readings/temperature.py",
        "kg_project/table/readings/mechanical/__init__.py",
        "kg_project/table/readings/mechanical/vibration.py",
        "kg_project/table/projections/site_cities.py",
        "kg_project/topology/__init__.py",
        "kg_project/topology/common.py",
        "kg_project/topology/site/__init__.py",
        "kg_project/topology/site/has_unit__unit.py",
        "kg_project/topology/unit/__init__.py",
        "kg_project/bindings/__init__.py",
        "kg_project/bindings/site/__init__.py",
        "kg_project/bindings/site/has_unit__unit.py",
    }


def test_generated_declarations_carry_their_ir_ref(project: GenerationOutcome) -> None:
    assert "# ir: table:sites" in _read(project, "kg_project/table/sites/__init__.py")
    assert "# ir: component:has_unit" in _read(
        project, "kg_project/topology/site/has_unit__unit.py"
    )
    assert "# Generated by kg-studio. Do not edit manually." in _read(
        project, "kg_project/table/sites/__init__.py"
    )


# ------------------------------------------------------------- refusals stay loud


def test_a_module_id_the_framework_does_not_export_is_refused(document: ProjectDocument) -> None:
    broken = document.updated(modules=[Module(id="no_such_module")])
    with pytest.raises(GenerationError, match="no_such_module"):
        render_project(broken)


def test_a_binding_of_an_abstract_component_still_gets_a_file(
    document: ProjectDocument,
) -> None:
    """Rendering faithfully: the framework's rejection is reported, not hidden."""
    site = document.bindings_by_id["site_binding"]
    broken = site.updated(
        id="category_binding",
        component="documented",
        properties=[
            PropertyBinding(name="summary", expression=item.expression)
            for item in site.properties
            if item.name == "name"
        ],
    )
    mutated = document.updated(
        bindings=[
            item for item in document.bindings if item.id != "site_binding"
        ]
        + [broken]
    )
    files = {item.path: item.content for item in render_project(mutated)}
    assert "# ir: binding:category_binding" in files["kg_project/bindings/documented.py"]


def test_an_expression_reading_an_undeclared_source_is_refused(
    document: ProjectDocument,
) -> None:
    broken = document.bindings_by_id["site_binding"]
    bad = broken.updated(
        build_key=FieldExpression(
            source="no_such_table", path=("x",), logical_type=unit("str")
        )
    )
    mutated = document.updated(
        bindings=[bad if item.id == broken.id else item for item in document.bindings]
    )
    with pytest.raises(GenerationError, match="no_such_table"):
        render_project(mutated)


# ------------------------------------------------------------------------- helpers


def document_fixture() -> ProjectDocument:
    """The golden document outside the fixture machinery (used by one direct test)."""
    sys.path.insert(0, str(Path(__file__).parent))
    import test_document

    for attribute in ("_fixture_function", "__wrapped__"):
        function = getattr(test_document.document, attribute, None)
        if callable(function):
            return function()
    return test_document.document()  # type: ignore[call-arg]


def _content(document: ProjectDocument, path: str) -> str:
    return {item.path: item.content for item in render_project(document)}[path]


def _ir(expression: Any) -> dict[str, Any]:
    return encode_expression_ir(expression_to_ir(expression.model))


def _document_with_coalesced_projection_key(document: ProjectDocument) -> ProjectDocument:
    """Give the golden projection a demo-shaped output: a defaulted key, non-null str.

    ``site_cities.site_id`` becomes ``sites.site_id.default_to("(unknown)")`` — a
    stack that ends in a *selection*, the shape whose trailing ``.expression`` made
    pyright report ``ProjectionField[Unknown]`` and cascade into every binding that
    reads the projection.
    """
    projection = document.projections[0]
    site_id = next(field for field in projection.fields if field.name == "site_id")
    coalesced = site_id.updated(
        expression=OperationExpression(
            operator="coalesce",
            arguments=(
                site_id.expression,
                LiteralExpression(value="(unknown)", logical_type=unit("str")),
            ),
            logical_type=unit("str"),
        )
    )
    return document.updated(
        projections=[
            projection.updated(
                fields=[
                    coalesced if field.name == "site_id" else field
                    for field in projection.fields
                ]
            )
            if item.id == projection.id
            else item
            for item in document.projections
        ]
    )


def _document_with_projection_reading_binding(
    document: ProjectDocument,
) -> ProjectDocument:
    """The defaulted projection key, and a binding that reads it through a calculation.

    Mirrors ``studio_test_project``: the edge binding's key is the projection output
    with a constant appended — a ``concat`` whose stack lowers through
    ``.expression``, so the read is concrete only if the published field is typed.
    """
    mutated = _document_with_coalesced_projection_key(document)
    projection = mutated.projections[0]
    binding = mutated.bindings_by_id["has_unit_binding"]
    column = FieldExpression(
        source="site_cities", path=("site_id",), logical_type=unit("str")
    )
    read_projection = binding.updated(
        build_key=OperationExpression(
            operator="concat",
            arguments=(
                column,
                LiteralExpression(value="-unit", logical_type=unit("str")),
            ),
            logical_type=unit("str"),
        )
    )
    return mutated.updated(
        bindings=[
            read_projection if item.id == binding.id else item
            for item in mutated.bindings
        ]
    )


def _document_with_concat(document: ProjectDocument, *, which: str) -> ProjectDocument:
    """Rebind ``site_binding.name`` to a ``concat`` of the site name and a constant."""
    site = document.bindings_by_id["site_binding"]
    name = next(item for item in site.properties if item.name == "name")
    literal = LiteralExpression(value="Site: ", logical_type=unit("str"))
    if which == "suffix":
        literal = literal.updated(value=" Site")
    arguments = (
        (literal, name.expression) if which == "prefix" else (name.expression, literal)
    )
    concat = OperationExpression(
        operator="concat", arguments=arguments, logical_type=unit("str")
    )
    properties = [
        PropertyBinding(name="name", expression=concat) if item.name == "name" else item
        for item in site.properties
    ]
    updated = site.updated(properties=properties)
    return document.updated(
        bindings=[updated if item.id == site.id else item for item in document.bindings]
    )


def _read(outcome: GenerationOutcome, relative: str) -> str:
    return (outcome.project_root / relative).read_text(encoding="utf-8")


def _manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / STATE_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))


def _files(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _stat(path: Path) -> tuple[int, int]:
    info = path.stat()
    return (info.st_size, info.st_mtime_ns)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ------------------------------------------------------- determinism and edge shapes


def test_rendering_does_not_depend_on_hash_seed(document: ProjectDocument) -> None:
    """Set iteration leaking into the output would show up here, not at review time."""
    tests = Path(__file__).parent
    script = (
        "import json, sys;"
        f"sys.path.insert(0, {str(tests)!r});"
        "from test_document import document as fixture;"
        "from studio_backend.generate import render_project;"
        "files = render_project(fixture._fixture_function());"
        "print(json.dumps([[f.path, f.content] for f in files]))"
    )
    digests = []
    for seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        digests.append(hashlib.sha256(result.stdout.encode()).hexdigest())
    assert len(set(digests)) == 1, "the rendering changed with the hash seed"


def test_an_empty_project_still_renders_a_valid_package(tmp_path: Path) -> None:
    """A brand-new workspace has nothing in it; the skeleton still has to be Python."""
    outcome = write_project(ProjectDocument(), tmp_path / "empty_project")
    assert set(outcome.owned_files) >= {"kg_project/__init__.py", "kg_project/build.py"}
    for relative in outcome.owned_files:
        cst.parse_module(_read(outcome, relative))


def test_a_struct_two_tables_read_is_declared_once(document: ProjectDocument) -> None:
    """A shared nested record is imported by the second table, not duplicated."""
    premises = document.structs_by_id["premises"]
    shared = DocNullable(
        value=DocStructType(
            module=f"{PACKAGE}.table.sites", qualname=premises.declaration_name
        )
    )
    column = DataField(name="premises", logical_type=shared)
    mutated = document.updated(
        tables=[
            item.updated(fields=[*item.fields, column])
            if item.id in {"sites", "equipment"}
            else item
            for item in document.tables
        ]
    )
    contents = {item.path: item.content for item in render_project(mutated)}
    assert contents["kg_project/table/sites/__init__.py"].count("class PremisesStruct") == 1
    equipment_file = contents["kg_project/table/equipment/__init__.py"]
    assert "class PremisesStruct" not in equipment_file
    assert "from kg_project.table.sites import PremisesStruct" in equipment_file


def test_navigation_above_an_operation_emits_struct_field(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """A ``pick`` whose parent is an operation is the case that records ``struct_field``."""
    areas = DocStruct(
        id="areas",
        declaration_name="AreasStruct",
        name="areas",
        fields=(DataField(name="area_code", logical_type=unit("str", nullable=True)),),
    )
    struct_type = DocStructType(module=f"{PACKAGE}.table.sites", qualname="AreasStruct")
    column_type = DocNullable(value=DocArray(item=DocNullable(value=struct_type)))
    column = FieldExpression(source="sites", path=("areas",), logical_type=column_type)
    expanded = OperationExpression(
        operator="expand",
        arguments=(column,),
        logical_type=DocNullable(value=struct_type),
    )
    picked = OperationExpression(
        operator="struct_field",
        arguments=(expanded,),
        parameters={"name": "area_code"},
        logical_type=unit("str", nullable=True),
    )
    projected = OperationExpression(
        operator="map_items",
        arguments=(column,),
        parameters={"name": "area_code"},
        logical_type=DocNullable(value=DocArray(item=DocNullable(value=unit("str")))),
    )
    sites = document.tables_by_id["sites"]
    projection = document.projections[0]
    mutated = document.updated(
        structs=[*document.structs, areas],
        tables=[
            sites.updated(fields=[*sites.fields, DataField(name="areas", logical_type=column_type)])
            if item.id == sites.id
            else item
            for item in document.tables
        ],
        projections=[
            projection.updated(
                fields=[
                    *projection.fields,
                    ProjectionField(name="area_code", expression=picked),
                    ProjectionField(name="all_codes", expression=projected),
                ]
            )
            if item.id == projection.id
            else item
            for item in document.projections
        ],
    )
    root = tmp_path / "navigation"
    outcome = write_project(mutated, root)
    assert "class AreasStruct(Struct):" in _read(outcome, "kg_project/table/sites/__init__.py")

    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module(f"{PACKAGE}.table.projections.site_cities")
        navigation = _ir(module.SiteCityProjection.__dict__["area_code"].expression)
        mapping = _ir(module.SiteCityProjection.__dict__["all_codes"].expression)
    finally:
        sys.path.remove(str(root))
        _forget_package()

    assert navigation["operator"] == "struct_field"
    assert navigation["arguments"][0]["operator"] == "expand"
    assert navigation["arguments"][0]["arguments"][0]["path"] == ["areas"]
    assert mapping["operator"] == "map_items"
    assert mapping["arguments"][0]["kind"] == "field"


def test_an_edge_binding_on_a_category_endpoint_supplies_the_token(
    document: ProjectDocument,
) -> None:
    """``endpoint(...)`` is written exactly when the document names one on a category."""
    binding = document.bindings_by_id["has_unit_binding"]
    tokenised = binding.updated(source="site", target="unit")
    mutated = document.updated(
        components=[
            item.updated(source="documented", target="documented")
            if item.id == "has_unit"
            else item
            for item in document.components
        ],
        bindings=[
            tokenised if item.id == binding.id else item for item in document.bindings
        ],
    )
    contents = {item.path: item.content for item in render_project(mutated)}
    # The edge now leaves a category, so it is filed under that category's package.
    edge = contents["kg_project/topology/documented/has_unit__documented.py"]
    assert (
        "class HasUnitEdge(MonitoredRelationAbstractEdge, "
        "Edge[DocumentedAbstractNode, DocumentedAbstractNode]):" in edge
    )
    binding_file = contents["kg_project/bindings/documented/has_unit__documented.py"]
    assert "source_node=endpoint(SiteNode)," in binding_file
    assert "target_node=endpoint(UnitNode)," in binding_file


def test_a_slot_description_is_written_under_the_slot(document: ProjectDocument) -> None:
    site = document.components_by_id["site"]
    described = site.updated(
        properties=[
            item.updated(description="City the premises is located in.")
            if item.name == "city"
            else item
            for item in site.properties
        ]
    )
    mutated = document.updated(
        components=[described if item.id == site.id else item for item in document.components]
    )
    rendered = _content(mutated, "kg_project/topology/site/__init__.py")
    assert (
        "city: PropertySlot[str] = property()\n"
        '    """City the premises is located in."""' in rendered
    )


def test_a_member_named_options_keeps_its_external_name(document: ProjectDocument) -> None:
    """``options_`` is the framework's escape hatch; the logical name survives it."""
    sites = document.tables_by_id["sites"]
    mutated = document.updated(
        tables=[
            sites.updated(fields=[*sites.fields, DataField(name="options", logical_type=unit("str"))])
            if item.id == sites.id
            else item
            for item in document.tables
        ]
    )
    assert "options_: Field[str] = field(name='options')" in _content(
        mutated, "kg_project/table/sites/__init__.py"
    )


def test_an_operator_with_the_wrong_arity_is_refused(document: ProjectDocument) -> None:
    """``expand`` takes exactly one argument; the planner asserts it, so refuse earlier."""
    binding = document.bindings_by_id["site_binding"]
    column = FieldExpression(
        source="sites", path=("site_id",), logical_type=unit("str", nullable=True)
    )
    broken = binding.updated(
        build_key=OperationExpression(
            operator="expand", arguments=(column, column), logical_type=unit("str")
        )
    )
    mutated = document.updated(
        bindings=[broken if item.id == binding.id else item for item in document.bindings]
    )
    with pytest.raises(GenerationError, match="expand"):
        render_project(mutated)


def test_an_unowned_stale_file_is_never_pruned(document: ProjectDocument, tmp_path: Path) -> None:
    """The manifest lists what studio wrote; anything else with that name stays."""
    root = tmp_path / ROOT_NAME
    outcome = write_project(document, root)
    (root / ".kg-studio/manifest.json").write_text(
        json.dumps(
            {
                **_manifest(root),
                "owned_files": sorted({*outcome.owned_files, "kg_project/keepme.py"}),
                "owned_file_hashes": {
                    **_manifest(root)["owned_file_hashes"],
                    "kg_project/keepme.py": "sha256:absent",
                },
            }
        ),
        encoding="utf-8",
    )
    stranger = root / "kg_project/keepme.py"
    stranger.write_text("# not studio's\n", encoding="utf-8")

    with pytest.raises(OwnershipError, match="keepme.py"):
        write_project(document, root)
    assert stranger.read_text(encoding="utf-8") == "# not studio's\n"


# ------------------------------------------------------------- strict pyright tier


def _pyright_command() -> list[str]:
    """The ``pyright`` CLI next to the server the diagnostics service discovers.

    Skipped rather than failed when pyright is not installed, mirroring
    ``tests/test_lsp_live.py``: a missing dev dependency is not a regression.
    """
    from studio_backend.diagnostics.service import (
        DiagnosticsError,
        discover_framework_venv,
        discover_server_command,
    )

    try:
        venv = discover_framework_venv()
        server = discover_server_command(venv)
    except DiagnosticsError as error:
        pytest.skip(str(error))
    cli = Path(server[0]).with_name("pyright")
    if cli.is_file():
        return [str(cli)]
    found = shutil.which("pyright")
    if found is None:
        pytest.skip("pyright-langserver was found but not the pyright CLI")
    return [found]


def test_the_generated_project_is_clean_under_strict_pyright(
    document: ProjectDocument, tmp_path: Path
) -> None:
    """Bug 1 end to end: the studio's own check reports zero errors on a generated project.

    The run mirrors what the studio does — ``typeCheckingMode: basic`` plus
    ``strict: [<package>]``, the config written by :func:`write_pyright_config`
    itself, so the check cannot drift from what the studio runs. The projection's
    defaulted key is read by a binding through a calculation, the exact
    ``studio_test_project`` shape where the trailing ``.expression`` inside
    ``projection_field`` reported ``ProjectionField[Unknown]`` and cascaded five
    more errors through the binding that reads the projection.
    """
    from studio_backend.diagnostics.service import DiagnosticsError, write_pyright_config

    mutated = _document_with_projection_reading_binding(document)
    root = tmp_path / "strict_project"
    write_project(mutated, root)
    try:
        config = write_pyright_config(root, PACKAGE)
    except DiagnosticsError as error:
        pytest.skip(str(error))

    result = subprocess.run(
        [*_pyright_command(), "-p", str(config)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "0 errors" in result.stdout
