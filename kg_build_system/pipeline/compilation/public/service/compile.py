"""Compile an existing graph blueprint into a workflow contract."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .....declaration.blueprint.public import GraphBlueprint
from ....contract.public import WorkflowContractDTO
from ..._private.compiler.pipeline import compile_blueprint as _compile


def compile_blueprint(
    blueprint: GraphBlueprint,
    *,
    modules: Sequence[Any],
    engine: Any = None,
) -> WorkflowContractDTO:
    """Compile a graph blueprint and its module compilers into a contract.

    The blueprint is read as given; this function never creates one. The
    composition root creates a blueprint and calls this function when it wants
    the canonical shortcut. Each module compiler receives the blueprint's
    in-memory build, and every compiled step carries the instruction that owns
    its execution.

    Example:
    ```python
    from kg_build_system.declaration.blueprint import create_blueprint
    from kg_build_system.pipeline.compilation import compile_blueprint

    blueprint = create_blueprint(namespace_path="graph_pipeline")
    contract = compile_blueprint(blueprint, modules=modules)
    ```
    """
    return _compile(blueprint, modules=modules, engine=engine)


__all__ = ["compile_blueprint"]
