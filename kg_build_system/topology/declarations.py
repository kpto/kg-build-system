"""Small declaration helpers retained by the topology authoring surface."""

from .models import property


def is_concrete_component(cls: type) -> bool:
    return (
        vars(cls).get("_component_declaration_kind") in {"node", "edge"}
        and not vars(cls).get("_component_abstract", False)
    )

__all__ = ["is_concrete_component", "property"]
