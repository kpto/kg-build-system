"""Compile a blueprint into a workflow contract through the private pipeline."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.declaration.blueprint.model.public import GraphBlueprint
from .....contract.model.public import WorkflowContractDTO


def compile_blueprint(
    blueprint: GraphBlueprint, *, modules: Sequence[Any], engine: Any = None,
) -> WorkflowContractDTO:
    """Compile a blueprint and its module compilers into the contract DTO."""
    from ..._private.compiler.pipeline import compile_blueprint as _compile_blueprint

    return _compile_blueprint(blueprint, modules=modules, engine=engine)


__all__ = ["compile_blueprint"]
