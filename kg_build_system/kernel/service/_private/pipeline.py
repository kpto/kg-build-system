"""Transcribe, link, compile and execute one toolchain flow.

Private implementation behind the public ``Toolchain``. It imports only kernel
model values and other private kernel flow helpers; services, executors and
instruction payloads stay opaque.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ...model.public.language import Layer
from ...model.public.runtime import RuntimeConfiguration
from ...model.public.workflow import (
    Component,
    Step,
    WorkflowPlan,
)
from .assembly import assemble_plan
from .ordering import order_languages


@dataclass(frozen=True, slots=True)
class LayerContext:
    """Expose already-transcribed layers to a language during transcription."""

    layers: Mapping[str, Layer]

    def layer(self, name: str) -> Layer:
        """Return the transcribed layer named ``name``."""
        return self.layers[name]


def transcribe_layers(
    languages: Sequence[Any],
    namespace: Any,
    declarations: Mapping[str, Sequence[object]] | None = None,
) -> tuple[Layer, ...]:
    """Collect, transcribe and validate one layer per language."""
    layers: dict[str, Layer] = {}
    context = LayerContext(layers)
    result: list[Layer] = []
    for language in languages:
        chosen = (
            declarations[language.name]
            if declarations is not None and language.name in declarations
            else language.collect(namespace)
        )
        layer = language.transcribe(chosen, context)
        if not isinstance(layer, Layer):
            raise TypeError(
                f"language {language.name!r} must transcribe to a Layer"
            )
        if layer.language != language.name:
            raise ValueError(
                f"language {language.name!r} transcribed layer "
                f"{layer.language!r}"
            )
        language.validate(layer)
        layers[language.name] = layer
        result.append(layer)
    return tuple(result)


def build_model(
    languages: Sequence[Any], linker: Any, namespace: Any,
) -> Any:
    """Order languages, transcribe and validate their layers, then link them."""
    ordered = order_languages(languages)
    layers = transcribe_layers(ordered, namespace)
    return linker.link({layer.language: layer for layer in layers})


def compile_model(
    planners: Sequence[Any], model: Any, context: Any,
) -> WorkflowPlan:
    """Plan every component and assemble the resulting steps into one plan."""
    contributions: list[tuple[Component, tuple[Step, ...]]] = []
    seen_components: set[str] = set()
    seen_steps: set[str] = set()
    for planner in planners:
        component_id = planner.component_id
        if component_id in seen_components:
            raise ValueError(f"duplicate component id {component_id!r}")
        seen_components.add(component_id)
        component = Component(
            component_id,
            planner.version,
            tuple(planner.runtime_fields),
        )
        steps: list[Step] = []
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
    resources: Any,
    runtime: Any,
    plan: WorkflowPlan,
    *,
    output_directory: Path,
    configuration: RuntimeConfiguration | None = None,
    monitor: Any = None,
) -> Any:
    """Resolve instruction kinds, create services and run one plan."""
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
    services = resources.services(plan, resolved)
    try:
        return runtime.execute(
            plan,
            by_kind,
            services=services,
            configuration=resolved,
            monitor=monitor,
        )
    finally:
        resources.close(services)


__all__ = [
    "LayerContext", "build_model", "compile_model", "execute_plan",
    "transcribe_layers",
]
