"""Fixtures for the inference and index tests, built on the canonical sample document.

The suite's ``conftest.py`` re-exports ``tests/test_document.py``'s monitored-estate
document, and that document is the base here: ``estate`` extends it rather than
restating it. It adds the handful of shapes the acceptance document had no reason to
carry — a non-null column beside all those nullable ones, a non-null member inside a
nullable struct, a projection output whose declared type is deliberately wrong — because
those are precisely the cases where nullability propagation and derived types show up.

``probe_project`` declares a second, real KG project through ``kg_build_system``'s
authoring API so inference can be measured against the framework rather than against
this suite's reading of it. A struct logical type resolves through ``importlib`` to an
importable top-level class (``expressions/selections.py``, ``_declaration``;
``types/normalization.py`` refuses a ``<locals>`` class), which is why the probe is
written to disk and imported instead of being declared inline.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from studio_backend.ir.document import (
    DataField,
    Expression,
    FieldExpression,
    LogicalType,
    OperationExpression,
    ProjectDocument,
    Projection,
    ProjectionField,
    Struct,
    StructType,
    Table,
    unit,
)

PROBE_MODULE = "studio_probe_authoring"

#: The probe's declarations. The names are load bearing: ``Table._table_name`` and a
#: struct's ``(module, qualname)`` identity come from them, and ``probe_document``
#: mirrors exactly what they compile to.
PROBE_SOURCE = '''"""Written by the studio test suite: a real KG project to compare inference with."""

from __future__ import annotations

from kg_build_system import Array, Field, Struct, Table, field


class InnerStruct(Struct):
    note: Field[str] = field()
    count: Field[int] = field()


class AreaStruct(Struct):
    area_code: Field[str | None] = field()
    depth: Field[float] = field()


class TagStruct(Struct):
    label: Field[str] = field()


class WidgetTable(Table):
    code: Field[str] = field()
    name: Field[str | None] = field()
    count: Field[int] = field()
    priority: Field[int | None] = field()
    amount: Field[float] = field()
    flag: Field[bool] = field()
    when: Field[str | None] = field()
    maybe_inner: Field[InnerStruct | None] = field()
    inner: Field[InnerStruct] = field()
    areas: Field[Array[AreaStruct | None] | None] = field()
    tags: Field[Array[TagStruct]] = field()
    strings: Field[Array[str]] = field()
    maybe_strings: Field[Array[str | None]] = field()
    maybe_string_array: Field[Array[str] | None] = field()
'''


@pytest.fixture
def estate(document: ProjectDocument) -> ProjectDocument:
    """The canonical document plus the shapes inference and the palette are tested on."""
    sites = document.tables_by_id["sites"]
    sites = sites.updated(
        fields=(
            *sites.fields,
            DataField(name="capacity", logical_type=unit("int")),
            DataField(name="score", logical_type=unit("float")),
            DataField(name="active", logical_type=unit("bool")),
        )
    )
    equipment = document.tables_by_id["equipment"]
    equipment = equipment.updated(
        fields=(
            *equipment.fields,
            # The register's own code is never missing, which makes it the one non-null
            # text column the text and Boolean families can be exercised on.
            DataField(name="code", logical_type=unit("str")),
            DataField(name="installed_on", logical_type=unit("date")),
        )
    )
    premises = document.structs_by_id["premises"]
    premises = premises.updated(
        fields=(*premises.fields, DataField(name="registered", logical_type=unit("date")))
    )
    projections = tuple(
        _extend_projection(item) if item.id == "site_cities" else item
        for item in document.projections
    )
    return document.updated(
        tables=(sites, equipment, *(item for item in document.tables if item.id not in {"sites", "equipment"})),
        structs=(premises, *(item for item in document.structs if item.id != "premises")),
        projections=projections,
    )


def _extend_projection(projection: Projection) -> Projection:
    """Add an output whose declared type is wrong, to prove types are derived."""
    site_id = FieldExpression(
        source="sites", path=("site_id",), logical_type=unit("str", nullable=True)
    )
    present = OperationExpression(  # type: ignore[call-arg]
        operator="where_present",
        arguments=(site_id,),
        logical_type=unit("str", nullable=True),  # stale on purpose
    )
    return projection.updated(
        fields=(*projection.fields, ProjectionField(name="present_id", expression=present))
    )


TOPOLOGY_MODULE = "studio_probe_topology"

#: A concrete component with two mixins and a category parent, declared the way the
#: generator declares one: templates first, then the parent, then the concrete base.
#: ``tests/test_index.py`` compares the framework's own inheritance answer with the
#: index's, so the ordering rules in ``index.resolved_properties`` are measured against
#: ``cls.__mro__`` and the generated dataclass rather than against a reading of them.
TOPOLOGY_SOURCE = '''"""Written by the studio test suite: component inheritance to compare against."""

from __future__ import annotations

import dataclasses

from kg_build_system import (
    AbstractNode, Node, NodeOptions, NodeTemplate, PropertySlot, property,
)


class FirstTemplate(NodeTemplate):
    alpha: PropertySlot[str] = property()


class SecondTemplate(NodeTemplate):
    beta: PropertySlot[str] = property()


class SharedTemplate(NodeTemplate):
    stamp: PropertySlot[str] = property()


class LeftTemplate(SharedTemplate):
    left_slot: PropertySlot[str] = property()


class RightTemplate(SharedTemplate):
    right_slot: PropertySlot[str] = property()


class BaseAbstractNode(AbstractNode):
    shared_slot: PropertySlot[str] = property()


class PairNode(FirstTemplate, SecondTemplate, BaseAbstractNode, Node):
    """A leaf with two unrelated templates and a category parent."""

    options = NodeOptions(name="pair")
    own: PropertySlot[str] = property()


class LeafNode(LeftTemplate, RightTemplate, BaseAbstractNode, Node):
    """A leaf, mixing two templates that share one template."""

    options = NodeOptions(name="leaf")
    own: PropertySlot[str] = property()


def attribute_order(declaration: type) -> list[str]:
    """The generated record's field order: the leaf's own slots first."""
    return [item.name for item in dataclasses.fields(declaration)]


def composition_order(declaration: type) -> list[str]:
    """``properties_for`` order: ``reversed(cls.__mro__)``, nearest ancestor shadowing."""
    return list(declaration._properties)
'''


@pytest.fixture
def probe_topology(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import the topology probe so its real MRO can be compared with ours."""
    path = tmp_path / f"{TOPOLOGY_MODULE}.py"
    path.write_text(TOPOLOGY_SOURCE, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(TOPOLOGY_MODULE, None)
    module = importlib.import_module(TOPOLOGY_MODULE)
    try:
        yield module
    finally:
        sys.modules.pop(TOPOLOGY_MODULE, None)


@dataclass(frozen=True, slots=True)
class ProbeProject:
    """One real KG project, and the Studio document that describes it."""

    module: ModuleType
    document: ProjectDocument

    @property
    def table(self) -> type:
        """``WidgetTable``, ready to author against."""
        return self.module.WidgetTable


def probe_document() -> ProjectDocument:
    """The Studio document for ``PROBE_SOURCE``.

    A struct reference names the module the probe is imported from and the class the
    framework resolves to, because ``(module, qualname)`` is what a ``StructType``
    records. Generated code would live in ``<package>.table.widget``; identity is what
    has to line up for the two IRs to be comparable, not the package name.
    """

    def field(name: str, value: LogicalType) -> DataField:
        return DataField(name=name, logical_type=value)

    def reference(name: str) -> StructType:
        return StructType(module=PROBE_MODULE, qualname=name)

    inner = Struct(
        id="inner",
        declaration_name="InnerStruct",
        name="inner",
        fields=(field("note", unit("str")), field("count", unit("int"))),
    )
    area = Struct(
        id="area",
        declaration_name="AreaStruct",
        name="area",
        fields=(field("area_code", unit("str", nullable=True)), field("depth", unit("float"))),
    )
    tag = Struct(
        id="tag", declaration_name="TagStruct", name="tag", fields=(field("label", unit("str")),)
    )
    widget = Table(
        id="widget",
        declaration_name="WidgetTable",
        name="widget",
        fields=(
            field("code", unit("str")),
            field("name", unit("str", nullable=True)),
            field("count", unit("int")),
            field("priority", unit("int", nullable=True)),
            field("amount", unit("float")),
            field("flag", unit("bool")),
            field("when", unit("str", nullable=True)),
            field("maybe_inner", _nullable(reference("InnerStruct"))),
            field("inner", reference("InnerStruct")),
            field("areas", _nullable(_array(_nullable(reference("AreaStruct"))))),
            field("tags", _array(reference("TagStruct"))),
            field("strings", _array(unit("str"))),
            field("maybe_strings", _array(unit("str", nullable=True))),
            field("maybe_string_array", _nullable(_array(unit("str")))),
        ),
    )
    return ProjectDocument(
        project=ProjectDocument().project.updated(name="Probe", package="probe_project"),
        structs=(inner, area, tag),
        tables=(widget,),
    )


def _array(item: LogicalType) -> LogicalType:
    from studio_backend.ir.document import array

    return array(item)  # type: ignore[return-value]


def _nullable(value: LogicalType) -> LogicalType:
    from studio_backend.ir.document import nullable

    return nullable(value)  # type: ignore[arg-type]


@pytest.fixture
def probe_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProbeProject:
    """Import the probe declarations and hand back the framework/Studio pair."""
    path = tmp_path / f"{PROBE_MODULE}.py"
    path.write_text(PROBE_SOURCE, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(PROBE_MODULE, None)
    module = importlib.import_module(PROBE_MODULE)
    try:
        yield ProbeProject(module=module, document=probe_document())
    finally:
        sys.modules.pop(PROBE_MODULE, None)


def expression_of(node: dict[str, object]) -> Expression:
    """A framework IR dict as a document expression model."""
    from pydantic import TypeAdapter

    return TypeAdapter(Expression).validate_python(node)  # type: ignore[no-any-return, return-value]
