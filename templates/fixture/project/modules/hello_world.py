"""Hello-world input adapter: one planner and one executor.

An adapter decodes a physical input into the relation the declarations already
describe. This example has no file to decode: it supplies one relation with one
row so the planner/executor boundary is visible. A real adapter replaces the
literal ``SELECT`` with its reader and preserves the source's schema, null
assumptions, grain and identity; it decodes and casts only.
"""

from collections.abc import Sequence

from kg_build_system.distribution.model.public.artifacts import CoreArtifactTypes
from kg_build_system.distribution.modules.duckdb import DuckDbService
from kg_build_system.distribution.modules.runtime import skipped, succeeded
from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    InstructionKind,
    Output,
    PlanContext,
    Step,
    StepOutcome,
)

HELLO_WORLD_KIND = InstructionKind("source_relation", "hello_world")
HELLO_WORLD_RELATION = "hello_world"


class HelloWorldPlanner:
    """Plan one no-input step that supplies the hello-world relation."""

    component_id = "hello_world"
    version = "1"
    runtime_fields = ()

    def plan(self, model: object, context: PlanContext) -> Sequence[Step]:
        del model, context
        return (
            Step(
                component=self.component_id,
                name="source.hello_world",
                inputs=(),
                outputs=(Output(CoreArtifactTypes.table(HELLO_WORLD_RELATION)),),
                instruction=Instruction(HELLO_WORLD_KIND, {}),
            ),
        )


class HelloWorldExecutor:
    """Register the one-row relation and return its reference."""

    kinds = (HELLO_WORLD_KIND,)
    resources = (DuckDbService,)

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        del instruction
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        relation = context.resources.get(DuckDbService).relations.view(
            HELLO_WORLD_RELATION,
            "SELECT 'hello world' AS message",
        )
        return succeeded(context, relation)


__all__ = [
    "HELLO_WORLD_KIND",
    "HELLO_WORLD_RELATION",
    "HelloWorldExecutor",
    "HelloWorldPlanner",
]
