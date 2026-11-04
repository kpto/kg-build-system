"""Declaration class-creation mechanics and projection planning helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from kg_build_system.distribution.languages.annotations.model.public import Annotation
from kg_build_system.kernel.model.public.types import Shape
from ...model.internal.model.declarations import DeclarationSpec
from ...model.internal.model.fields import FieldSpec
from ...model.public.declarations import is_concrete_table, is_table_group
from .descriptors import resolve_field_specs
from .naming import declaration_name

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import BoolExpression
    from ...model.public.row_sources import DerivedRowSource


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
    from ...model.public.declarations import StructOptions, StructOptionsTemplate, TableOptions

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
    from ...model.public.declarations import StructOptionsTemplate

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
    from kg_build_system.distribution.languages.expressions.model.public import BoolExpression
    from .rows import derive_row_source
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
    from ...model.public.declarations import Projection

    attrs: dict[str, Any] = {
        "_kg_row_source": row_source,
        "_projection_base": True,
    }
    return type("PinnedProjectionBase", (Projection,), attrs)


def projection_base(row_source: Any) -> type[Any]:
    """A dynamic base carrying a row source plan and its inherited fields."""
    from ...model.public.declarations import Projection
    from .rows import as_row_source
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
    from kg_build_system.distribution.languages.expressions.service.internal import expression_dto
    from kg_build_system.distribution.languages.expressions.model.internal import FieldReferenceDTO
    from ...model.internal.dto.blueprint_dto import RowScanDTO

    try:
        from kg_build_system.distribution.languages.expressions.service.internal import walk_expression_dto
    except ImportError:  # pragma: no cover - depends on the expressions surface
        from kg_build_system.distribution.languages.expressions.service.internal import walk_expression_dto

    spec = vars(declaration).get("_kg_declaration_spec")
    if spec is None:
        return getattr(declaration, "_projection_row_source", None)
    sources: set[str] = set()
    for item in spec.fields:
        expression = item.descriptor.expression
        if expression is None:
            continue
        for node in walk_expression_dto(expression_dto(expression.model)):
            if isinstance(node, FieldReferenceDTO):
                sources.add(node.source)
    if len(sources) == 1:
        return RowScanDTO(next(iter(sources)))
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


def prepare_table_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``Table`` declaration at class creation."""
    from ...model.public.declarations import TableOptions

    if any(_final_kind(base) == "table" for base in cls.__mro__[1:]):
        raise TypeError("a final Table may not inherit from another final Table")
    options = vars(cls).get("options", TableOptions())
    _require_host_options(cls, "Table", options, TableOptions)
    name = options.name or declaration_name(cls.__name__, suffixes=("Table",))
    cls._table_name = name
    _prepare_declaration(
        cls,
        kind="table",
        name=name,
        description=_description(cls, options.description),
        annotations=(*_template_annotations(cls), *options.annotations),
    )
    cls.shape = cls


def prepare_struct_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``Struct`` declaration at class creation."""
    from ...model.public.declarations import StructOptions

    options = vars(cls).get("options", StructOptions())
    _require_host_options(cls, "Struct", options, StructOptions)
    name = options.name or declaration_name(cls.__name__, suffixes=("Struct",))
    _prepare_declaration(
        cls,
        kind="struct",
        name=name,
        description=_description(cls, options.description),
        annotations=(*_template_annotations(cls), *options.annotations),
    )


def prepare_computed_struct_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``ComputedStruct`` declaration."""
    from ...model.public.declarations import StructOptions

    options = vars(cls).get("options", StructOptions())
    _require_host_options(cls, "ComputedStruct", options, StructOptions)
    name = options.name or declaration_name(
        cls.__name__, suffixes=("ComputedStruct",),
    )
    _prepare_declaration(
        cls,
        kind="computed_struct",
        name=name,
        description=_description(cls, options.description),
        annotations=(*_template_annotations(cls), *options.annotations),
    )


def prepare_projection_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``Projection`` declaration at class creation."""
    from ...model.public.declarations import ProjectionOptions

    is_base = bool(vars(cls).get("_projection_base", False))
    if not is_base and any(
        _final_kind(base) == "projection" for base in cls.__mro__[1:]
    ):
        raise TypeError(
            "a final Projection may not inherit from another final Projection"
        )
    options = vars(cls).get("options", ProjectionOptions())
    _require_host_options(cls, "Projection", options, ProjectionOptions)

    row_source = next(
        (
            vars(base).get("_kg_row_source")
            for base in cls.__mro__
            if "_kg_row_source" in vars(base)
        ),
        None,
    )
    name = options.name or declaration_name(
        cls.__name__, suffixes=("Projection",),
    )
    spec = _prepare_declaration(
        cls,
        kind="projection",
        name=name,
        description=_description(cls, options.description),
        annotations=tuple(options.annotations),
        final=not is_base,
        row_source=row_source,
    )
    if not spec.fields and not is_base:
        raise TypeError("projections must declare at least one computed_field")
    cls._projection_name = name
    cls._projection_row_source = row_source
    setattr(cls, "shape", shape_view(cls))


def prepare_table_group_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``TableGroup`` declaration at class creation."""
    from ...model.public.declarations import TableGroupOptions

    if any(_final_kind(base) == "table_group" for base in cls.__mro__[1:]):
        raise TypeError(
            "a final TableGroup may not inherit from another final TableGroup"
        )
    options = vars(cls).get("options", TableGroupOptions())
    _require_host_options(cls, "TableGroup", options, TableGroupOptions)

    declared: dict[str, type[Any]] = {}
    for base in reversed(cls.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, type) and (
                is_concrete_table(value) or is_table_group(value)
            ):
                declared[attribute] = value
            elif attribute in declared:
                del declared[attribute]

    invalid = tuple(
        member
        for member in options.members
        if not is_concrete_table(member) and not is_table_group(member)
    )
    if invalid:
        raise TypeError(
            "table groups may contain only final Table or TableGroup declarations"
        )
    entries = tuple(dict.fromkeys((*options.members, *declared.values())))
    if not entries:
        raise TypeError("table groups must declare at least one member")

    name = options.name or declaration_name(
        cls.__name__, suffixes=("TableGroup",),
    )
    cls._table_group_name = name
    cls._table_group_entries = entries
    _prepare_declaration(
        cls,
        kind="table_group",
        name=name,
        description=_description(cls, options.description),
        annotations=tuple(options.annotations),
        members=entries,
    )
    cls._is_table_group = True

    from .sources import group_tables

    group_tables(cls)


def require_struct_template_host(cls: type[Any]) -> None:
    """Reject a template mixed into a declaration that is not a record host."""
    from ...model.public.declarations import Projection, TableGroup

    if issubclass(cls, (Projection, TableGroup)):
        raise TypeError(
            f"{cls.__name__} mixes StructTemplate into a non-record declaration: "
            "the template tier serves only Table, Struct and ComputedStruct hosts"
        )


def prepare_struct_template_annotations(cls: type[Any]) -> None:
    """Record a template's own annotations when it has a record host."""
    from ...model.public.declarations import ComputedStruct, Struct, Table

    if issubclass(cls, (Table, Struct, ComputedStruct)):
        return
    _record_template_annotations(cls, vars(cls).get("options"))


def prepare_projection_type(source: Any | None) -> type[Any]:
    """Build the pinned projection base for ``Projection(source)``."""
    if source is None:
        raise TypeError(
            "Projection(source) requires a row source; "
            "declare outputs on a named subclass"
        )
    from .rows import as_row_source

    return pinned_base(as_row_source(source))


__all__ = [
    "DeclarationSpec", "S", "is_concrete_table", "is_table_group",
    "pinned_base", "prepare_computed_struct_declaration",
    "prepare_projection_declaration", "prepare_projection_type",
    "prepare_struct_declaration", "prepare_struct_template_annotations",
    "prepare_table_declaration", "prepare_table_group_declaration",
    "projection_base", "projection_row_source", "require_struct_template_host",
    "shape_view",
]
