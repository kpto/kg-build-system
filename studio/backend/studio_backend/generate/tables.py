"""Data contracts: one generated package per table, structs beside their table.

The rendering follows ``reference_project/table/`` file for file — the framework's
generated-file header, ``TableOptions(name=…)``, unified ``Field[T]`` members — with
one deliberate difference: a description is written as the documentation string
directly below the member rather than as a ``description=`` argument, because that
is the convention the framework's hand-written contracts use and it keeps a long
description out of the declaration line.

The framework turns those strings into descriptions again on the way in:
``Field.__set_name__`` and ``_PropertyDeclaration.__set_name__`` read the literal
below the assignment, which is why ``description=`` would be a second, louder way
of saying the same thing.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..ir.document import (
    ArrayType,
    DataField,
    NullableType,
    ProjectDocument,
    Struct,
    StructType,
    Table,
)
from .annotations import annotation_tuple_text
from .layout import Layout, ModuleLocation
from .render import (
    AnchorHint,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    annotation_text,
    attribute_docstring_lines,
    declaration_name,
    docstring_lines,
    generated_file,
    member_name,
    string_literal,
)

STRUCT_SUFFIXES = ("Struct", "Table", "TableGroup")


def render_tables(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """Every table package, group module and shared-struct module of the project."""
    paths = sorted({*layout.table_members, *layout.struct_members})
    return [
        _render_module(
            document,
            layout,
            path=path,
            location=_location_for(layout, path),
            table_ids=tuple(layout.table_members.get(path, ())),
            struct_ids=tuple(layout.struct_members.get(path, ())),
        )
        for path in paths
    ]


def _location_for(layout: Layout, path: str) -> ModuleLocation:
    for table in layout.tables.values():
        if table.path == path:
            return table.location
    for struct in layout.structs.values():
        if struct.path == path:
            return struct.location
    raise GenerationError(f"no declaration maps to {path}")


def _render_module(
    document: ProjectDocument,
    layout: Layout,
    *,
    path: str,
    location: ModuleLocation,
    table_ids: tuple[str, ...],
    struct_ids: tuple[str, ...],
) -> RenderedFile:
    imports = Imports(layout.package, location.module)
    body = Lines()
    anchors: list[AnchorHint] = []

    structs = _ordered_structs(document, struct_ids)
    for struct in structs:
        lines, member_anchors = _render_struct(document, layout, struct, location, imports)
        body.extend(lines)
        body.blank()
        anchors.extend(member_anchors)
    for table_id in table_ids:
        table = document.tables_by_id[table_id]
        lines, member_anchors = _render_table(document, layout, table, imports)
        body.extend(lines)
        body.blank()
        anchors.extend(member_anchors)

    products = [document.tables_by_id[item].declaration_name for item in table_ids]
    exports = products or [struct.declaration_name for struct in structs]
    if exports:
        body.blank()
        body.add(f"__all__ = {exports!r}")

    # The declaration the file exists for comes first: it is the ref everything
    # unmapped in the file falls back to.
    refs = [
        *(f"table:{table_id}" for table_id in table_ids),
        *(f"struct:{struct.id}" for struct in structs),
    ]
    return generated_file(
        path=path,
        module=location.module,
        docstring=None,
        imports=imports,
        body=body,
        owner_refs=refs,
        anchors=anchors,
        directives=True,
    )


# ------------------------------------------------------------------- declarations


def _ordered_structs(document: ProjectDocument, struct_ids: tuple[str, ...]) -> tuple[Struct, ...]:
    """Member structs before the structs that contain them.

    A field annotation names the class plainly, so the class has to exist by the
    time the class body runs. The document may list a container before its
    members, which is why the order is resolved here rather than trusted; ties
    keep the document's own order, which is what makes the output stable.
    """
    pending = [document.structs_by_id[item] for item in struct_ids]
    by_name = {struct.declaration_name: struct for struct in pending}
    ordered: list[Struct] = []
    visiting: list[str] = []

    def visit(struct: Struct) -> None:
        if any(item.id == struct.id for item in ordered):
            return
        if struct.id in visiting:
            trail = " -> ".join((*visiting, struct.id))
            raise GenerationError(
                f"struct containment cycles at {trail}; a nested record cannot "
                "contain itself, so no annotation can name it"
            )
        visiting.append(struct.id)
        for member in struct.fields:
            for reference in _struct_references(member.logical_type):
                nested = by_name.get(reference.qualname)
                if nested is not None:
                    visit(nested)
        visiting.pop()
        ordered.append(struct)

    for struct in pending:
        visit(struct)
    return tuple(ordered)


def _render_struct(
    document: ProjectDocument,
    layout: Layout,
    struct: Struct,
    location: ModuleLocation,
    imports: Imports,
) -> tuple[list[str], list[AnchorHint]]:
    imports.add_framework("Field", "Struct", "field")
    body = Lines()
    body.add(f"class {struct.declaration_name}(Struct):")
    if struct.description:
        body.extend(docstring_lines(struct.description, level=1))
        body.blank()
    if declaration_name(struct.declaration_name, suffixes=STRUCT_SUFFIXES) != struct.name:
        imports.add_framework("StructOptions")
        body.add(f"options = StructOptions(name={string_literal(struct.name)})", level=1)
        body.blank()
    body.extend(_member_lines(document, layout, struct.fields, location.module, imports))
    body.blank()

    anchors = [AnchorHint("class", f"struct:{struct.id}", struct.declaration_name)]
    anchors.extend(
        AnchorHint(
            "member",
            f"struct:{struct.id}.field.{member.name}",
            f"{struct.declaration_name}.{member_name(member.name)}",
        )
        for member in struct.fields
    )
    return body.items, anchors


def _render_table(
    document: ProjectDocument,
    layout: Layout,
    table: Table,
    imports: Imports,
) -> tuple[list[str], list[AnchorHint]]:
    body = Lines()
    if layout.is_group(table.id):
        imports.add_framework("TableGroup", "TableGroupOptions")
        body.add(f"class {table.declaration_name}(TableGroup):")
        if table.description:
            body.extend(docstring_lines(table.description, level=1))
            body.blank()
        body.add(f"options = TableGroupOptions(name={string_literal(table.name)})", level=1)
        body.blank()
        body.extend(_group_member_lines(document, layout, table, imports))
    else:
        imports.add_framework("Field", "Table", "TableOptions", "field")
        body.add(f"class {table.declaration_name}(Table):")
        if table.description:
            body.extend(docstring_lines(table.description, level=1))
            body.blank()
        body.add(f"options = TableOptions(name={string_literal(table.name)})", level=1)
        body.blank()
        body.extend(
            _member_lines(
                document, layout, table.fields, layout.table(table.id).module, imports
            )
        )
    body.blank()

    anchors = [AnchorHint("class", f"table:{table.id}", table.declaration_name)]
    anchors.extend(
        AnchorHint(
            "member",
            f"table:{table.id}.field.{member.name}",
            f"{table.declaration_name}.{member_name(member.name)}",
        )
        for member in table.fields
    )
    return body.items, anchors


def _group_member_lines(
    document: ProjectDocument, layout: Layout, table: Table, imports: Imports
) -> Lines:
    """``python_name = MemberTable``, one line per catalogue entry."""
    body = Lines()
    members = layout.members_of(table.id)
    if not members:
        raise GenerationError(f"table group {table.id!r} declares no members")
    for member in members:
        member_table = document.tables_by_id.get(member.table_id)
        if member_table is None:
            raise GenerationError(
                f"table group {table.id!r} names member {member.table_id!r}, "
                "which is not declared"
            )
        attribute = member.attribute
        if not attribute.isidentifier() or attribute == "options":
            raise GenerationError(
                f"table group member {attribute!r} of {table.id!r} is not a usable "
                "Python attribute name"
            )
        imports.add(layout.table(member.table_id).module, member_table.declaration_name)
        body.add(f"{attribute} = {member_table.declaration_name}", level=1)
    return body


def _member_lines(
    document: ProjectDocument,
    layout: Layout,
    fields: Sequence[DataField],
    current_module: str,
    imports: Imports,
) -> Lines:
    """``name: Field[T] = field(name='…')``, its description written underneath."""
    body = Lines()
    for member in fields:
        if len(body):
            body.blank()
        annotation = annotation_text(member.logical_type, imports, current_module=current_module)
        arguments = [f"name={string_literal(member.name)}"]
        annotations = annotation_tuple_text(document, layout, member.annotations, imports)
        if annotations:
            arguments.append(f"annotations={annotations}")
        body.add(
            f"{member_name(member.name)}: Field[{annotation}] = field({', '.join(arguments)})",
            level=1,
        )
        body.extend(attribute_docstring_lines(member.description or ""))
    return body


def _struct_references(value) -> list[StructType]:
    if isinstance(value, NullableType):
        return _struct_references(value.value)
    if isinstance(value, ArrayType):
        return _struct_references(value.item)
    return [value] if isinstance(value, StructType) else []
