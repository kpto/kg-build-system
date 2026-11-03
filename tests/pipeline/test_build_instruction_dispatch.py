from __future__ import annotations

import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from kg_build_system.kernel import StepOutcome, StepStatus
from kg_build_system.pipeline.build._private.contract import (
    Instruction,
    read_contract,
)
from kg_build_system.pipeline.build._private.instructions import (
    InstructionDispatcher,
    UnknownInstructionKind,
)


@dataclass(frozen=True)
class _FakeInstruction:
    kind: str
    payload: Any = None


@dataclass(frozen=True)
class _FakeStep:
    name: str
    instruction: _FakeInstruction


@dataclass(frozen=True)
class _FakeContribution:
    reference: Any
    steps: tuple[_FakeStep, ...]


@dataclass(frozen=True)
class _FakeWorkflow:
    contributions: tuple[_FakeContribution, ...]
    connections: tuple[Any, ...] = ()


@dataclass(frozen=True)
class _FakeContract:
    workflow: _FakeWorkflow
    workflow_fingerprint: str = "fake-fingerprint"
    provenance: Any = None


class _RecordingExecutor:
    def __init__(self, module_id: str, step_id: str) -> None:
        self._module_id = module_id
        self._step_id = step_id
        self.calls: list[tuple[Any, Instruction]] = []

    def execute(self, context: Any, instruction: Instruction) -> StepOutcome:
        self.calls.append((context, instruction))
        return StepOutcome(
            step_id=self._step_id,
            module_id=self._module_id,
            status=StepStatus.SUCCEEDED,
        )


def _contract() -> _FakeContract:
    reference = SimpleNamespace(
        module_id="fake_module",
        import_module="fake.module",
        class_qualname="FakeModule",
        implementation_version="1",
        configuration=None,
    )
    return _FakeContract(_FakeWorkflow((
        _FakeContribution(reference, (
            _FakeStep("alpha", _FakeInstruction("alpha", {"value": 1})),
            _FakeStep("beta", _FakeInstruction("beta", {"value": 2})),
        )),
    )))


class InstructionDispatchTests(unittest.TestCase):
    def test_a_step_dispatches_to_the_executor_for_its_kind(self) -> None:
        contract = _contract()
        steps = read_contract(contract).workflow.steps
        alpha = _RecordingExecutor("fake_module", "fake_module::alpha")
        beta = _RecordingExecutor("fake_module", "fake_module::beta")
        dispatcher = InstructionDispatcher({"alpha": alpha, "beta": beta})
        context: Any = object()

        first = steps[0].instruction
        second = steps[1].instruction
        assert first is not None
        assert second is not None
        dispatcher.execute(context, first)
        dispatcher.execute(context, second)

        self.assertEqual(len(alpha.calls), 1)
        self.assertEqual(alpha.calls[0][1].kind, "alpha")
        self.assertEqual(alpha.calls[0][1].payload, {"value": 1})
        self.assertEqual(len(beta.calls), 1)
        self.assertEqual(beta.calls[0][1].kind, "beta")
        self.assertEqual(beta.calls[0][1].payload, {"value": 2})

    def test_an_unknown_kind_is_refused_by_type(self) -> None:
        dispatcher = InstructionDispatcher({
            "known": _RecordingExecutor("fake_module", "fake_module::known"),
        })
        instruction = Instruction("unknown", {"value": 3})
        context: Any = object()

        with self.assertRaises(UnknownInstructionKind) as caught:
            dispatcher.execute(context, instruction)

        self.assertEqual(caught.exception.kind, "unknown")


if __name__ == "__main__":
    unittest.main()
