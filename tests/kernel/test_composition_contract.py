"""The composition contract: artifact matching, not producer identities."""
from __future__ import annotations

import unittest

from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    Input,
    Instruction,
    InstructionKind,
    Key,
    Publication,
    Step,
    StepId,
    Toolchain,
)

KIND = InstructionKind("test", "default")


class Producer:
    """Publish one artifact type under a distinct component."""

    version = "1"
    runtime_fields = ()

    def __init__(self, component: str, artifact: str) -> None:
        self.component_id = component
        self.artifact = artifact

    def plan(self, model: object, context: object) -> tuple[Step, ...]:
        del model, context
        return (
            Step(
                self.component_id,
                "publish",
                (),
                (
                    Publication(
                        ArtifactType.of("ingest", self.artifact),
                        Key((self.artifact,)),
                    ),
                ),
                Instruction(KIND, None),
            ),
        )


class Consumer:
    """Read a type or pattern; the declaration never names a producer."""

    component_id = "consumer"
    version = "1"
    runtime_fields = ()

    def __init__(self, pattern: ArtifactPattern) -> None:
        self.pattern = pattern

    def plan(self, model: object, context: object) -> tuple[Step, ...]:
        del model, context
        return (
            Step(
                self.component_id,
                "read",
                (Input(self.pattern, None, "records"),),
                (
                    Publication(
                        ArtifactType.of("graph", "result"),
                        Key(("result",)),
                    ),
                ),
                Instruction(KIND, None),
            ),
        )


def compile_plan(*planners: object):
    return Toolchain(
        languages=(),
        linker=object(),
        planners=tuple(planners),
        executors=(),
        runtime=None,
    ).compile(object())


def consumer_connections(plan, consumer: Consumer) -> int:
    target = StepId(consumer.component_id, "read")
    return sum(1 for connection in plan.connections if connection.input.step == target)


class CompositionContractTests(unittest.TestCase):
    def test_a_pattern_consumer_sees_every_matching_producer(self) -> None:
        consumer = Consumer(ArtifactPattern.of("ingest", "**"))
        plan = compile_plan(
            Producer("a", "a"),
            Producer("b", "b"),
            consumer,
        )

        self.assertEqual(consumer_connections(plan, consumer), 2)

    def test_adding_a_producer_leaves_the_consumer_declaration_unchanged(self) -> None:
        consumer = Consumer(ArtifactPattern.of("ingest", "**"))
        before = compile_plan(Producer("a", "a"), consumer)
        after = compile_plan(Producer("a", "a"), Producer("b", "b"), consumer)

        self.assertEqual(consumer_connections(before, consumer), 1)
        self.assertEqual(consumer_connections(after, consumer), 2)

    def test_an_exact_input_narrows_eligibility(self) -> None:
        consumer = Consumer(ArtifactPattern.of("ingest", "a"))
        plan = compile_plan(
            Producer("a", "a"),
            Producer("b", "b"),
            consumer,
        )

        self.assertEqual(consumer_connections(plan, consumer), 1)

    def test_two_producers_of_one_type_are_refused(self) -> None:
        consumer = Consumer(ArtifactPattern.of("ingest", "a"))

        with self.assertRaisesRegex(ValueError, "could be fed by"):
            compile_plan(
                Producer("a", "a"),
                Producer("b", "a"),
                consumer,
            )


if __name__ == "__main__":
    unittest.main()
