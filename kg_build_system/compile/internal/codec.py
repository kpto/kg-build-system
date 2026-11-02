"""Blueprint codec: the canonical JSON-compatible document."""
from __future__ import annotations

from typing import Any

from .ir import BlueprintModule, BuildBlueprint


def encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    """Encode a blueprint into its canonical document."""
    from ...binding.internal import encode_binding_part
    from ...table.internal import encode_data_part
    from ...table.internal.ir import DataIR
    from ...topology.internal import encode_topology_part

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
    """Decode a blueprint from its canonical document."""
    from ...table.internal import decode_data_part
    from ...topology.internal import decode_topology_part
    from ...binding.internal import decode_binding_part

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


__all__ = ["decode_blueprint", "encode_blueprint"]
