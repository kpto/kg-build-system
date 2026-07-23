from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar, cast, final, reveal_type

T = TypeVar("T")


@dataclass(frozen=True)
class TemplateMetadata:
    name: str | None
    description: str | None


@final
class TableDeclaration(Generic[T]):
    _name: ClassVar[str]
    _schema: ClassVar[type[object]]
    _template_name: ClassVar[str | None]
    _template_description: ClassVar[str | None]

    @classmethod
    def table_name(cls) -> str:
        return cls._name

    @classmethod
    def schema_type(cls) -> type[T]:
        return cast(type[T], cls._schema)

    @classmethod
    def template_name(cls) -> str | None:
        return cls._template_name

    @classmethod
    def template_description(cls) -> str | None:
        return cls._template_description


@dataclass(frozen=True)
class BoundTable(Generic[T]):
    declaration: type[TableDeclaration[T]]


def table_template(
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[type[T]], type[T]]:
    def declare(schema: type[T]) -> type[T]:
        setattr(
            schema,
            "__table_template_metadata__",
            TemplateMetadata(name=name, description=description),
        )
        return schema

    return declare


def table(*, name: str) -> Callable[[type[T]], type[TableDeclaration[T]]]:
    def declare(schema: type[T]) -> type[TableDeclaration[T]]:
        metadata = getattr(schema, "__table_template_metadata__", None)
        template_name = metadata.name if isinstance(metadata, TemplateMetadata) else None
        template_description = metadata.description if isinstance(metadata, TemplateMetadata) else None
        generated = type(
            schema.__name__,
            (TableDeclaration, schema),
            {
                "_name": name,
                "_schema": schema,
                "_template_name": template_name,
                "_template_description": template_description,
                "__module__": schema.__module__,
            },
        )
        return cast(type[TableDeclaration[T]], generated)

    return declare


def bind_source(target: type[TableDeclaration[T]]) -> BoundTable[T]:
    return BoundTable(target)


@table_template(
    name="association",
    description="A reusable scored-association row shape.",
)
class Association:
    score: float


@table(name="target_disease")
class TargetDisease(Association):
    evidence_count: int


reveal_type(TargetDisease)
reveal_type(Association)
reveal_type(TargetDisease.table_name())
reveal_type(TargetDisease.schema_type())
reveal_type(TargetDisease.template_name())
reveal_type(TargetDisease.template_description())
reveal_type(bind_source(TargetDisease))

assert TargetDisease.template_name() == "association"
assert TargetDisease.template_description() == "A reusable scored-association row shape."

bind_source(Association)  # expected: template class is not bindable


class InvalidTableInheritance(TargetDisease):  # expected: concrete table is final
    pass
