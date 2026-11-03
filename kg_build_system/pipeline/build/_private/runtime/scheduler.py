"""The static execution graph implied by a contract's connections."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from .....kernel import Publication
from ..contract import ContractStep, ContractWorkflow
from .identity import opening_identity, output_name, step_identity


@dataclass(frozen=True, slots=True)
class Schedule:
    """Steps indexed by the identities their openings and producers use."""

    steps: tuple[tuple[str, ContractStep], ...]
    identity_of: Mapping[tuple[str, str], str]
    output_owner: Mapping[str, str]
    publication_ids: tuple[str, ...]
    publishing_steps: tuple[str, ...]
    incoming: Mapping[str, tuple[str, ...]]

    def identity(self, module_id: str, step: ContractStep) -> str:
        """Return the whole-workflow identity of one step."""
        return self.identity_of[(module_id, step.name)]

    def sources(self, step_id: str, taken_name: str) -> tuple[str, ...]:
        """Return the output identities feeding one taken opening."""
        return self.incoming.get(opening_identity(step_id, taken_name), ())

    def is_ready(
        self, entry: tuple[str, ContractStep], completed: set[str],
    ) -> bool:
        """Return whether every producer of a step has completed."""
        module_id, step = entry
        identity = self.identity(module_id, step)
        return all(
            self.output_owner[source] in completed
            for taken in step.inputs
            for source in self.sources(identity, taken.name)
        )


def schedule(workflow: ContractWorkflow) -> Schedule:
    """Index a contract workflow by its generated identities."""
    steps = tuple(workflow.steps_by_module)
    identity_of = {
        (module_id, step.name): step_identity(module_id, step.name)
        for module_id, step in steps
    }
    output_owner = {
        opening_identity(identity_of[(module_id, step.name)], output_name(output)):
            identity_of[(module_id, step.name)]
        for module_id, step in steps for output in step.outputs
    }
    publication_ids = tuple(
        opening_identity(identity_of[(module_id, step.name)], output_name(output))
        for module_id, step in steps for output in step.outputs
        if isinstance(output, Publication)
    )
    publishing_steps = tuple(dict.fromkeys(
        identity_of[(module_id, step.name)]
        for module_id, step in steps
        if any(isinstance(output, Publication) for output in step.outputs)
    ))
    incoming: dict[str, list[str]] = defaultdict(list)
    for connection in workflow.connections:
        incoming[connection.input_id].append(connection.output_id)
    return Schedule(
        steps=steps,
        identity_of=identity_of,
        output_owner=output_owner,
        publication_ids=publication_ids,
        publishing_steps=publishing_steps,
        incoming={key: tuple(value) for key, value in incoming.items()},
    )


__all__ = ["Schedule", "schedule"]
