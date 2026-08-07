"""Minimal JSON provider used to prove the code-generation extension."""

from __future__ import annotations

import json
import keyword
from pathlib import Path
import re
from typing import Any, ClassVar

from .models import GeneratedClass, GeneratedField, GeneratedFieldKind, GeneratedModule, GenerationError, ProviderGenerationConfig
from .providers import Provider, ProviderContext


_TYPES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}


def _identifier(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", result).lower().strip("_") or "field"
    if result[0].isdigit():
        result = f"field_{result}"
    if keyword.iskeyword(result) or result == "options":
        result += "_"
    return result


class DummyGenerationConfig(ProviderGenerationConfig):
    source: str
    selector: str | None = None


class DummyProvider(Provider[DummyGenerationConfig]):
    """Read ``{"fields": [{"name": ..., "type": ...}]}`` JSON schemas."""

    ID: ClassVar[str] = "dummy"
    VERSION: ClassVar[str] = "1"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = DummyGenerationConfig

    @classmethod
    def dependencies(cls, context: ProviderContext[DummyGenerationConfig]) -> tuple[Path, ...]:
        return (context.resolve_path(context.config.source),)

    @classmethod
    def generate(cls, context: ProviderContext[DummyGenerationConfig], *, generated_name: str) -> GeneratedModule:
        path = cls.dependencies(context)[0]
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise GenerationError(f"cannot load dummy schema {path}: {error}") from error
        if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
            raise GenerationError("dummy schema must contain a fields array")
        fields: list[GeneratedField] = []
        used: dict[str, str] = {}
        for item in schema["fields"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise GenerationError("every dummy field requires a string name")
            external = item["name"]
            python_name = _identifier(external)
            if python_name in used:
                raise GenerationError(f"dummy fields {used[python_name]!r} and {external!r} collide")
            used[python_name] = external
            raw_type = item.get("type", "string")
            if raw_type not in _TYPES:
                raise GenerationError(f"unsupported dummy field type {raw_type!r}")
            fields.append(
                GeneratedField(
                    python_name=python_name,
                    external_name=external,
                    kind=GeneratedFieldKind.SCALAR,
                    value_type=_TYPES[raw_type],
                    nullable=bool(item.get("nullable", False)),
                    description=item.get("description") if isinstance(item.get("description"), str) else None,
                )
            )
        if not fields:
            raise GenerationError("dummy schema must contain at least one field")
        return GeneratedModule((GeneratedClass(generated_name, tuple(fields)),))
