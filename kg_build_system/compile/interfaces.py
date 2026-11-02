"""Internal compilation interface."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from ..kernel.contract import CompilationContext
from .ir import BlueprintModule, BuildBlueprint


class ModuleCompiler(Protocol):
    async def compile(self, context: Any) -> Any: ...


class CompilableModule(Protocol):
    ID: str
    VERSION: str
    CONFIGURATION_TYPE: type[Any]

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: ...


def validate_blueprint(blueprint: BuildBlueprint) -> None:
    if not blueprint.components:
        raise ValueError("blueprints require at least one graph component")
    if not blueprint.bindings:
        raise ValueError("blueprints require at least one graph binding")
    symbols = (
        *(item.symbol_id for item in blueprint.structs),
        *(item.symbol_id for item in blueprint.tables),
        *(item.symbol_id for item in blueprint.components),
        *(item.symbol_id for item in blueprint.projections),
        *(item.symbol_id for item in blueprint.bindings),
        *(item.symbol_id for item in blueprint.sources),
    )
    if len(symbols) != len(set(symbols)):
        raise ValueError("blueprint symbol IDs must be unique")
    sources = tuple(item.table for item in blueprint.sources)
    if len(sources) != len(set(sources)):
        raise ValueError("source-bound table names must be unique")


def encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    from ..binding.interfaces import encode_binding_part
    from ..table.interfaces import encode_data_part
    from ..table.ir import DataIR
    from ..topology.interfaces import encode_topology_part

    return {
        "data": encode_data_part(DataIR(
            value.structs, value.tables, value.projections, value.sources,
        )),
        "topology": encode_topology_part(value.components),
        "binding": encode_binding_part(value.bindings),
        "modules": [
            {
                "module_id": item.module_id,
                "module_import": item.module_import,
                "module_qualname": item.module_qualname,
                "configuration": item.configuration,
            }
            for item in value.modules
        ],
    }


def decode_blueprint(value: dict[str, Any]) -> BuildBlueprint:
    from ..table.interfaces import decode_data_part
    from ..topology.interfaces import decode_topology_part
    from ..binding.interfaces import decode_binding_part

    data = decode_data_part(value["data"])
    components = decode_topology_part(value["topology"])
    bindings = decode_binding_part(value["binding"])
    modules = tuple(
        BlueprintModule(
            item["module_id"], item["module_import"], item["module_qualname"],
            item.get("configuration"),
        )
        for item in value.get("modules", ())
    )
    return BuildBlueprint(
        data.structs, data.tables, components, data.projections, bindings,
        data.sources, modules,
    )


__all__ = [
    "BlueprintModule", "BuildBlueprint", "CompilableModule", "CompilationContext",
    "ModuleCompiler",
    "decode_blueprint", "encode_blueprint", "validate_blueprint",
]
