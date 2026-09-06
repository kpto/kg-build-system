"""What the studio can offer the UI right now: modules, types, operators, data files.

The module catalogue is read from the installed framework rather than hardcoded, so
configuration forms in the UI are generated from each module's own
``CONFIGURATION_TYPE`` JSON Schema and cannot drift from it.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Union, cast, get_args, get_origin, get_type_hints

from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    MergeCompatibleFactsModule,
    MetaGraphModule,
    Neo4jModule,
    RejectConflictingNonNullValuesModule,
)
from kg_build_system.types import is_canonical_unit_name

from .ir.document import ProjectDocument
from .ir.infer import OPERATION_CATALOGUE, UnitInputError

#: Core is always appended by ``compile``; it is never configured from the studio.
_MODULE_CLASSES: tuple[type[object], ...] = (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    RejectConflictingNonNullValuesModule,
    FileModule,
    MetaGraphModule,
    Neo4jModule,
)

_OPERATORS = frozenset({"collapse_exact_duplicates", "merge_compatible_facts", "reject_conflicting_non_null_values"})
_TARGETS = frozenset({"file", "meta_graph", "neo4j"})


@dataclass(frozen=True, slots=True)
class ModuleEntry:
    id: str
    role: str
    label: str
    summary: str
    import_module: str
    class_qualname: str
    configuration_schema: dict[str, Any] | None
    default_configuration: dict[str, Any] | None

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "label": self.label,
            "summary": self.summary,
            "import_module": self.import_module,
            "class_qualname": self.class_qualname,
            "configuration_schema": self.configuration_schema,
            "default_configuration": self.default_configuration,
        }


def _sentence(document: str | None) -> str:
    if not document:
        return ""
    first = document.strip().split("\n\n")[0].replace("\n", " ").strip()
    return first


def module_catalogue() -> tuple[ModuleEntry, ...]:
    entries: list[ModuleEntry] = []
    for module_class in _MODULE_CLASSES:
        module_id = str(getattr(module_class, "ID", ""))
        config_type = getattr(module_class, "CONFIGURATION_TYPE", None)
        schema = None if config_type is None else configuration_schema(config_type)
        entries.append(
            ModuleEntry(
                id=module_id,
                role="operator" if module_id in _OPERATORS else "target" if module_id in _TARGETS else "other",
                label=_label(module_id),
                summary=_sentence(module_class.__doc__),
                import_module=module_class.__module__,
                class_qualname=module_class.__qualname__,
                configuration_schema=schema,
                default_configuration=_defaults(schema),
            )
        )
    return tuple(entries)


def configuration_schema(config_type: type[object]) -> dict[str, Any]:
    """A JSON Schema for a module's configuration.

    Module configurations are frozen dataclasses rather than pydantic models, so the
    schema is derived from ``dataclasses.fields`` and the type hints. Deriving it
    here means the UI's configuration form cannot drift from what the module accepts.
    """
    if not dataclasses.is_dataclass(config_type):
        return {"type": "object", "properties": {}, "additionalProperties": False}
    hints = get_type_hints(cast(type, config_type))
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in dataclasses.fields(cast(type, config_type)):
        schema = _schema_for(hints.get(field.name, str))
        if field.default is not dataclasses.MISSING:
            schema["default"] = field.default
        elif field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            schema["default"] = field.default_factory()  # type: ignore[misc]
        else:
            required.append(field.name)
        properties[field.name] = schema
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _schema_for(annotation: object) -> dict[str, Any]:
    origin = get_origin(annotation)
    if origin is Literal:
        return {"type": "string", "enum": list(get_args(annotation))}
    if origin in (list, tuple):
        item_types = [argument for argument in get_args(annotation) if argument is not Ellipsis]
        return {"type": "array", "items": _schema_for(item_types[0]) if item_types else {"type": "string"}}
    if origin is Union:
        arguments = [argument for argument in get_args(annotation) if argument is not type(None)]
        if len(arguments) == 1:
            return {**_schema_for(arguments[0]), "nullable": True}
        return {"anyOf": [_schema_for(argument) for argument in arguments]}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is dict or origin in (dict,):
        return {"type": "object"}
    return {"type": "string"}


def _defaults(schema: dict[str, Any] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    properties = schema.get("properties", {})
    if not properties:
        return {}
    return {
        name: specification["default"]
        for name, specification in properties.items()
        if "default" in specification
    }


def configuration_problems(module_id: str, configuration: dict[str, Any] | None, schema: dict[str, Any]) -> list[str]:
    """Required keys missing and unknown keys, against the derived schema."""
    payload = configuration or {}
    problems: list[str] = []
    for key in schema.get("required", ()):
        if key not in payload:
            problems.append(f"{module_id}: configuration is missing required {key!r}")
    known = set(schema.get("properties", {}))
    for key in payload:
        if key not in known:
            problems.append(f"{module_id}: configuration declares unknown {key!r}")
    return problems


def instantiate_configuration(module_class: type[object], configuration: dict[str, Any] | None) -> object | None:
    config_type = getattr(module_class, "CONFIGURATION_TYPE", None)
    if config_type is None:
        return None
    return config_type(**(configuration or {}))


def _label(module_id: str) -> str:
    return " ".join(part.title() for part in module_id.split("_"))


def type_catalogue() -> list[dict[str, Any]]:
    """The canonical unit vocabulary the type pickers offer."""
    return [
        {"name": name, "representative": representative, "graph_safe": True}
        for name, representative in (
            ("bool", "bool"),
            ("int", "int"),
            ("float", "float"),
            ("str", "str"),
            ("date", "Date"),
            ("time", "Time"),
            ("timestamp", "Timestamp"),
            ("uuid", "Uuid"),
        )
    ]


def operator_catalogue() -> list[dict[str, Any]]:
    """The expression blocks the binding composer can stack, with their guards.

    Each entry carries the family it applies to and the shape it produces, which is
    what lets the UI offer only operations valid for the block below it.
    """
    payload: list[dict[str, Any]] = []
    for name, spec in OPERATION_CATALOGUE.items():
        payload.append({"operator": name, **spec})
    return payload


def data_files(document: ProjectDocument, project_root: Path) -> list[dict[str, str]]:
    """Discoverable physical inputs, offered by the source picker."""
    root = project_root / document.project.data_directory
    if not root.is_dir():
        return []
    extensions = {".json": "json", ".ndjson": "json", ".jsonl": "json", ".csv": "csv", ".parquet": "parquet"}
    found: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        kind = extensions.get(path.suffix.lower())
        if kind is None:
            continue
        found.append(
            {
                "location": path.relative_to(project_root).as_posix(),
                "name": path.stem,
                "format": kind,
                "size_bytes": str(path.stat().st_size),
            }
        )
    return found


def infer_target_options(document: ProjectDocument) -> list[dict[str, str]]:
    """Tables a source may bind to, with the label the picker shows."""
    options: list[dict[str, str]] = []
    for table in document.tables:
        options.append(
            {
                "id": table.id,
                "label": f"{table.name} ({'group' if table.is_group else 'table'})",
                "is_group": str(table.is_group).lower(),
            }
        )
    return options


def vocabulary() -> dict[str, Any]:
    """Static vocabulary shared with the UI on first connection."""
    return {
        "canonical_units": [entry["name"] for entry in type_catalogue()],
        "is_canonical_unit_name": is_canonical_unit_name("str"),
        "formats": ["json", "csv", "parquet"],
        "tiers": ["template", "category", "concrete"],
        "nullability": ["declared", "enforced", "defaulted"],
        "operator_error": UnitInputError.__name__,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_module_class(import_module: str, class_qualname: str) -> type[object]:
    value: object = importlib.import_module(import_module)
    for part in class_qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise TypeError(f"{import_module}.{class_qualname} is not a class")
    return value
