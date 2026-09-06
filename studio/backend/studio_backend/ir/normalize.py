"""Backend-owned repair of derived fields in a candidate document.

A client may send an expression without ``logical_type`` values, with a stale one,
or with a struct reference whose declaring module moved. None of those are meanings
the client owns. The backend recomputes them here so the document on disk is exactly
what the generator will render and the framework will compile.
"""

from __future__ import annotations

from typing import Any

from .document import (
    ArrayType,
    Binding,
    DataField,
    Expression,
    NullableType,
    Projection,
    ProjectDocument,
    StructType,
    Table,
    TableGroupMember,
)
from .infer import InferenceError, infer_expression


class NormalizationError(ValueError):
    """A candidate document whose expressions cannot be typed."""

    def __init__(self, issues: list[str]) -> None:
        super().__init__("; ".join(issues) or "expressions could not be typed")
        self.issues = issues


def struct_module(package: str, table_id: str) -> str:
    """The module that will declare a table's structs."""
    return f"{package}.table.{table_id}"


def normalize_document(document: ProjectDocument, *, strict: bool = True) -> ProjectDocument:
    """Recompute struct reference modules and every expression's logical types.

    ``strict`` raises :class:`NormalizationError` when an expression cannot be
    typed, which is how the API rejects an edit rather than persisting something the
    generator cannot render. A non-strict pass keeps a half-finished edit viewable.
    """
    homes = _struct_homes(document)
    problems: list[str] = []

    structs = tuple(
        struct.updated(fields=_repair_fields(struct.fields, homes)) for struct in document.structs
    )
    tables = tuple(
        table.updated(
            fields=_repair_fields(table.fields, homes),
            members=_members_for(table, document),
        )
        for table in document.tables
    )
    projections = tuple(
        projection.updated(
            fields=tuple(
                field.updated(
                    expression=_typed(
                        field.expression, document, f"projection:{projection.id}.{field.name}", problems
                    )
                )
                for field in projection.fields
            )
        )
        for projection in document.projections
    )
    bindings = tuple(
        _repair_binding(binding, document, problems) for binding in document.bindings
    )

    normalized = document.updated(
        structs=structs, tables=tables, projections=projections, bindings=bindings
    )
    if problems and strict:
        raise NormalizationError(problems)
    return normalized


def _members_for(table: Table, document: ProjectDocument) -> tuple[TableGroupMember, ...]:
    """Rebuild a group's member list from who declares it as their parent.

    ``Table.members`` and ``Table.group`` describe one relationship from two sides,
    and a client can get them out of step — copying a group to derive a member, for
    instance, carries the member list along. The parent pointer is authoritative and
    the list is derived, so the generator and the UI can never disagree with it.
    """
    if table.is_group:
        return tuple(
            TableGroupMember(python_name=member.name, ref=member.id)
            for member in sorted(
                (candidate for candidate in document.tables if candidate.group == table.id),
                key=lambda candidate: candidate.name,
            )
        )
    return ()


def _repair_fields(fields: tuple[DataField, ...], homes: dict[str, str]) -> tuple[DataField, ...]:
    return tuple(
        field.updated(logical_type=_repair_type(field.logical_type, homes)) for field in fields
    )


def _repair_binding(binding: Binding, document: ProjectDocument, problems: list[str]) -> Binding:
    where = f"binding:{binding.id}"
    return binding.updated(
        build_key=_typed(binding.build_key, document, f"{where}.build_key", problems),
        source_build_key=(
            None
            if binding.source_build_key is None
            else _typed(binding.source_build_key, document, f"{where}.source_build_key", problems)
        ),
        target_build_key=(
            None
            if binding.target_build_key is None
            else _typed(binding.target_build_key, document, f"{where}.target_build_key", problems)
        ),
        properties=tuple(
            item.updated(
                expression=_typed(item.expression, document, f"{where}.property.{item.name}", problems)
            )
            for item in binding.properties
        ),
    )


def _typed(
    expression: Expression, document: ProjectDocument, where: str, problems: list[str]
) -> Expression:
    try:
        return infer_expression(document, expression)
    except InferenceError as error:
        problems.append(f"{where}: {error}")
        return expression
    except Exception as error:  # noqa: BLE001 - a save must report, not traceback
        problems.append(f"{where}: expression could not be typed ({type(error).__name__}: {error})")
        return expression


def _repair_type(value: Any, homes: dict[str, str]) -> Any:
    if isinstance(value, NullableType):
        return value.updated(value=_repair_non_null(value.value, homes))
    return _repair_non_null(value, homes)


def _repair_non_null(value: Any, homes: dict[str, str]) -> Any:
    if isinstance(value, StructType):
        module = homes.get(value.qualname, value.module)
        return value.updated(module=module)
    if isinstance(value, ArrayType):
        return value.updated(item=_repair_type(value.item, homes))
    return value


def _struct_homes(document: ProjectDocument) -> dict[str, str]:
    """Map each struct's class name to the module that will declare it.

    A struct belongs to the first table, in document order, whose field tree reaches
    it — that is the package the generator writes it into, so a ``struct`` logical
    type must name that module for the generated annotation to import.
    """
    homes: dict[str, str] = {}
    for table in document.tables:
        for qualname in _referenced_structs(document, table.fields):
            homes.setdefault(qualname, struct_module(document.project.package, table.id))
    return homes


def _referenced_structs(document: ProjectDocument, fields: tuple[DataField, ...]) -> tuple[str, ...]:
    found: list[str] = []
    pending = [field.logical_type for field in fields]
    seen: set[str] = set()
    while pending:
        value = pending.pop(0)
        if isinstance(value, NullableType):
            pending.append(value.value)
        elif isinstance(value, ArrayType):
            pending.append(value.item)
        elif isinstance(value, StructType):
            if value.qualname in seen:
                continue
            seen.add(value.qualname)
            found.append(value.qualname)
            struct = next(
                (item for item in document.structs if item.declaration_name == value.qualname),
                None,
            )
            if struct is not None:
                pending.extend(field.logical_type for field in struct.fields)
    return tuple(found)
