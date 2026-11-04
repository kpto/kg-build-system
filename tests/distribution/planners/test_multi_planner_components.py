from __future__ import annotations

import unittest
from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import (
    Instruction,
    InstructionKind,
    PlanContext,
    RuntimeField,
    Step,
    Toolchain,
)


class _FakeLinker:
    def link(self, languages: Any, namespace: Any) -> object:
        return object()


class _StepPlanner:
    def __init__(
        self,
        name: str,
        *,
        component_id: str = "shared",
        version: str = "1",
        runtime_fields: tuple[RuntimeField, ...] = (),
    ) -> None:
        self.name = name
        self.component_id = component_id
        self.version = version
        self.runtime_fields = runtime_fields

    def plan(self, model: Any, context: PlanContext) -> Sequence[Step]:
        return (
            Step(
                component=self.component_id,
                name=self.name,
                inputs=(),
                outputs=(),
                instruction=Instruction(InstructionKind("noop", "default"), {}),
            ),
        )


class MultiPlannerComponentTests(unittest.TestCase):
    def test_planners_for_one_component_must_agree_on_version(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            planners=(
                _StepPlanner("first", version="1"),
                _StepPlanner("second", version="2"),
            ),
        )

        with self.assertRaisesRegex(ValueError, "disagree on version"):
            toolchain.compile(object())

    def test_planners_for_one_component_are_merged(self) -> None:
        toolchain: Toolchain[object] = Toolchain(
            languages=(),
            linker=_FakeLinker(),
            planners=(
                _StepPlanner("first", version="1"),
                _StepPlanner("second", version="1"),
            ),
        )

        plan = toolchain.compile(object())

        self.assertEqual([component.id for component in plan.components], ["shared"])
        self.assertEqual(
            [(step.component, step.name) for step in plan.steps],
            [("shared", "first"), ("shared", "second")],
        )


if __name__ == "__main__":
    unittest.main()
