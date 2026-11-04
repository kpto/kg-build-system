"""Link, compile and execute one toolchain flow.

Private implementation behind the public ``Toolchain``. It imports only kernel
model values; resources, executors and instruction payloads stay opaque.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from ...model.public.runtime import RuntimeConfiguration
from ...model.public.workflow import (
    Component,
    Step,
    WorkflowPlan,
)
from .assembly import assemble_plan


def build_model(
    languages: Sequence[Any], linker: Any, namespace: Any,
) -> Any:
    """Hand the language declarations to the linker."""
    return linker.link(tuple(languages), namespace)


def compile_model(
    planners: Sequence[Any], model: Any, context: Any,
) -> WorkflowPlan:
    """Group planners by component and assemble their steps into one plan.

    Several planners may share a ``component_id``. They must agree on
    ``version`` and ``runtime_fields``; the component is published once and the
    component id is assigned to every step the group produces.
    """
    groups: dict[str, list[Any]] = {}
    for planner in planners:
        groups.setdefault(planner.component_id, []).append(planner)

    contributions: list[tuple[Component, tuple[Step, ...]]] = []
    seen_steps: set[str] = set()
    for component_id, group in groups.items():
        first = group[0]
        component = Component(
            component_id,
            first.version,
            tuple(first.runtime_fields),
        )
        for planner in group[1:]:
            if planner.version != component.version:
                raise ValueError(
                    f"planners for component {component_id!r} disagree on "
                    f"version: {component.version!r} and {planner.version!r}"
                )
            if tuple(planner.runtime_fields) != component.runtime_fields:
                raise ValueError(
                    f"planners for component {component_id!r} disagree on "
                    "runtime_fields"
                )
        steps: list[Step] = []
        for planner in group:
            for step in planner.plan(model, context):
                assigned = replace(step, component=component_id)
                identity = f"{component_id}.{assigned.name}"
                if identity in seen_steps:
                    raise ValueError(f"duplicate step id {identity!r}")
                seen_steps.add(identity)
                steps.append(assigned)
        contributions.append((component, tuple(steps)))
    return assemble_plan(tuple(contributions))


def execute_plan(
    executors: Sequence[Any],
    runtime: Any,
    plan: WorkflowPlan,
    *,
    output_directory: Path,
    configuration: RuntimeConfiguration | None = None,
    monitor: Any = None,
) -> Any:
    """Resolve instruction kinds and run one plan through the runtime."""
    by_kind: dict[tuple[str, ...], Any] = {}
    for executor in executors:
        for kind in executor.kinds:
            if kind in by_kind:
                raise ValueError(
                    f"duplicate executor for instruction kind {kind!r}"
                )
            by_kind[kind] = executor

    unknown: list[tuple[str, ...]] = []
    for step in plan.steps:
        kind = step.instruction.kind
        if kind not in by_kind and kind not in unknown:
            unknown.append(kind)
    if unknown:
        listed = ", ".join(repr(kind) for kind in unknown)
        raise ValueError(f"no executor for instruction kind(s): {listed}")

    resolved = (
        configuration
        if configuration is not None
        else RuntimeConfiguration(
            output_directory=Path(output_directory),
            working_directory=Path(output_directory) / "_workdir",
        )
    )
    return runtime.execute(
        plan,
        by_kind,
        configuration=resolved,
        monitor=monitor,
    )


__all__ = ["build_model", "compile_model", "execute_plan"]
