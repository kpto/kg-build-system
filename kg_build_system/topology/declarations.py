"""Small declaration factories retained by the topology authoring surface."""

from .models import property


def is_final_component(cls: type) -> bool:
    return vars(cls).get("_component_declaration_kind") in {"node", "edge"}

__all__ = ["is_final_component", "property"]
