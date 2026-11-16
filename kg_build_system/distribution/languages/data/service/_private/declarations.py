"""Declaration class-creation mechanics and derived-relation planning helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, get_args, get_origin

from kg_build_system.distribution.languages.annotations.model.public import Annotation
from kg_build_system.kernel.model.public.types import Shape
from ...model.internal.model.declarations import DeclarationSpec
from ...model.internal.model.fields import FieldSpec
from ...model.public.declarations import is_concrete_source_relation, is_source_relation_group
from .descriptors import resolve_field_specs
from .naming import declaration_name, snake_case

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import Selection
    from ...model.public.row_sources import DerivedRowSource


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
    from ...model.public.declarations import StructOptions, StructOptionsTemplate, SourceRelationOptions

    if options is None:
        cls._kg_template_annotations = ()
        return
    if isinstance(options, StructOptionsTemplate):
        cls._kg_template_annotations = tuple(options.annotations)
        return
    if isinstance(options, (SourceRelationOptions, StructOptions)):
        raise TypeError(
            f"{cls.__name__} is a data template: its options must be "
            "StructOptionsTemplate, which carries no name — wrap it: "
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
    annotations: tuple[Annotation, ...],
    final: bool = True,
    row_source: Any = None,
    members: tuple[type[Any], ...] = (),
    asset: Any = None,
    meaning: Any = None,
    definition: Any = None,
) -> DeclarationSpec:
    field_kind = "source" if kind in {"source_relation", "struct"} else "computed"
    fields = resolve_field_specs(cls, field_kind)
    spec = DeclarationSpec(
        kind=kind,
        name=name,
        annotations=annotations,
        fields=fields,
        final=final,
        row_source=row_source,
        members=members,
        asset=asset,
        meaning=meaning,
        definition=definition,
    )
    cls._kg_declaration_spec = spec
    cls._fields = {item.attribute: item.descriptor for item in fields}
    cls._data_name = name
    cls._data_annotations = annotations
    cls._data_declaration_kind = kind if final else None
    return spec


S = TypeVar("S", bound=Shape)


def _derive(
    declaration: type[Any],
    predicate: Callable[[Any], "Selection[bool]"],
) -> "DerivedRowSource[Any]":
    from kg_build_system.distribution.languages.expressions.model.public import Selection
    from .rows import derive_row_source
    from .shapes import make_shape_context, shape_view

    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    shape = shape_view(declaration)
    result = predicate(make_shape_context(shape))
    if not isinstance(result, Selection):
        raise TypeError("where predicates must return a Selection[bool]")
    return derive_row_source(declaration.row_source(), result, shape=shape)


def shape_view(source: Any) -> type[Shape]:
    """A shape class with the source's fields, usable as a derived-relation base."""
    from .shapes import shape_view as _shape_view

    return _shape_view(source)


def pinned_base(row_source: Any) -> type[Any]:
    """A dynamic derived-relation base carrying only a row source pin."""
    from ...model.public.declarations import DerivedRelation

    return _pinned_computed_base(
        DerivedRelation, row_source, "_derived_relation_base",
    )


def _pinned_computed_base(
    declaration: type[Any], row_source: Any, marker: str,
) -> type[Any]:
    attrs: dict[str, Any] = {
        "_kg_row_source": row_source,
        marker: True,
    }
    return type(f"Pinned{declaration.__name__}Base", (declaration,), attrs)






def derived_relation_row_source(declaration: type[Any]) -> Any | None:
    """The pinned row source of a derived relation."""
    spec = vars(declaration).get("_kg_declaration_spec")
    if spec is not None:
        return spec.row_source
    return getattr(declaration, "_derived_relation_row_source", None)


def _source_relation_asset(cls: type[Any]) -> type[Any]:
    """Resolve the logical asset a source relation names through ``SourceRelation[Asset]``."""
    from kg_build_system.distribution.languages.asset.model.public import Asset
    from ...model.public.declarations import SourceRelation

    for base in getattr(cls, "__orig_bases__", ()):
        if get_origin(base) is not SourceRelation:
            continue
        arguments = get_args(base)
        if not arguments:
            continue
        asset = arguments[0]
        if not isinstance(asset, type) or not issubclass(asset, Asset):
            raise TypeError(
                f"{cls.__name__} must name an Asset subclass: "
                "SourceRelation[Asset]"
            )
        return asset
    raise TypeError(
        f"{cls.__name__} is a concrete SourceRelation without an asset; "
        "declare it as SourceRelation[Asset]"
    )


def prepare_source_relation_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``SourceRelation[Asset]`` declaration at class creation."""
    from ...model.public.declarations import SourceRelationOptions

    if any(_final_kind(base) == "source_relation" for base in cls.__mro__[1:]):
        raise TypeError("a final source relation may not inherit from another final source relation")
    options = vars(cls).get("options", SourceRelationOptions())
    _require_host_options(cls, "SourceRelation", options, SourceRelationOptions)
    name = options.name or declaration_name(cls.__name__, suffixes=("SourceRelation",))
    asset = _source_relation_asset(cls)
    contract = options.contract
    definition = contract.definition if contract is not None else None
    meaning = contract.meaning if contract is not None else None
    cls._source_relation_name = name
    cls._source_relation_asset = asset
    spec = _prepare_declaration(
        cls,
        kind="source_relation",
        name=name,
        annotations=(*_template_annotations(cls), *options.annotations),
        asset=asset,
        meaning=meaning,
        definition=definition,
    )
    _validate_definition_outputs(cls, definition, spec)
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
        annotations=(*_template_annotations(cls), *options.annotations),
        meaning=options.meaning,
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
        annotations=(*_template_annotations(cls), *options.annotations),
        meaning=options.meaning,
    )


def _computed_row_source(cls: type[Any]) -> Any:
    """The row source a computed declaration was pinned to."""
    return next(
        (
            vars(base).get("_kg_row_source")
            for base in cls.__mro__
            if "_kg_row_source" in vars(base)
        ),
        None,
    )


def _validate_definition_outputs(
    cls: type[Any], definition: Any, spec: DeclarationSpec,
) -> None:
    """Every identity name must be an external output of the declaring class."""
    if definition is None:
        return
    outputs = {field.name for field in spec.fields}
    for name in definition.identity:
        if name not in outputs:
            raise ValueError(
                f"{cls.__name__} definition identity names unknown output {name!r}"
            )


def _prepare_computed_relation(
    cls: type[Any],
    *,
    kind: str,
    base_marker: str,
    label: str,
    options_type: type[Any],
    suffixes: tuple[str, ...] | None,
) -> DeclarationSpec:
    """Record one derived relation or stage from its shared computed members."""
    from ...model.public.declarations import StageOptions

    is_base = bool(vars(cls).get(base_marker, False))
    if not is_base and any(
        _final_kind(base) == kind for base in cls.__mro__[1:]
    ):
        raise TypeError(
            f"a final {label} may not inherit from another final {label}"
        )
    row_source = _computed_row_source(cls)
    if not is_base and row_source is None:
        raise TypeError(
            f"{label}(source) requires a row source; declare outputs on a "
            f"named subclass of {label}(row_source)"
        )
    options = vars(cls).get("options")
    if options is None:
        if not is_base:
            if kind == "stage":
                raise ValueError("a stage requires a Definition")
            raise ValueError(
                "a derived relation requires a Contract with a Definition "
                "and a Meaning"
            )
        name = (
            declaration_name(cls.__name__, suffixes=suffixes)
            if suffixes is not None else snake_case(cls.__name__)
        )
        definition = None
        meaning = None
    else:
        _require_host_options(cls, label, options, options_type)
        name = (
            options.name
            or (
                declaration_name(cls.__name__, suffixes=suffixes)
                if suffixes is not None else snake_case(cls.__name__)
            )
        )
        if isinstance(options, StageOptions):
            definition = options.definition
            meaning = None
        else:
            contract = options.contract
            if contract is None:
                raise ValueError(
                    "a derived relation requires a Contract with a Definition "
                    "and a Meaning"
                )
            definition = contract.definition
            meaning = contract.meaning
            if meaning.purpose is None:
                raise ValueError(
                    "a derived relation contract requires a purpose"
                )
    spec = _prepare_declaration(
        cls,
        kind=kind,
        name=name,
        annotations=tuple(options.annotations) if options else (),
        final=not is_base,
        row_source=row_source,
        meaning=meaning,
        definition=definition,
    )
    if not is_base and not spec.fields:
        raise TypeError(
            "derived relations must declare at least one computed_field"
            if kind == "derived_relation"
            else "stages must declare at least one computed_field"
        )
    _validate_definition_outputs(cls, definition, spec)
    if kind == "derived_relation":
        cls._derived_relation_name = name
        cls._derived_relation_row_source = row_source
    else:
        cls._stage_name = name
        cls._stage_row_source = row_source
    setattr(cls, "shape", shape_view(cls))
    return spec


def prepare_derived_relation_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``DerivedRelation`` declaration at class creation."""
    from ...model.public.declarations import DerivedRelationOptions

    _prepare_computed_relation(
        cls,
        kind="derived_relation",
        base_marker="_derived_relation_base",
        label="DerivedRelation",
        options_type=DerivedRelationOptions,
        suffixes=("DerivedRelation",),
    )


def prepare_stage_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``Stage`` declaration at class creation."""
    from ...model.public.declarations import StageOptions

    _prepare_computed_relation(
        cls,
        kind="stage",
        base_marker="_stage_base",
        label="Stage",
        options_type=StageOptions,
        suffixes=None,
    )


def prepare_source_relation_group_declaration(cls: type[Any]) -> None:
    """Record the spec of one ``SourceRelationGroup`` declaration at class creation."""
    from ...model.public.declarations import SourceRelationGroupOptions

    if any(_final_kind(base) == "source_relation_group" for base in cls.__mro__[1:]):
        raise TypeError(
            "a final source relation group may not inherit from another final source relation group"
        )
    options = vars(cls).get("options", SourceRelationGroupOptions())
    _require_host_options(cls, "SourceRelationGroup", options, SourceRelationGroupOptions)

    declared: dict[str, type[Any]] = {}
    for base in reversed(cls.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, type) and (
                is_concrete_source_relation(value) or is_source_relation_group(value)
            ):
                declared[attribute] = value
            elif attribute in declared:
                del declared[attribute]

    invalid = tuple(
        member
        for member in options.members
        if not is_concrete_source_relation(member) and not is_source_relation_group(member)
    )
    if invalid:
        raise TypeError(
            "source relation groups may contain only final source relation or source relation group declarations"
        )
    entries = tuple(dict.fromkeys((*options.members, *declared.values())))
    if not entries:
        raise TypeError("source relation groups must declare at least one member")

    name = options.name or declaration_name(
        cls.__name__, suffixes=("SourceRelationGroup",),
    )
    cls._source_relation_group_name = name
    cls._source_relation_group_entries = entries
    _prepare_declaration(
        cls,
        kind="source_relation_group",
        name=name,
        annotations=tuple(options.annotations),
        members=entries,
    )
    cls._is_source_relation_group = True

    from .groups import group_source_relations

    group_source_relations(cls)


def require_struct_template_host(cls: type[Any]) -> None:
    """Reject a template mixed into a declaration that is not a record host."""
    from ...model.public.declarations import DerivedRelation, SourceRelationGroup

    if issubclass(cls, (DerivedRelation, SourceRelationGroup)):
        raise TypeError(
            f"{cls.__name__} mixes StructTemplate into a non-record declaration: "
            "the template tier serves only source relation, struct and computed struct hosts"
        )


def prepare_struct_template_annotations(cls: type[Any]) -> None:
    """Record a template's own annotations when it has a record host."""
    from ...model.public.declarations import ComputedStruct, Struct, SourceRelation

    if issubclass(cls, (SourceRelation, Struct, ComputedStruct)):
        return
    _record_template_annotations(cls, vars(cls).get("options"))


def prepare_derived_relation_type(source: Any | None) -> type[Any]:
    """Build the pinned derived-relation base for ``DerivedRelation(source)``."""
    if source is None:
        raise TypeError(
            "DerivedRelation(source) requires a row source; "
            "declare outputs on a named subclass"
        )
    from .rows import as_row_source

    return pinned_base(as_row_source(source))


def prepare_stage_type(source: Any | None) -> type[Any]:
    """Build the pinned stage base for ``Stage(source)``."""
    if source is None:
        raise TypeError(
            "Stage(source) requires a row source; "
            "declare outputs on a named subclass"
        )
    from ...model.public.declarations import Stage
    from .rows import as_row_source

    return _pinned_computed_base(
        Stage, as_row_source(source), "_stage_base",
    )


__all__ = [
    "DeclarationSpec", "S", "is_concrete_source_relation", "is_source_relation_group",
    "pinned_base", "prepare_computed_struct_declaration",
    "prepare_derived_relation_declaration", "prepare_derived_relation_type",
    "prepare_stage_declaration", "prepare_stage_type",
    "prepare_struct_declaration", "prepare_struct_template_annotations",
    "prepare_source_relation_declaration", "prepare_source_relation_group_declaration",
    "derived_relation_row_source", "require_struct_template_host",
    "shape_view",
]
