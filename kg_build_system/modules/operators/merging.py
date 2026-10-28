"""Workflow operator that merges compatible facts by graph identity."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, ClassVar

from ..._frozen_json import freeze_json
from ...workflow.models import (
    Artifact, DisruptedExecutionContext, ExecutionContext,
    ExecutorFactoryContext, Input, ModuleDefinition, ModuleReference, Output,
    StepOutcome, StepStatus, WorkflowContribution, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...topology.models import Edge, Node
from ...workflow.identity import output_name
from ...workflow.interfaces import ModuleExecutor
from ..core import CoreArtifactTypes, graph_record_components


@dataclass(frozen=True)
class MergeCompatibleFactsModuleConfiguration(ModuleRegistrationConfiguration):
    """``components=None`` merges every record component; a tuple restricts the
    operator to those component classes, leaving every other component's records
    untouched by this step.

    Merging folds same-key rows into one record (a ``min()`` per column), so it
    is only sound for components whose parallel same-key rows are meant to be one
    fact. Edge families that deliberately keep parallel facts stay outside the
    scope.
    """

    components: tuple[type[Node] | type[Edge[Any, Any]], ...] | None = None

    def __post_init__(self) -> None:
        if self.components is not None:
            values = tuple(
                _resolve_component(component) for component in self.components
            )
            for component in values:
                kind = getattr(component, "_component_declaration_kind", None)
                if (
                    not isinstance(component, type)
                    or kind not in {"node", "edge"}
                    or getattr(component, "_component_abstract", False)
                ):
                    raise TypeError(
                        "components must be concrete Node or Edge classes"
                    )
            object.__setattr__(self, "components", values)

    def to_json(self) -> Any:
        return {
            "components": (
                None if self.components is None
                else [
                    {
                        "module": component.__module__,
                        "qualname": component.__qualname__,
                    }
                    for component in self.components
                ]
            ),
        }


def _resolve_component(value: Any) -> Any:
    if isinstance(value, type):
        return value
    if isinstance(value, dict):
        module = importlib.import_module(str(value["module"]))
        component: Any = module
        for part in str(value["qualname"]).split("."):
            component = getattr(component, part)
        return component
    raise TypeError("components must be concrete Node or Edge classes")


_RECORDS_INPUT = "records"
_MERGED_OUTPUT = "merged"


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


@dataclass(frozen=True)
class MergeCompatibleFactsModule(Module):
    configuration: MergeCompatibleFactsModuleConfiguration
    ID: ClassVar[str] = "merge_compatible_facts"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[MergeCompatibleFactsModuleConfiguration]] = (
        MergeCompatibleFactsModuleConfiguration
    )

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return _Executor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        steps: list[WorkflowStep] = []
        instructions: dict[str, Any] = {}
        scope = self.configuration.components
        scope_names = None if scope is None else {
            component._component_name for component in scope
        }
        for component in graph_record_components(context.blueprint):
            if scope_names is not None and component.name not in scope_names:
                continue
            records_type = CoreArtifactTypes.graph_records(
                component.kind, component.name
            )
            fields = [prop.name for prop in component.properties]
            if component.kind == "edge":
                fields = ["source_build_key", "target_build_key", *fields]
            aggregates = [
                f'min("{_quote_identifier(name)}") AS "{_quote_identifier(name)}"'
                for name in fields
            ]
            select = ", ".join(['"build_key"', *aggregates])
            steps.append(WorkflowStep(
                inputs=(Input(records_type, _RECORDS_INPUT),),
                outputs=(Output(records_type, _MERGED_OUTPUT),),
                name=component.name,
            ))
            instructions[component.name] = {
                "relation": f"kg_normalised_{component.name.lower()}",
                "select": select,
            }

        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json(self.configuration.to_json()),
            )
        )
        return WorkflowContribution(
            definition, tuple(steps), freeze_json({"instructions": instructions}),
        )


class _Executor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instructions = context.variables["instructions"][context.step.name]
        if not isinstance(instructions, dict):
            raise ValueError("fact merging requires an object instruction")

        input_relation = next(
            (
                item.artifact.value
                for item in context.inputs[_RECORDS_INPUT]
                if item.artifact is not None
            ),
            None,
        )
        if input_relation is None:
            return StepOutcome(
                step_id=context.step_id,
                module_id=context.module_id,
                status=StepStatus.SUCCEEDED,
            )

        source = context.services.relations.reference(input_relation)
        relation = context.services.relations.materialize(
            str(instructions["relation"]),
            f'SELECT {instructions["select"]} FROM {source} GROUP BY "build_key"',
        )

        outputs = {output_name(given): given for given in context.step.outputs}
        artifact = Artifact(
            _MERGED_OUTPUT, outputs[_MERGED_OUTPUT].type, relation,
        )
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
