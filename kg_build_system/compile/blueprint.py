"""Aggregate compilation IR for an immutable declaration blueprint."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

from ..binding.ir import BindingIR
from ..table.ir import ProjectionIR, SourceIR, StructIR, TableIR
from ..topology.ir import ComponentIR
from ..workflow.ir import BlueprintModuleIR


BLUEPRINT_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    """A compilation artifact containing no authoring Python classes."""

    structs: tuple[StructIR, ...]
    tables: tuple[TableIR, ...]
    components: tuple[ComponentIR, ...]
    projections: tuple[ProjectionIR, ...]
    bindings: tuple[BindingIR, ...]
    sources: tuple[SourceIR, ...] = ()
    modules: tuple[BlueprintModuleIR, ...] = ()
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
