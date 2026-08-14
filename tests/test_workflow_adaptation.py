from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from kg_build_system.compile.blueprint import BuildBlueprint
from kg_build_system.table.dto import SourceDTO as SourceDefinition
from kg_build_system.compile.contracts import BuildContract
from kg_build_system.workflow import BuildRuntime, build
from kg_build_system.workflow.interfaces import (
    CompilationContext, Module, ModuleCompilationResult, ModuleCompiler,
    ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration,
)
from kg_build_system.workflow.models import (
    Artifact, ArtifactRole, CollectionInputSlot, Connection,
    DisruptedExecutionContext, ExecutionContext, ExecutorFactoryContext,
    ModuleDefinition, ModuleReference, OutputSlot, RuntimeFieldDefinition,
    SingleInputSlot, StepOutcome, StepStatus, WorkflowArtifactRoles,
    WorkflowDefinition, WorkflowStep,
)
from kg_build_system.workflow.validation import validate_workflow


@dataclass(frozen=True)
class RecoveryConfiguration(ModuleRegistrationConfiguration):
    pass


@dataclass(frozen=True)
class RecoveryModule(Module, ModuleRegistration[RecoveryConfiguration]):
    configuration: RecoveryConfiguration = field(
        default_factory=RecoveryConfiguration,
    )
    ID: ClassVar[str] = "test_recovery"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.registration_configuration)

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return RecoveryExecutor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> ModuleCompilationResult:
        raise NotImplementedError


class RecoveryExecutor(ModuleExecutor):
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        if context.step.payload == {"action": "fail"}:
            raise RuntimeError("intentional failure")
        return StepOutcome(
            context.step.step_id, context.step.module_id, StepStatus.SUCCEEDED,
        )

    async def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        output = context.step.outputs[0]
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.WARNING,
            (Artifact(output.slot_id, output.artifact_role, {"recovered": True}),),
        )


def _module_definition(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> ModuleDefinition:
    return ModuleDefinition(
        reference=ModuleReference(
            module_id=RecoveryModule.ID,
            import_module=RecoveryModule.__module__,
            class_qualname=RecoveryModule.__qualname__,
            implementation_version=version,
            priority=0,
        ),
        runtime_fields=runtime_fields,
    )


def _contract(
    *, version: str = "1",
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = (),
) -> BuildContract:
    private_role = ArtifactRole(namespace="test_recovery", name="failed")
    published_role = WorkflowArtifactRoles.published(
        RecoveryModule.ID, "report",
    )
    failing = WorkflowStep(
        step_id="test_recovery::fail",
        module_id=RecoveryModule.ID,
        outputs=(OutputSlot(slot_id="test_recovery::fail.output", artifact_role=private_role),),
        payload={"action": "fail"},
    )
    recovery_input = SingleInputSlot(slot_id="test_recovery::recover.input")
    recovering = WorkflowStep(
        step_id="test_recovery::recover",
        module_id=RecoveryModule.ID,
        inputs=(recovery_input,),
        outputs=(OutputSlot(slot_id="test_recovery::recover.output", artifact_role=published_role),),
    )
    source = SourceDefinition(
        symbol_id="table:test", table="test", location="unused.json",
        format="json",
    )
    blueprint = BuildBlueprint(
        structs=(), tables=(), components=(), projections=(), bindings=(),
        sources=(source,),
    )
    workflow = WorkflowDefinition(
        modules=(_module_definition(version=version, runtime_fields=runtime_fields),),
        steps=(failing, recovering),
        connections=(Connection(
            input_slot_id=recovery_input.slot_id,
            output_slot_id=failing.outputs[0].slot_id,
        ),),
    )
    return BuildContract(
        blueprint=blueprint,
        blueprint_fingerprint="blueprint",
        sources=(source,),
        workflow_fingerprint="workflow",
        workflow=workflow,
    )


class WorkflowDefinitionTests(unittest.TestCase):
    def test_rejects_an_unconnected_collection_input(self) -> None:
        module = _module_definition()
        step = WorkflowStep(
            step_id="test_recovery::consumer",
            module_id=RecoveryModule.ID,
            inputs=(CollectionInputSlot(slot_id="test_recovery::consumer.inputs"),),
        )
        workflow = WorkflowDefinition(modules=(module,), steps=(step,))
        with self.assertRaisesRegex(ValueError, "requires at least one connection"):
            validate_workflow(workflow)

    def test_rejects_a_dependency_cycle_before_execution(self) -> None:
        role = ArtifactRole(namespace="test_recovery", name="value")
        first = WorkflowStep(
            step_id="test_recovery::first",
            module_id=RecoveryModule.ID,
            inputs=(SingleInputSlot(slot_id="test_recovery::first.input"),),
            outputs=(OutputSlot(slot_id="test_recovery::first.output", artifact_role=role),),
        )
        second = WorkflowStep(
            step_id="test_recovery::second",
            module_id=RecoveryModule.ID,
            inputs=(SingleInputSlot(slot_id="test_recovery::second.input"),),
            outputs=(OutputSlot(slot_id="test_recovery::second.output", artifact_role=role),),
        )
        workflow = WorkflowDefinition(
            modules=(_module_definition(),),
            steps=(first, second),
            connections=(
                Connection(
                    input_slot_id=first.inputs[0].slot_id,
                    output_slot_id=second.outputs[0].slot_id,
                ),
                Connection(
                    input_slot_id=second.inputs[0].slot_id,
                    output_slot_id=first.outputs[0].slot_id,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "contains a cycle"):
            validate_workflow(workflow)


class WorkflowRuntimeTests(unittest.TestCase):
    def test_successful_disrupted_handler_recovers_upstream_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = build(_contract(), output_directory=Path(directory))
        self.assertTrue(report.succeeded)
        self.assertEqual(len(report.recovered_failures), 1)
        self.assertEqual(report.unresolved_failures, ())
        self.assertEqual(report.published_artifacts[0].value, {"recovered": True})

    def test_rejects_an_incompatible_runtime_module_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "does not match compiled version"):
                build(
                    _contract(version="2"), output_directory=Path(directory),
                )

    def test_validates_runtime_configuration_types(self) -> None:
        runtime_field = RuntimeFieldDefinition(
            key="attempts", description="Number of attempts.",
            value_type="integer",
        )
        runtime = BuildRuntime(module_configuration={
            RecoveryModule.ID: {"attempts": "three"},
        })
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "invalid runtime configuration"):
                build(
                    _contract(runtime_fields=(runtime_field,)), runtime,
                    output_directory=Path(directory),
                )


if __name__ == "__main__":
    unittest.main()
