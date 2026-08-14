"""Aggregate compilation DTO for an immutable declaration blueprint."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

from ..binding.dto import BindingDTO
from ..table.dto import ProjectionDTO, SourceDTO, StructDTO, TableDTO
from ..topology.dto import ComponentDTO
from ..workflow.dto import BlueprintModuleDTO


BLUEPRINT_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """A compilation artifact containing no authoring Python classes."""

    structs: tuple[StructDTO, ...]
    tables: tuple[TableDTO, ...]
    components: tuple[ComponentDTO, ...]
    projections: tuple[ProjectionDTO, ...]
    bindings: tuple[BindingDTO, ...]
    sources: tuple[SourceDTO, ...] = ()
    modules: tuple[BlueprintModuleDTO, ...] = ()
    schema_version: Literal[1] = 1

    def model_dump(self, *, mode: str = "python", **_: Any) -> dict[str, Any]:
        from .codec import encode_blueprint

        return encode_blueprint(self)

    def model_dump_json(self, *, indent: int | None = None, **_: Any) -> str:
        from .codec import blueprint_json

        return blueprint_json(self, indent=indent)

    @classmethod
    def model_validate(cls, value: Any) -> "BuildBlueprint":
        from collections.abc import Mapping

        from .codec import decode_blueprint

        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("blueprints must be decoded from an object")
        return decode_blueprint(value)

    @classmethod
    def model_validate_json(cls, value: str | bytes | bytearray) -> "BuildBlueprint":
        from .codec import blueprint_from_json

        return blueprint_from_json(value)


__all__ = ["BLUEPRINT_SCHEMA_VERSION", "BuildBlueprint"]
