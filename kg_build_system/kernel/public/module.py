"""The module protocol: compile a frozen build and execute its steps.

A module is the unit that turns a build into workflow steps and later executes
those steps. It has a stable identity, an implementation version and one
configuration type. The compiler and executor are created from it; they are
separate objects so a build never carries a live execution service.
"""
from __future__ import annotations

from typing import Any, ClassVar, Protocol


class ModuleCompiler(Protocol):
    """Compile a module against a build into a workflow contribution.

    ``context`` is a ``CompilationContext``. Compilation is async because a
    module may read external metadata or lower through an engine.

    Example:
    ```python
    from kg_build_system.kernel import (
        ModuleDefinition, ModuleReference, WorkflowContribution,
    )

    class EchoCompiler:
        async def compile(self, context):
            return WorkflowContribution(
                ModuleDefinition(ModuleReference(
                    "echo", "my_package.echo", "EchoModule", "1",
                )),
            )
    ```
    """

    async def compile(self, context: Any) -> Any:
        """Compile the module for one build context.

        Example:
            ```python
            contribution = await EchoCompiler().compile(context)
            ```
        """
        ...


class ModuleExecutor(Protocol):
    """Execute one step of a compiled module contract.

    ``handle`` receives an ``ExecutionContext``; ``handle_disrupted`` receives a
    ``DisruptedExecutionContext`` when an upstream input failed or was skipped.

    Example:
    ```python
    from kg_build_system.kernel import StepOutcome, StepStatus

    class EchoExecutor:
        def handle(self, context):
            return StepOutcome(
                context.step_id, context.module_id, StepStatus.SUCCEEDED,
            )

        def handle_disrupted(self, context):
            return StepOutcome(
                context.step_id, context.module_id, StepStatus.SKIPPED,
            )
    ```
    """

    def handle(self, context: Any) -> Any:
        """Execute one step and return its outcome.

        Example:
            ```python
            outcome = EchoExecutor().handle(context)
            ```
        """
        ...

    def handle_disrupted(self, context: Any) -> Any:
        """Report a step whose inputs failed or were skipped.

        Example:
            ```python
            outcome = EchoExecutor().handle_disrupted(context)
            ```
        """
        ...


class Module(Protocol):
    """A module declaration: identity, version, configuration and factories.

    ``ID`` is the module's stable identity and ``VERSION`` identifies the
    implementation that produced a build. ``CONFIGURATION_TYPE`` is the class
    the compiler context's ``configuration`` is an instance of.

    Example:
    ```python
    class EchoModule:
        ID = "echo"
        VERSION = "1"
        CONFIGURATION_TYPE = EchoConfiguration

        @classmethod
        async def create_compiler(cls, context):
            return EchoCompiler()

        @classmethod
        def create_executor(cls, context):
            return EchoExecutor()
    ```
    """

    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler:
        """Create the compiler for this module version.

        Example:
            ```python
            compiler = await EchoModule.create_compiler(context)
            ```
        """
        ...

    @classmethod
    def create_executor(cls, context: Any) -> ModuleExecutor:
        """Create the executor for this module version.

        Example:
            ```python
            executor = EchoModule.create_executor(context)
            ```
        """
        ...


__all__ = ["Module", "ModuleCompiler", "ModuleExecutor"]
