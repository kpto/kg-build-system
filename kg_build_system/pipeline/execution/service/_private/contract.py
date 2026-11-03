"""Convert a workflow contract into the build's executable model.

The build reads structure from the contract and execution facts from each step's
instruction. It does not read SQL, Python coordinates or target configuration
from the contract: those live in ``step.instruction.payload``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .....kernel import (
    ArtifactType,
    Connection,
    Given,
    ModuleDefinition,
    ModuleReference,
    Output,
    Publication,
    RuntimeFieldDefinition,
    TakenInput,
)
from ...model.internal.contract import (
    BuildContract,
    ContractStep,
    ContractWorkflow,
    Instruction,
)


def _read(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _items(value: object) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return (value,)


def _artifact_type(value: object) -> ArtifactType:
    if isinstance(value, ArtifactType):
        return value
    namespace = _read(value, "namespace")
    name = _read(value, "name")
    if not isinstance(namespace, str) or not isinstance(name, str):
        raise TypeError("an artifact type requires namespace and name strings")
    return ArtifactType(namespace, name)


def _given(value: object) -> Given:
    if isinstance(value, (Output, Publication)):
        return value
    artifact_type = _artifact_type(_read(value, "type"))
    name = _read(value, "name")
    if name is not None and not isinstance(name, str):
        raise TypeError("an output name must be a string or None")
    kind = _read(value, "kind")
    if kind == "publication" or isinstance(value, Publication):
        return Publication(artifact_type, name)
    return Output(artifact_type, name)


def _taken_input(value: object) -> TakenInput:
    if isinstance(value, TakenInput):
        return value
    artifact_type = _artifact_type(_read(value, "type"))
    name = _read(value, "name")
    input_name = _read(value, "input_name", name)
    if not isinstance(name, str) or not name:
        raise TypeError("a taken input requires a non-empty opening name")
    if not isinstance(input_name, str) or not input_name:
        raise TypeError("a taken input requires a non-empty input name")
    return TakenInput(artifact_type, name, input_name)


def _module_reference(value: object) -> ModuleReference:
    if isinstance(value, ModuleReference):
        return value
    module_id = _read(value, "module_id")
    import_module = _read(value, "import_module")
    class_qualname = _read(value, "class_qualname")
    implementation_version = _read(value, "implementation_version")
    for field_name, field_value in (
        ("module_id", module_id),
        ("import_module", import_module),
        ("class_qualname", class_qualname),
        ("implementation_version", implementation_version),
    ):
        if not isinstance(field_value, str) or not field_value:
            raise TypeError(f"a module reference requires {field_name}")
    return ModuleReference(
        module_id,
        import_module,
        class_qualname,
        implementation_version,
        _read(value, "configuration"),
    )


def _runtime_field(value: object) -> RuntimeFieldDefinition:
    if isinstance(value, RuntimeFieldDefinition):
        return value
    key = _read(value, "key")
    description = _read(value, "description", "")
    if not isinstance(key, str) or not key:
        raise TypeError("a runtime field requires a key")
    if not isinstance(description, str):
        raise TypeError("a runtime field description must be a string")
    return RuntimeFieldDefinition(
        key,
        description,
        bool(_read(value, "required", True)),
        _read(value, "value_type", "string"),
        bool(_read(value, "secret", False)),
    )


def _module_definition(contribution: object) -> ModuleDefinition:
    """Convert a contribution's module DTO into the runtime definition.

    ``ContributionDTO.module`` is a ``ModuleDefinitionDTO``; the build needs the
    kernel ``ModuleDefinition`` because the execution context carries kernel
    values. A contribution that already carries the kernel value is accepted
    unchanged for the migration path.
    """
    module = _read(contribution, "module")
    if isinstance(module, ModuleDefinition):
        return module
    if module is not None:
        reference_value = _read(module, "reference")
        if reference_value is not None:
            return ModuleDefinition(
                _module_reference(reference_value),
                tuple(
                    _runtime_field(field)
                    for field in _items(_read(module, "runtime_fields"))
                ),
            )
    reference_value = _read(contribution, "reference")
    if reference_value is None:
        raise TypeError("a contribution requires a module definition")
    return ModuleDefinition(
        _module_reference(reference_value),
        tuple(
            _runtime_field(field)
            for field in _items(_read(contribution, "runtime_fields"))
        ),
    )


def _instruction(value: object) -> Instruction | None:
    if value is None:
        return None
    kind = _read(value, "kind")
    payload = _read(value, "payload")
    if not isinstance(kind, str) or not kind:
        raise TypeError("a step instruction requires a non-empty kind")
    return Instruction(kind, payload)


def _contract_workflow(contract: object) -> ContractWorkflow:
    # WorkflowContractDTO carries contributions and connections at its root.
    # The wrapper fallback keeps the earlier in-progress contract readable while
    # the composition root migrates; the DTO path is the one the build states.
    workflow = (
        contract
        if _read(contract, "contributions") is not None
        else _read(contract, "workflow", contract)
    )
    steps: list[ContractStep] = []
    for contribution in _items(_read(workflow, "contributions")):
        module = _module_definition(contribution)
        variables = _read(contribution, "variables")
        for step in _items(_read(contribution, "steps")):
            name = _read(step, "name")
            if not isinstance(name, str) or not name:
                raise TypeError("a contract step requires a non-empty name")
            steps.append(ContractStep(
                module_id=module.reference.module_id,
                module=module,
                name=name,
                inputs=tuple(
                    _taken_input(item)
                    for item in _items(_read(step, "inputs"))
                ),
                outputs=tuple(
                    _given(item) for item in _items(_read(step, "outputs"))
                ),
                instruction=_instruction(_read(step, "instruction")),
                variables=variables,
            ))
    connections = tuple(
        Connection(
            str(_read(item, "input_id")),
            str(_read(item, "output_id")),
        )
        for item in _items(_read(workflow, "connections"))
    )
    return ContractWorkflow(tuple(steps), connections)


def read_contract(contract: object) -> BuildContract:
    """Read a workflow contract into the build's executable model.

    The canonical value is ``WorkflowContractDTO``: its contributions carry a
    ``ModuleDefinitionDTO`` and each step carries an ``InstructionDTO``. A step
    with no instruction keeps ``instruction=None`` only so the temporary module
    adapter can run an earlier contract during migration.
    """
    fingerprint = _read(
        contract,
        "workflow_fingerprint",
        _read(contract, "fingerprint", ""),
    )
    return BuildContract(
        workflow=_contract_workflow(contract),
        fingerprint=str(fingerprint) if fingerprint is not None else "",
        provenance=_read(contract, "provenance"),
    )


__all__ = ["read_contract"]
