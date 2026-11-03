"""Source forms shared by the declaration languages.

The helpers are pure: they take a frozen DTO value and return authoring source
text plus the imports the text needs. A language decides which helpers to call;
the helpers know nothing about a particular language's class declarations.
"""
from __future__ import annotations

import keyword
import re
from collections.abc import Iterable, Mapping
from typing import Any

from kg_build_system.kernel.internal.json import FrozenObject, thaw_json
from kg_build_system.declaration.foundations.annotations.internal import Annotation
from kg_build_system.declaration.foundations.annotations.internal import AnnotationDTO
from kg_build_system.declaration.foundations.annotations.internal import EdgeLabel, NodeLabel
from kg_build_system.kernel.internal.types.dto import (
    ArrayTypeDTO,
    CustomTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
    UnitTypeDTO,
)

_UNIT_SOURCE = {
    "bool": "bool",
    "int": "int",
    "float": "float",
    "str": "str",
    "date": "Date",
    "time": "Time",
    "timestamp": "Timestamp",
    "uuid": "Uuid",
}
_UNIT_IMPORTS = {
    "date": "Date",
    "time": "Time",
    "timestamp": "Timestamp",
    "uuid": "Uuid",
}

_LABELS: dict[tuple[str, str], type[Annotation]] = {
    (NodeLabel.namespace, NodeLabel.annotation_id): NodeLabel,
    (EdgeLabel.namespace, EdgeLabel.annotation_id): EdgeLabel,
}


def snake_case(value: str) -> str:
    """Convert a Python identifier to the portable external-name convention."""
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    return value.lower()


def pascal_case(value: str) -> str:
    """Convert a logical graph name to a class-name stem."""
    parts = [part for part in re.split(r"[^0-9A-Za-z]+", snake_case(value)) if part]
    stem = "".join(part[:1].upper() + part[1:] for part in parts) or "Component"
    if stem[:1].isdigit():
        stem = f"_{stem}"
    return stem


def class_name(value: str, suffix: str) -> str:
    """Return the declaration class name for one logical graph name."""
    return f"{pascal_case(value)}{suffix}"


def member_name(value: str) -> str:
    """Return a valid Python member name for one external member name."""
    candidate = re.sub(r"[^0-9A-Za-z_]+", "_", snake_case(value)).strip("_") or "value"
    if candidate[:1].isdigit():
        candidate = f"_{candidate}"
    if keyword.iskeyword(candidate):
        candidate = f"{candidate}_"
    return candidate


def render_docstring(text: str | None, indent: str = "    ") -> tuple[str, ...]:
    """Render a description as a single docstring line, if present."""
    if not text:
        return ()
    return (f"{indent}{text!r}",)


def render_static_value(value: Any) -> str:
    """Render a JSON-compatible annotation argument as Python source."""
    if isinstance(value, FrozenObject):
        value = thaw_json(value)
    if isinstance(value, Mapping):
        return "{" + ", ".join(
            f"{render_static_value(str(key))}: {render_static_value(item)}"
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        ) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(render_static_value(item) for item in value) + "]"
    return repr(value)


def render_logical_type(
    value: LogicalTypeDTO, imports: set[str],
) -> str:
    """Render a logical type in the author-facing type vocabulary."""
    if isinstance(value, UnitTypeDTO):
        alias = _UNIT_SOURCE[value.name]
        if value.name in _UNIT_IMPORTS:
            imports.add(
                f"from kg_build_system.types import {_UNIT_IMPORTS[value.name]}"
            )
        return alias
    if isinstance(value, NullableTypeDTO):
        return f"{render_logical_type(value.value, imports)} | None"
    if isinstance(value, ArrayTypeDTO):
        imports.add("from kg_build_system.types import Array")
        return f"Array[{render_logical_type(value.item, imports)}]"
    if isinstance(value, (CustomTypeDTO, StructTypeDTO)):
        if value.module and value.module != "builtins" and value.module != "__main__":
            imports.add(f"import {value.module}")
            return f"{value.module}.{value.qualname}"
        return value.qualname
    raise TypeError(f"unsupported logical type {value!r}")


def _all_subclasses(cls: type[Any]) -> Iterable[type[Any]]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _all_subclasses(subclass)


def annotation_class(
    namespace: str, annotation_id: str,
) -> type[Annotation] | None:
    """Return the loaded ``Annotation`` subclass for one portable identity."""
    known = _LABELS.get((namespace, annotation_id))
    if known is not None:
        return known
    for candidate in _all_subclasses(Annotation):
        if (
            getattr(candidate, "namespace", None) == namespace
            and getattr(candidate, "annotation_id", None) == annotation_id
        ):
            return candidate
    return None


def _annotation_arguments(value: AnnotationDTO) -> Any:
    if isinstance(value.arguments, FrozenObject):
        return thaw_json(value.arguments)
    return value.arguments


def render_annotation(value: AnnotationDTO, imports: set[str]) -> str:
    """Render one portable annotation as an authoring constructor call."""
    key = (value.namespace, value.id)
    label = _LABELS.get(key)
    if label is not None:
        imports.add(f"from kg_build_system.declaration.foundations.annotations import {label.__name__}")
        arguments = _annotation_arguments(value)
        if isinstance(arguments, Mapping) and set(arguments) == {"label"}:
            return f"{label.__name__}({arguments['label']!r})"
        return f"{label.__name__}(label={render_static_value(arguments)})"
    cls = annotation_class(value.namespace, value.id)
    if cls is None:
        raise ValueError(
            "cannot render annotation "
            f"{value.namespace!r}/{value.id!r}: no loaded "
            "Annotation subclass declares that identity"
        )
    module = getattr(cls, "__module__", "")
    qualname = getattr(cls, "__qualname__", cls.__name__)
    if module and module != "builtins":
        imports.add(f"import {module}")
        name = f"{module}.{qualname}"
    else:
        name = qualname
    arguments = _annotation_arguments(value)
    if not isinstance(arguments, Mapping):
        raise ValueError(
            f"annotation {value.namespace!r}/{value.id!r} has "
            "non-object arguments"
        )
    if not arguments:
        return f"{name}()"
    return f"{name}(" + ", ".join(
        f"{key_name}={render_static_value(item)}"
        for key_name, item in sorted(arguments.items())
    ) + ")"


__all__ = [
    "annotation_class", "class_name", "member_name", "pascal_case",
    "render_annotation", "render_docstring", "render_logical_type",
    "render_static_value", "snake_case",
]
