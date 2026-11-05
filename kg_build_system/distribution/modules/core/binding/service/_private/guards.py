"""Guards that keep a binding's declared non-null values non-null."""
from __future__ import annotations

from collections.abc import Mapping

from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
)
from kg_build_system.distribution.modules.core.service._private.planning.emission import (
    binding_outputs,
    sql_type_for,
)
from kg_build_system.distribution.service.internal.emission import (
    NULL_GUARD_MACRO,
    canonical_sql_type,
)
from kg_build_system.kernel.model.internal.types.dto import (
    LogicalTypeDTO,
    NullableTypeDTO,
)

ROW_KEY = "_kg_named._kg_raw_build_key"
RAW = "_kg_raw_"


def quote_identifier(value: str) -> str:
    """Quote one SQL identifier."""
    return '"' + value.replace('"', '""') + '"'


def sql_string(value: str) -> str:
    """Quote one SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def claim_message(binding: BindingDTO, name: str) -> str:
    """A SQL expression naming the binding and, where possible, the row."""
    subject = f"{binding.component}.{name}"
    if name == "build_key":
        return sql_string(
            f"{subject} is null, but it is declared non-null"
        )
    return (
        sql_string(f"{subject} is null for build_key ")
        + " || coalesce(CAST(" + ROW_KEY + " AS VARCHAR), '<null>')"
    )


def binding_guard_projection(binding: BindingDTO) -> str:
    """The guarded select list reading a binding's renamed row values."""
    guarded: list[str] = []
    for name, expression in binding_outputs(binding).items():
        column = quote_identifier(RAW + name)
        if isinstance(expression.logical_type, NullableTypeDTO):
            guarded.append(f"{column} AS {quote_identifier(name)}")
            continue
        guarded.append(
            f"{NULL_GUARD_MACRO}({column}, "
            f"{claim_message(binding, name)}) AS {quote_identifier(name)}"
        )
    return ", ".join(guarded)


def binding_rename_projection(
    binding: BindingDTO,
    property_types: Mapping[str, LogicalTypeDTO] | None = None,
) -> str:
    """Cast each property to its declared type, then rename it for the guards."""
    declared = property_types or {}
    items: list[str] = []
    for name in binding_outputs(binding):
        column = quote_identifier(name)
        raw = quote_identifier(RAW + name)
        logical_type = declared.get(name)
        sql_type = None if logical_type is None else sql_type_for(logical_type)
        if sql_type is None:
            items.append(f"{column} AS {raw}")
        else:
            items.append(
                f"CAST({column} AS {canonical_sql_type(sql_type)}) AS {raw}"
            )
    return ", ".join(items)


__all__ = [
    "RAW",
    "ROW_KEY",
    "binding_guard_projection",
    "binding_rename_projection",
    "claim_message",
    "quote_identifier",
    "sql_string",
]
