"""File-output workflow module."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar
from ..compile.models import ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference, OutputSlot, RuntimeFieldDefinition, WorkflowStep
from ..workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, ModuleRegistration, ModuleRegistrationConfiguration, WorkflowStepDraft
from ..workflow.models import Artifact, ModuleExecutionContext, StepOutcome, StepStatus

@dataclass(frozen=True)
class FileModuleConfiguration(ModuleRegistrationConfiguration):
    location: str

@dataclass(frozen=True)
class FileModule(Module, ModuleRegistration[FileModuleConfiguration]):
    configuration: FileModuleConfiguration
    ID: ClassVar[str] = "file"; VERSION: ClassVar[str] = "1"
    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler: return context.registration
    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor: return FileExecutor(context.runtime_configuration)
    async def compile(self, context: Any) -> ModuleCompilationResult:
        records=CollectionInputSlot(slot_id="file::write.records"); diagnostics=CollectionInputSlot(slot_id="file::write.diagnostics")
        step=WorkflowStep(step_id="file::write",module_id=self.ID,assembly_preference="deferred",inputs=(records,diagnostics),outputs=(OutputSlot(slot_id="file::write.result",artifact_role=ArtifactRole(namespace="file",name="result")),),payload={})
        definition=ModuleDefinition(reference=ModuleReference(module_id=self.ID,import_module=type(self).__module__,class_qualname=type(self).__qualname__,implementation_version=self.VERSION,priority=0,configuration={"location":self.configuration.location}),runtime_fields=(RuntimeFieldDefinition(key="output_location",description="Optional runtime replacement for the output location.",required=False),))
        return ModuleCompilationResult(definition,(WorkflowStepDraft(step,{records.slot_id:lambda _input,output:output.artifact_role.namespace=="core" and output.artifact_role.name.startswith("graph.records."),diagnostics.slot_id:lambda _input,output:output.artifact_role.namespace=="core" and output.artifact_role.name.startswith("diagnostic.")} ),))

class FileExecutor:
    def __init__(self, configuration: dict[str, Any]) -> None: self._configuration=configuration
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        compiled=context.module.reference.configuration
        if not isinstance(compiled,dict) or not isinstance(compiled.get("location"),str): raise RuntimeError("file module requires a compiled output location")
        location=str(self._configuration.get("output_location") or compiled["location"])
        failures=[diagnostic.message for values in context.inputs.values() for item in values if item.role.name.startswith("diagnostic.") for diagnostic in item.value if diagnostic.severity == "error"]
        if failures: raise ValueError("graph normalisation failed: "+"; ".join(failures))
        output=Path(location); output.parent.mkdir(parents=True,exist_ok=True); connection=context.services["duckdb"]; nodes=edges=0
        with output.open("w",encoding="utf-8") as stream:
            for values in context.inputs.values():
                for artifact in values:
                    if not artifact.role.name.startswith("graph.records."): continue
                    result=connection.execute(f'SELECT * FROM "{artifact.value}"'); columns=tuple(column[0] for column in result.description); _,_,kind,component=artifact.role.name.split(".",3)
                    for row in result.fetchall():
                        record=dict(zip(columns,row,strict=True)); record.update(build_key=str(record["build_key"]),type=component,kind=kind); nodes+=kind=="node"; edges+=kind=="edge"; stream.write(json.dumps(record,sort_keys=True,default=str)+"\n")
        manifest=output.with_suffix(output.suffix+".manifest.json"); manifest.write_text(json.dumps({"nodes":nodes,"edges":edges,"blueprint_fingerprint":context.contract.blueprint_fingerprint,"workflow_fingerprint":context.contract.workflow_fingerprint},sort_keys=True),encoding="utf-8")
        result={"nodes":nodes,"edges":edges,"location":str(output),"manifest":str(manifest)}
        artifact_output = step.outputs[0]
        return StepOutcome(
            step.step_id,
            step.module_id,
            StepStatus.SUCCEEDED,
            (Artifact(artifact_output.slot_id, artifact_output.artifact_role, result),),
            metrics={"graph.nodes": nodes, "graph.edges": edges},
            result=result,
        )
