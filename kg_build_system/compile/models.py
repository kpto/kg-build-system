"""Immutable workflow and executable build-contract models."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
    PlainValidator,
    model_validator,
)

from .ir import BuildBlueprint, SourceDefinition


class IRModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ModuleReference(IRModel):
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    import_module: str = Field(min_length=1)
    class_qualname: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    priority: int = Field(ge=0)
    configuration: JsonValue | None = None


class RuntimeFieldDefinition(IRModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ModuleDefinition(IRModel):
    reference: ModuleReference
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = ()


class ArtifactRole(IRModel):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class OutputSlot(IRModel):
    slot_id: str = Field(min_length=1)
    artifact_role: ArtifactRole


class SingleInputSlot(IRModel):
    kind: Literal["single"] = "single"
    slot_id: str = Field(min_length=1)


class CollectionInputSlot(IRModel):
    kind: Literal["collection"] = "collection"
    slot_id: str = Field(min_length=1)


InputSlot = Annotated[
    SingleInputSlot | CollectionInputSlot,
    Field(discriminator="kind"),
]


class WorkflowStep(IRModel):
    step_id: str = Field(min_length=1)
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    assembly_preference: Literal["eager", "deferred"] = "eager"
    inputs: tuple[InputSlot, ...] = ()
    outputs: tuple[OutputSlot, ...] = ()
    payload: JsonValue | None = None


class Connection(IRModel):
    input_slot_id: str = Field(min_length=1)
    output_slot_id: str = Field(min_length=1)


class WorkflowDefinition(IRModel):
    modules: tuple[ModuleDefinition, ...] = Field(min_length=1)
    steps: tuple[WorkflowStep, ...] = Field(min_length=1)
    connections: tuple[Connection, ...] = ()

    @model_validator(mode="after")
    def validate_workflow(self) -> Self:
        module_ids = tuple(module.reference.module_id for module in self.modules)
        if len(module_ids) != len(set(module_ids)):
            raise ValueError("workflow module IDs must be unique")

        step_ids = tuple(step.step_id for step in self.steps)
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("workflow step IDs must be unique")
        if any(step.module_id not in module_ids for step in self.steps):
            raise ValueError("workflow step references an unknown module")

        inputs = {slot.slot_id: slot for step in self.steps for slot in step.inputs}
        outputs = {slot.slot_id for step in self.steps for slot in step.outputs}
        input_count = sum(len(step.inputs) for step in self.steps)
        output_count = sum(len(step.outputs) for step in self.steps)
        if len(inputs) != input_count:
            raise ValueError("workflow input slot IDs must be unique")
        if len(outputs) != output_count:
            raise ValueError("workflow output slot IDs must be unique")

        connection_counts: dict[str, int] = {}
        connection_pairs: set[tuple[str, str]] = set()
        for connection in self.connections:
            if connection.input_slot_id not in inputs:
                raise ValueError("workflow connection references an unknown input slot")
            if connection.output_slot_id not in outputs:
                raise ValueError("workflow connection references an unknown output slot")
            pair = (connection.input_slot_id, connection.output_slot_id)
            if pair in connection_pairs:
                raise ValueError("workflow connections must be unique")
            connection_pairs.add(pair)
            connection_counts[connection.input_slot_id] = (
                connection_counts.get(connection.input_slot_id, 0) + 1
            )

        for slot_id, slot in inputs.items():
            count = connection_counts.get(slot_id, 0)
            if count == 0:
                raise ValueError(f"input {slot_id!r} requires at least one connection")
            if isinstance(slot, SingleInputSlot) and count != 1:
                raise ValueError(f"single input {slot_id!r} requires exactly one connection")

        output_owners = {
            slot.slot_id: step.step_id for step in self.steps for slot in step.outputs
        }
        input_owners = {
            slot.slot_id: step.step_id for step in self.steps for slot in step.inputs
        }
        dependents: dict[str, set[str]] = {step.step_id: set() for step in self.steps}
        indegrees = {step.step_id: 0 for step in self.steps}
        for connection in self.connections:
            producer = output_owners[connection.output_slot_id]
            consumer = input_owners[connection.input_slot_id]
            if consumer not in dependents[producer]:
                dependents[producer].add(consumer)
                indegrees[consumer] += 1

        ready = [step_id for step_id, degree in indegrees.items() if degree == 0]
        visited = 0
        while ready:
            producer = ready.pop()
            visited += 1
            for consumer in dependents[producer]:
                indegrees[consumer] -= 1
                if indegrees[consumer] == 0:
                    ready.append(consumer)
        if visited != len(self.steps):
            raise ValueError("workflow dependency graph contains a cycle")
        return self


class BuildSettings(IRModel):
    duckdb_threads: int | None = Field(default=None, ge=1)


class SourceOverride(IRModel):
    table: str = Field(min_length=1)
    original: SourceDefinition | None = None
    override: SourceDefinition


class BuildOverrides(IRModel):
    sources: tuple[SourceOverride, ...] = ()


def _decode_blueprint(value: Any) -> BuildBlueprint:
    return BuildBlueprint.model_validate(value)


def _encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    return value.model_dump(mode="json")


BlueprintField = Annotated[
    BuildBlueprint,
    PlainValidator(_decode_blueprint),
    PlainSerializer(_encode_blueprint, return_type=dict[str, Any]),
]


class BuildContract(IRModel):
    """A complete executable workflow with its resolved declaration graph."""

    blueprint: BlueprintField
    blueprint_fingerprint: str = Field(min_length=1)
    sources: tuple[SourceDefinition, ...] = Field(min_length=1)
    settings: BuildSettings = Field(default_factory=BuildSettings)
    overrides: BuildOverrides = Field(default_factory=BuildOverrides)
    workflow_fingerprint: str = Field(min_length=1)
    workflow: WorkflowDefinition
