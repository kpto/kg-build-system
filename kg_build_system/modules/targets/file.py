"""File-output workflow module."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar
from ...compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, RuntimeFieldDefinition, WorkflowStep
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
from ...workflow.models import Artifact, DisruptedExecutionContext, ExecutionContext, StepOutcome, StepStatus, WorkflowArtifactRoles
from ..core import CoreArtifactRoles

@dataclass(frozen=True)
class FileModuleConfiguration(ModuleRegistrationConfiguration):
    relative_path: str

    def __post_init__(self) -> None:
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("FileModule output path must be relative to the build output directory")

@dataclass(frozen=True)
class FileModule(Module, ModuleRegistration[FileModuleConfiguration]):
    configuration: FileModuleConfiguration
    ID: ClassVar[str] = "file"; VERSION: ClassVar[str] = "1"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return cls(context.registration_configuration)
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return FileExecutor(context.runtime_configuration)
    async def compile(self, context: Any) -> ModuleCompilationResult:
        records=CollectionInputSlot(slot_id="file::write.records")
        step=WorkflowStep(step_id="file::write",module_id=self.ID,assembly_preference="deferred",inputs=(records,),outputs=(OutputSlot(slot_id="file::write.result",artifact_role=WorkflowArtifactRoles.published(self.ID, "write_result")),),payload={})
        definition=ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version=self.VERSION,priority=0,configuration={"relative_path":self.configuration.relative_path}),runtime_fields=(RuntimeFieldDefinition(key="relative_path",description="Optional runtime replacement for the relative output path.",required=False),))
        return ModuleCompilationResult(definition,(WorkflowStepDraft(step,{records.slot_id:lambda _input,output:CoreArtifactRoles.is_graph_records(output.artifact_role)} ),))

class FileExecutor(ModuleExecutor):
    def __init__(self, configuration: dict[str, Any]) -> None: self._configuration=configuration
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        step = context.step
        compiled=context.module.reference.configuration
        if not isinstance(compiled,dict) or not isinstance(compiled.get("relative_path"),str): raise RuntimeError("file module requires a compiled relative output path")
        relative_path=str(self._configuration.get("relative_path") or compiled["relative_path"])
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("FileModule output path must be relative to the build output directory")
        output = context.services.output_storage.child(PurePosixPath(relative_path))
        output.parent.mkdir(parents=True,exist_ok=True); nodes=edges=0
        with output.open("w",encoding="utf-8") as stream:
            for values in context.inputs.values():
                for item in values:
                    artifact = item.artifact
                    if artifact is None:
                        continue
                    identity=CoreArtifactRoles.graph_record_identity(artifact.role)
                    if identity is None: continue
                    result=context.services.duckdb.execute(f'SELECT * FROM "{str(artifact.value).replace(chr(34),chr(34)*2)}"'); columns=tuple(column[0] for column in result.description); kind,component=identity.kind,identity.component
                    while batch := result.fetchmany(1_000):
                        for row in batch:
                            record=dict(zip(columns,row,strict=True)); record.update(build_key=str(record["build_key"]),type=component,kind=kind); nodes+=kind=="node"; edges+=kind=="edge"; stream.write(json.dumps(record,sort_keys=True,default=str)+"\n")
        result={"nodes":nodes,"edges":edges,"location":str(output)}
        artifact_output = step.outputs[0]
        return StepOutcome(
            step.step_id,
            step.module_id,
            StepStatus.SUCCEEDED,
            (Artifact(artifact_output.slot_id, artifact_output.artifact_role, result),),
        )

    async def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        return await super().handle_disrupted(context)
