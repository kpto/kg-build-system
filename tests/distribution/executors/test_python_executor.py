from __future__ import annotations

import unittest

from kg_build_system.distribution.modules.python import PythonExecutor
from kg_build_system.kernel import (
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    Output,
    ResourceView,
    Step,
    StepStatus,
)

VALUE = ArtifactType("python", "value")


def produce(context: ExecutionContext, instruction: Instruction) -> int:
    """A module-level target addressed by module and qualname."""
    return 42


def _step() -> Step:
    return Step(
        "python",
        "produce",
        (),
        (Output(VALUE, "value"),),
        Instruction(
            ("python", "cpython"),
            {"module": __name__, "qualname": "produce"},
        ),
    )


class PythonExecutorTests(unittest.TestCase):
    def test_a_module_level_function_returns_an_artifact(self) -> None:
        step = _step()
        context = ExecutionContext(
            step=step,
            step_id="python.produce",
            component="python",
            runtime_configuration={},
            inputs={},
            resources=ResourceView({}),
            logger=None,
        )

        outcome = PythonExecutor().execute(context, step.instruction)

        self.assertEqual(outcome.status, StepStatus.SUCCEEDED)
        self.assertEqual(len(outcome.artifacts), 1)
        self.assertEqual(outcome.artifacts[0].value, 42)

    def test_a_disrupted_context_is_skipped(self) -> None:
        step = _step()
        context = DisruptedExecutionContext(
            step=step,
            step_id="python.produce",
            component="python",
            runtime_configuration={},
            inputs={},
            disruptions=(),
            resources=ResourceView({}),
            logger=None,
        )

        outcome = PythonExecutor().execute(context, step.instruction)

        self.assertEqual(outcome.status, StepStatus.SKIPPED)


if __name__ == "__main__":
    unittest.main()
