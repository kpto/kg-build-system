"""Where every declaration lands in the generated project.

The layout is the framework's node-first convention (``KG_BUILD_SYSTEM_SPEC.md``
§14), which is what makes a generated project indistinguishable in shape from
``reference_project``:

============================================= ===================================
path                                          contents
============================================= ===================================
``<pkg>/table/<table>/__init__.py``           one data contract package per table
``<pkg>/table/<group>/<member>.py``           a member table of a table group
``<pkg>/table/structs.py``                    structs no table reads (yet)
``<pkg>/table/projections/<id>.py``           projections
``<pkg>/topology/common.py``                  templates and categories
``<pkg>/topology/<node>/__init__.py``         a concrete node component
``<pkg>/topology/<node>/<pred>__<dest>.py``   an edge, filed under its source
``<pkg>/bindings/<node>/…``                   bindings, mirroring ``topology/``
``<pkg>/annotations.py``                      project-owned annotation types
``<pkg>/sources.py``                          one ``bind_source`` per source
``<pkg>/build.py``                            the composition entry point
============================================= ===================================

Every path is derived from the document, so the same document always yields the
same file map, and a rename moves exactly one file.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ir.document import ArrayType, Component, ProjectDocument, Struct, Table, unwrap_nullable
from ..ir.document import NullableType, StructType
from .render import GenerationError, python_name

TABLE_PACKAGE = "table"
PROJECTION_PACKAGE = "projections"
TOPOLOGY_PACKAGE = "topology"
BINDINGS_PACKAGE = "bindings"
SHARED_STRUCTS_FILE = "structs.py"


@dataclass(frozen=True)
class ModuleLocation:
    """One generated Python module: its project-relative parts, path and name."""

    parts: tuple[str, ...]

    @property
    def path(self) -> str:
        return "/".join(self.parts)

    @property
    def module(self) -> str:
        parts = list(self.parts)
        if parts and parts[-1] in ("__init__.py", "__init__"):
            parts.pop()
        return ".".join(part.removesuffix(".py") for part in parts)

    @property
    def is_package(self) -> bool:
        return self.parts[-1] == "__init__"

    def under(self, *segments: str) -> "ModuleLocation":
        """The same directory, holding ``segments`` instead of the last part."""
        return ModuleLocation((*self.parts[:-1], *segments))

    def mirrored(self, replace_first: str, with_first: str) -> "ModuleLocation":
        """This location with its top-level directory renamed."""
        if len(self.parts) < 2 or self.parts[1] != replace_first:
            raise GenerationError(f"{self.path} is not under {replace_first}/")
        return ModuleLocation((self.parts[0], with_first, *self.parts[2:]))


def _location(package: str, *parts: str) -> ModuleLocation:
    return ModuleLocation((package, *parts))


@dataclass(frozen=True)
class TableLocation:
    table: Table
    #: The catalogue path segments: the group chain plus this table's own name.
    segments: tuple[str, ...]
    location: ModuleLocation

    @property
    def path(self) -> str:
        return self.location.path

    @property
    def module(self) -> str:
        return self.location.module

    @property
    def catalog_path(self) -> str:
        """The group-qualified logical name an expression may address it by."""
        return "/".join(self.segments)


@dataclass(frozen=True)
class StructLocation:
    struct: Struct
    location: ModuleLocation

    @property
    def path(self) -> str:
        return self.location.path

    @property
    def module(self) -> str:
        return self.location.module

    @property
    def key(self) -> tuple[str, str]:
        """The identity a ``StructType`` reference addresses it by."""
        return (self.module, self.struct.declaration_name)


@dataclass(frozen=True)
class ComponentLocation:
    component: Component
    location: ModuleLocation


@dataclass(frozen=True)
class SourceEntry:
    """One logical source an expression may read: a concrete table or projection."""

    ref: str
    #: Every name an expression's ``source`` may use for it.
    names: tuple[str, ...]
    class_name: str
    module: str


@dataclass(frozen=True)
class GroupMember:
    """One entry of a table group's catalogue, as it will be declared."""

    attribute: str
    table_id: str


class Layout:
    """The whole file map of one document, resolved before anything renders."""

    def __init__(self, document: ProjectDocument) -> None:
        self.document = document
        self.package = python_name(document.project.package)
        self.data_directory = document.project.data_directory
        self.tables: dict[str, TableLocation] = {}
        self.table_members: dict[str, list[str]] = {}
        self.catalogue: dict[str, tuple[GroupMember, ...]] = {}
        self.groups: set[str] = set()
        self.structs: dict[str, StructLocation] = {}
        self.struct_members: dict[str, list[str]] = {}
        self.struct_keys: dict[tuple[str, str], StructLocation] = {}
        self.projections: dict[str, ModuleLocation] = {}
        self.components: dict[str, ComponentLocation] = {}
        self.component_members: dict[str, list[str]] = {}
        self.bindings: dict[str, ModuleLocation] = {}
        self.binding_members: dict[str, list[str]] = {}
        self._build()

    # -- construction ------------------------------------------------------

    def _build(self) -> None:
        self._resolve_catalogues()
        self._place_tables()
        self._place_projections()
        self._place_structs()
        self._place_components()
        self._place_bindings()
        self._check_import_cycles()

    def _resolve_catalogues(self) -> None:
        """Which tables are groups, and what each group holds.

        ``Table.members`` is not evidence on its own: the document's ``updated()``
        copies a group's members onto every table derived from it, so a leaf table
        can arrive holding its own parent's catalogue. ``Table.group`` is the
        authoritative parentage, so a table is a group exactly when other tables
        name it, and a member entry naming a table that belongs to a different
        group is stale and ignored.
        """
        by_id = self.document.tables_by_id
        children: dict[str, list[str]] = {}
        for table in self.document.tables:
            if table.group is None:
                continue
            if table.group not in by_id:
                raise GenerationError(
                    f"table {table.id!r} names group {table.group!r}, which is not declared"
                )
            children.setdefault(table.group, []).append(table.id)
        self.groups = set(children)

        for group_id, child_ids in children.items():
            group = by_id[group_id]
            if group.fields and not child_ids:
                raise GenerationError(f"table {group.id!r} declares fields and members")
            listed: list[GroupMember] = []
            remaining = dict.fromkeys(child_ids)
            for member in group.members:
                if member.ref not in remaining:
                    continue
                listed.append(GroupMember(attribute=member.python_name, table_id=member.ref))
                remaining.pop(member.ref)
            for child_id in remaining:
                listed.append(
                    GroupMember(
                        attribute=python_name(by_id[child_id].name), table_id=child_id
                    )
                )
            self.catalogue[group_id] = tuple(listed)

    def is_group(self, table_id: str) -> bool:
        return table_id in self.groups

    def members_of(self, group_id: str) -> tuple[GroupMember, ...]:
        return self.catalogue.get(group_id, ())

    def _place_tables(self) -> None:
        by_id = self.document.tables_by_id
        for table in self.document.tables:
            segments = [python_name(table.name)]
            group_id = table.group
            seen: set[str] = {table.id}
            while group_id is not None:
                if group_id in seen:
                    raise GenerationError(
                        f"table group chain for {table.id!r} cycles at {group_id!r}"
                    )
                seen.add(group_id)
                parent = by_id[group_id]
                segments.insert(0, python_name(parent.name))
                group_id = parent.group
            placed = tuple(segments)
            if self.is_group(table.id) or table.group is None:
                location = _location(
                    self.package, TABLE_PACKAGE, *placed, "__init__.py"
                )
            else:
                location = _location(
                    self.package,
                    TABLE_PACKAGE,
                    *placed[:-1],
                    f"{placed[-1]}.py",
                )
            self.tables[table.id] = TableLocation(
                table=table, segments=placed, location=location
            )
            self.table_members.setdefault(location.path, []).append(table.id)

    def _place_structs(self) -> None:
        """Give every struct the module that reads it, as the framework's own does.

        A nested record is declared beside the table that uses it, so a field
        annotation is a plain class name. The first reference in document order
        claims a struct, and a struct read from two packages is imported by the
        second rather than duplicated. Structs no field reads yet — the ones still
        being authored — are collected in one module instead of being dropped.
        """
        known = self._known_modules()
        homes: dict[str, ModuleLocation] = {}

        def claim(qualname: str, declared: str, fallback: ModuleLocation) -> None:
            preferred = known.get(declared, fallback)
            for struct in self.document.structs:
                if struct.declaration_name != qualname or struct.id in homes:
                    continue
                homes[struct.id] = preferred
                return

        for table in self.document.tables:
            location = self.tables[table.id].location
            for member in table.fields:
                for reference in _struct_references(member.logical_type):
                    claim(reference.qualname, reference.module, location)

        # Nested references follow their owner, which the document may list in
        # either order, so propagate until nothing moves.
        for _ in range(len(self.document.structs) + 1):
            before = dict(homes)
            for struct in self.document.structs:
                owner = homes.get(struct.id)
                if owner is None:
                    continue
                for member in struct.fields:
                    for reference in _struct_references(member.logical_type):
                        claim(reference.qualname, reference.module, owner)
            if homes == before:
                break

        shared = _location(self.package, TABLE_PACKAGE, SHARED_STRUCTS_FILE)
        for struct in self.document.structs:
            placed = StructLocation(struct=struct, location=homes.get(struct.id, shared))
            self.structs[struct.id] = placed
            self.struct_members.setdefault(placed.path, []).append(struct.id)
            if placed.key in self.struct_keys:
                raise GenerationError(
                    f"struct {placed.struct.declaration_name!r} is declared twice "
                    f"in {placed.module}"
                )
            self.struct_keys[placed.key] = placed

    def _known_modules(self) -> dict[str, ModuleLocation]:
        """Every generated module that can already hold a declaration."""
        known = {location.module: location.location for location in self.tables.values()}
        known.update({location.module: location for location in self.projections.values()})
        return known

    def _place_projections(self) -> None:
        for projection in self.document.projections:
            self.projections[projection.id] = _location(
                self.package,
                TABLE_PACKAGE,
                PROJECTION_PACKAGE,
                f"{python_name(projection.id)}.py",
            )

    def _place_components(self) -> None:
        for component in self.document.components:
            if component.tier != "concrete":
                # Templates and categories are shared across node packages.
                location = _location(self.package, TOPOLOGY_PACKAGE, "common.py")
            elif component.kind == "node":
                location = _location(
                    self.package,
                    TOPOLOGY_PACKAGE,
                    python_name(component.name),
                    "__init__.py",
                )
            else:
                location = _location(
                    self.package,
                    TOPOLOGY_PACKAGE,
                    self._endpoint_namespace(component.source),
                    (
                        f"{python_name(component.name)}__"
                        f"{self._endpoint_namespace(component.target)}.py"
                    ),
                )
            self.components[component.id] = ComponentLocation(
                component=component, location=location
            )
            self.component_members.setdefault(location.path, []).append(component.id)

    def _endpoint_namespace(self, component_id: str | None) -> str:
        """The node package an endpoint is filed under, category or concrete."""
        if component_id is None:
            raise GenerationError("an edge component must name both endpoints")
        endpoint = self.document.components_by_id.get(component_id)
        if endpoint is None:
            raise GenerationError(f"unknown endpoint component {component_id!r}")
        if endpoint.kind != "node":
            raise GenerationError(f"endpoint {component_id!r} is not a node component")
        return python_name(endpoint.name)

    def _place_bindings(self) -> None:
        """One module per component module, so ``bindings/`` mirrors ``topology/``."""
        for binding in self.document.bindings:
            location = self.components.get(binding.component)
            if location is None:
                raise GenerationError(
                    f"binding {binding.id!r} targets unknown component {binding.component!r}"
                )
            component = location.component
            if component.tier != "concrete":
                # Nothing bindable, but the file has to exist so the framework's
                # own rejection is reported against this binding rather than lost.
                target = _location(
                    self.package, BINDINGS_PACKAGE, f"{python_name(component.name)}.py"
                )
            elif component.kind == "node":
                target = location.location.mirrored(
                    TOPOLOGY_PACKAGE, BINDINGS_PACKAGE
                ).under("__init__.py")
            else:
                target = location.location.mirrored(TOPOLOGY_PACKAGE, BINDINGS_PACKAGE)
            self.bindings[binding.id] = target
            self.binding_members.setdefault(target.path, []).append(binding.id)

    def _check_import_cycles(self) -> None:
        """Cross-package struct sharing can close an import cycle; refuse it early.

        The framework resolves a struct annotation when its class body runs, so a
        cycle between two generated modules is a ``NameError`` at import time —
        far better reported as one generation error naming both paths.
        """
        edges: dict[str, set[str]] = {}

        def depend(path: str, logical_type) -> None:
            for reference in _struct_references(logical_type):
                holder = self.struct_holder(reference)
                if holder is not None and holder.path != path:
                    edges.setdefault(path, set()).add(holder.path)

        for table in self.document.tables:
            for member in table.fields:
                depend(self.tables[table.id].path, member.logical_type)
        for struct in self.document.structs:
            for member in struct.fields:
                depend(self.structs[struct.id].path, member.logical_type)

        state: dict[str, str] = {}

        def visit(node: str, trail: tuple[str, ...]) -> None:
            if state.get(node) == "done":
                return
            if state.get(node) == "open":
                raise GenerationError(
                    "generated imports would cycle: "
                    + " -> ".join((*trail, node))
                    + "; a struct shared by two table packages must not reach back "
                    "into the other"
                )
            state[node] = "open"
            for target in sorted(edges.get(node, ())):
                visit(target, (*trail, node))
            state[node] = "done"

        for node in sorted(edges):
            visit(node, ())

    # -- queries -----------------------------------------------------------

    def struct_holder(self, reference: StructType) -> StructLocation | None:
        """Where a struct reference resolves, by module then by declaration name."""
        located = self.struct_keys.get((reference.module, reference.qualname))
        if located is not None:
            return located
        for location in self.structs.values():
            if location.struct.declaration_name == reference.qualname:
                return location
        return None

    def table(self, table_id: str) -> TableLocation:
        try:
            return self.tables[table_id]
        except KeyError:
            raise GenerationError(f"unknown table {table_id!r}") from None

    def struct(self, struct_id: str) -> StructLocation:
        try:
            return self.structs[struct_id]
        except KeyError:
            raise GenerationError(f"unknown struct {struct_id!r}") from None

    def struct_for(self, reference: StructType) -> StructLocation:
        location = self.struct_holder(reference)
        if location is None:
            raise GenerationError(
                f"struct {reference.qualname!r} in {reference.module!r} is not declared"
            )
        return location

    def component(self, component_id: str) -> ComponentLocation:
        try:
            return self.components[component_id]
        except KeyError:
            raise GenerationError(f"unknown component {component_id!r}") from None

    def projection(self, projection_id: str) -> ModuleLocation:
        try:
            return self.projections[projection_id]
        except KeyError:
            raise GenerationError(f"unknown projection {projection_id!r}") from None

    def binding(self, binding_id: str) -> ModuleLocation:
        try:
            return self.bindings[binding_id]
        except KeyError:
            raise GenerationError(f"unknown binding {binding_id!r}") from None

    def sources(self) -> tuple[SourceEntry, ...]:
        """Every logical source an expression may read, by every name it answers to."""
        entries: list[SourceEntry] = []
        for table in self.document.tables:
            if self.is_group(table.id):
                continue
            location = self.tables[table.id]
            entries.append(
                SourceEntry(
                    ref=f"table:{table.id}",
                    names=(table.name, location.catalog_path),
                    class_name=table.declaration_name,
                    module=location.module,
                )
            )
        for projection in self.document.projections:
            location = self.projections[projection.id]
            entries.append(
                SourceEntry(
                    ref=f"projection:{projection.id}",
                    names=(projection.name, location.parts[-1].removesuffix(".py")),
                    class_name=projection.declaration_name,
                    module=location.module,
                )
            )
        return tuple(entries)

def _struct_references(value: object) -> list[StructType]:
    """Every struct a logical type names, through nullable wrappers and arrays.

    An ``Array[Areas | None] | None`` declares ``Areas`` just as surely as a plain
    struct field does, so the search goes all the way down.
    """
    if isinstance(value, NullableType):
        return _struct_references(value.value)
    if isinstance(value, ArrayType):
        return _struct_references(value.item)
    base = unwrap_nullable(value)
    return [base] if isinstance(base, StructType) else []
