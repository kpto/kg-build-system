"""Declaration class-creation mechanics and projection planning helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from ...annotations.internal import Annotation
from ...types.internal import Shape
from .descriptors import FieldSpec, resolve_field_specs

if TYPE_CHECKING:
    from ...expressions.internal import BoolExpression
    from ..public.row_sources import DerivedRowSource


@dataclass(frozen=True, slots=True)
class DeclarationSpec:
    """The frozen authoring facts of one declaration class."""

    kind: str
    name: str | None
    description: str | None
    annotations: tuple[Annotation, ...]
    fields: tuple[FieldSpec, ...] = ()
    final: bool = True
    row_source: Any = None
    members: tuple[type[Any], ...] = ()


def _description(cls: type[Any], configured: str | None) -> str | None:
    return configured if configured is not None else (vars(cls).get("__doc__") or None)


def _final_kind(cls: type[Any]) -> str | None:
    spec = vars(cls).get("_kg_declaration_spec")
    return spec.kind if isinstance(spec, DeclarationSpec) and spec.final else None


def _template_annotations(cls: type[Any]) -> tuple[Annotation, ...]:
    """Collect each template's own contribution in C3 order, base first."""
    return tuple(
        annotation
        for base in reversed(cls.__mro__[1:])
        for annotation in vars(base).get("_kg_template_annotations", ())
    )


def _record_template_annotations(cls: type[Any], options: Any) -> None:
    from ..public.declarations import StructOptions, StructOptionsTemplate, TableOptions

    if options is None:
        cls._kg_template_annotations = ()
        return
    if isinstance(options, StructOptionsTemplate):
        cls._kg_template_annotations = tuple(options.annotations)
        return
    if isinstance(options, (TableOptions, StructOptions)):
        raise TypeError(
            f"{cls.__name__} is a data template: its options must be "
            "StructOptionsTemplate, which carries no name or description — wrap it: "
            "`options = StructOptionsTemplate(annotations=(...))`"
        )
    raise TypeError(
        f"{cls.__name__} is a data template: wrap the value: "
        "`options = StructOptionsTemplate(annotations=(...))`"
    )


def _require_host_options(cls: type[Any], kind: str, options: Any, expected: type) -> None:
    from ..public.declarations import StructOptionsTemplate

    if isinstance(options, StructOptionsTemplate):
        raise TypeError(
            f"{cls.__name__} is a {kind} declaration: declare {expected.__name__}, "
            "not template options"
        )
    if not isinstance(options, expected):
        raise TypeError(f"{kind}.options must be a {expected.__name__} value")


def _prepare_declaration(
    cls: type[Any],
    *,
    kind: str,
    name: str | None,
    description: str | None,
    annotations: tuple[Annotation, ...],
    final: bool = True,
    row_source: Any = None,
    members: tuple[type[Any], ...] = (),
) -> DeclarationSpec:
    field_kind = "source" if kind in {"table", "struct"} else "computed"
    fields = resolve_field_specs(cls, field_kind)
    spec = DeclarationSpec(
        kind=kind,
        name=name,
        description=description,
        annotations=annotations,
        fields=fields,
        final=final,
        row_source=row_source,
        members=members,
    )
    cls._kg_declaration_spec = spec
    cls._fields = {item.attribute: item.descriptor for item in fields}
    cls._data_name = name
    cls._data_annotations = annotations
    cls._data_metadata = {"description": description} if description is not None else {}
    cls._data_declaration_kind = kind if final else None
    return spec


S = TypeVar("S", bound=Shape)


def _derive(
    declaration: type[Any],
    predicate: Callable[[Any], "BoolExpression"],
) -> "DerivedRowSource[Any]":
    from ...expressions.internal import BoolExpression
    from .plans import derive_row_source
    from .shapes import make_shape_context, shape_view

    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    shape = shape_view(declaration)
    result = predicate(make_shape_context(shape))
    if not isinstance(result, BoolExpression):
        raise TypeError("where predicates must return a BoolExpression")
    return derive_row_source(declaration.row_source(), result, shape=shape)


def shape_view(source: Any) -> type[Shape]:
    """A shape class with the source's fields, usable as a projection base."""
    from .shapes import shape_view as _shape_view

    return _shape_view(source)


def pinned_base(row_source: Any) -> type[Any]:
    """A dynamic base carrying only a row source pin."""
    from ..public.declarations import Projection

    attrs: dict[str, Any] = {
        "_kg_row_source": row_source,
        "_projection_base": True,
    }
    return type("PinnedProjectionBase", (Projection,), attrs)


def projection_base(row_source: Any) -> type[Any]:
    """A dynamic base carrying a row source plan and its inherited fields."""
    from ..public.declarations import Projection
    from .plans import as_row_source
    from .shapes import projection_attrs

    source = as_row_source(row_source)
    attrs = projection_attrs(source.shape)
    attrs["_kg_row_source"] = source
    attrs["_projection_base"] = True
    base_name = getattr(getattr(source, "source", None), "__name__", "RowSource")
    name = f"{base_name}ProjectionBase"

    return type(name, (Projection,), attrs)


def _derive_projection_plan(declaration: type[Any]) -> Any | None:
    """Derive the scan of an unpinned projection from its output expressions."""
    from ...expressions.internal import expression_to_ir
    from ...expressions.internal.ir import FieldReferenceExpressionIR
    from ..internal.ir import RowScanIR

    try:
        from ...expressions.internal import walk_expression_ir
    except ImportError:  # pragma: no cover - depends on the expressions surface
        from ...expressions.internal.ir import walk_expression_ir

    spec = vars(declaration).get("_kg_declaration_spec")
    if spec is None:
        return getattr(declaration, "_projection_row_source", None)
    sources: set[str] = set()
    for item in spec.fields:
        expression = item.descriptor.expression
        if expression is None:
            continue
        for node in walk_expression_ir(expression_to_ir(expression.model)):
            if isinstance(node, FieldReferenceExpressionIR):
                sources.add(node.source)
    if len(sources) == 1:
        return RowScanIR(next(iter(sources)))
    return None


def projection_row_source(declaration: type[Any]) -> Any | None:
    """The pinned plan, or the plan derived from an old-style projection."""
    spec = vars(declaration).get("_kg_declaration_spec")
    pinned = spec.row_source if spec is not None else getattr(
        declaration, "_projection_row_source", None,
    )
    if pinned is not None:
        return pinned
    return _derive_projection_plan(declaration)


def is_concrete_table(cls: type[Any]) -> bool:
    """Return whether a class is a final, source-bindable table."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table" and spec.final


def is_table_group(cls: type[Any]) -> bool:
    """Return whether a class is a final table group."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table_group" and spec.final


__all__ = [
    "DeclarationSpec", "S", "is_concrete_table", "is_table_group",
    "pinned_base", "projection_base", "projection_row_source", "shape_view",
]
