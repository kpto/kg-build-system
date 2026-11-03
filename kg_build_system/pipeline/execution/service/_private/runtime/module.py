"""Execute a step through the module that contributed it.

The build does not know target names. A step's instruction kind selects the
generic executors (``sql``, ``python``) or falls through to the module named by
the contract contribution. That module creates its executor from the step
context and owns the meaning of its instruction payload.
"""
from __future__ import annotations

import importlib
from dataclasses import replace
from typing import Any, cast

from kg_build_system.kernel.model.internal.json import freeze_json

from ......kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
)
from ....model.internal.contract import ContractStep, Instruction
from ..instructions import InstructionExecutor, UnknownInstructionKind
from .outcome import skipped

LEGACY_MODULE_KIND = "module"


def legacy_instruction(step: ContractStep) -> Instruction:
    """The synthetic kind under which a step without an instruction runs."""
    return Instruction(LEGACY_MODULE_KIND, None)


def _load_class(module_name: str, qualname: str) -> type[Any]:
    value: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _module_variables(
    context: ExecutionContext | DisruptedExecutionContext,
    instruction: Instruction,
) -> Any:
    """Carry the contract instruction payload into the module executor.

    A module executor receives its instruction through the execution context.
    New contract steps carry it under the running step's name; a step without an
    instruction keeps the variables supplied by an earlier contract.
    """
    if instruction.payload is None:
        return context.variables
    return freeze_json({
        "instructions": {context.step.name: instruction.payload},
    })


def _create_executor(
    module_class: type[Any],
    context: ExecutionContext | DisruptedExecutionContext,
    instruction: Instruction,
) -> Any | None:
    factory_context = ExecutorFactoryContext(
        context.module,
        _module_variables(context, instruction),
        context.runtime_configuration,
    )
    executor_factory = getattr(module_class, "executor", None)
    if callable(executor_factory):
        return executor_factory(factory_context)
    legacy_factory = getattr(module_class, "create_executor", None)
    if callable(legacy_factory):
        return legacy_factory(factory_context)
    return None


class ContractModuleInstructionExecutor(InstructionExecutor):
    """Run one step through the executor its contract module supplies."""

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Resolve the contribution module, create it and hand it the step."""
        reference = context.module.reference
        module_class = _load_class(
            reference.import_module, reference.class_qualname,
        )
        module_id = getattr(module_class, "ID", None)
        if module_id is not None and module_id != reference.module_id:
            raise RuntimeError(
                f"module import does not provide {reference.module_id!r}"
            )
        version = getattr(module_class, "VERSION", None)
        if (
            version is not None
            and str(version) != reference.implementation_version
        ):
            raise RuntimeError(
                f"module {reference.module_id!r} implementation version "
                f"{version!r} does not match compiled version "
                f"{reference.implementation_version!r}"
            )
        executor = _create_executor(module_class, context, instruction)
        if executor is None:
            raise UnknownInstructionKind(instruction.kind)
        step_context = replace(
            context,
            variables=_module_variables(context, instruction),
        )
        if isinstance(context, DisruptedExecutionContext):
            handler = getattr(executor, "handle_disrupted", None)
            if callable(handler):
                return cast(StepOutcome, handler(step_context))
            return skipped(context)
        return executor.handle(step_context)


__all__ = [
    "ContractModuleInstructionExecutor",
    "LEGACY_MODULE_KIND",
    "legacy_instruction",
]
