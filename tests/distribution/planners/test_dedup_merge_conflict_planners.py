from __future__ import annotations

import unittest
from pathlib import Path

from kg_build_system.distribution import (
    ConflictValidationConfiguration,
    ConflictValidationPlanner,
    DeduplicationPlanner,
    MergingConfiguration,
    MergingPlanner,
)
from kg_build_system.distribution.interpreter import create_blueprint
from kg_build_system.distribution.modules.core import core_planners
from kg_build_system.kernel import Output, PlanContext, Publication
from reference_project.topology.site import SiteNode


class DeduplicationPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        context = PlanContext()
        cls.core_steps = tuple(
            step
            for planner in core_planners()
            for step in planner.plan(cls.blueprint, context)
        )
        cls.steps = tuple(
            DeduplicationPlanner().plan(cls.blueprint, PlanContext())
        )
        bound = {
            binding.component for binding in cls.blueprint.bindings
        }
        cls.components = tuple(
            component
            for component in (
                *cls.blueprint.graph.nodes,
                *cls.blueprint.graph.edges,
            )
            if component.name in bound
        )

    def test_one_step_per_bound_component(self) -> None:
        self.assertEqual(
            [step.name for step in self.steps],
            [component.name for component in self.components],
        )

    def test_steps_use_records_and_publish_distinct(self) -> None:
        for step in self.steps:
            self.assertEqual(step.instruction.kind, ("deduplication", "duckdb"))
            self.assertEqual(step.inputs[0].input_name, "records")
            self.assertEqual(step.outputs[0].name, "distinct")
            self.assertIsInstance(step.outputs[0], Output)
            self.assertNotIsInstance(step.outputs[0], Publication)
            self.assertEqual(
                step.outputs[0].type,
                next(
                    core.outputs[0].type
                    for core in self.core_steps
                    if core.name == f"aggregate.{step.name}"
                ),
            )
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertEqual(
                payload["relation"], f"kg_distinct_{step.name.lower()}",
            )


class MergingPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        cls.steps = tuple(
            MergingPlanner(MergingConfiguration()).plan(
                cls.blueprint, PlanContext(),
            )
        )
        bound = {
            binding.component for binding in cls.blueprint.bindings
        }
        cls.components = tuple(
            component
            for component in (
                *cls.blueprint.graph.nodes,
                *cls.blueprint.graph.edges,
            )
            if component.name in bound
        )

    def test_one_merge_step_per_bound_component(self) -> None:
        self.assertEqual(
            [step.name for step in self.steps],
            [component.name for component in self.components],
        )

    def test_each_step_merges_records_by_build_key(self) -> None:
        for step in self.steps:
            self.assertEqual(step.instruction.kind, ("merging", "duckdb"))
            self.assertEqual(step.inputs[0].input_name, "records")
            self.assertEqual(step.outputs[0].name, "merged")
            self.assertIsInstance(step.outputs[0], Output)
            self.assertNotIsInstance(step.outputs[0], Publication)
            payload = step.instruction.payload
            assert isinstance(payload, dict)
            self.assertEqual(
                payload["relation"],
                f"kg_normalised_{step.name.lower()}",
            )
            self.assertIn('"build_key"', payload["select"])

    def test_configuration_scope_restricts_components(self) -> None:
        steps = tuple(
            MergingPlanner(
                MergingConfiguration(components=(SiteNode,)),
            ).plan(self.blueprint, PlanContext())
        )
        self.assertEqual([step.name for step in steps], ["site"])


class ConflictValidationPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprint = create_blueprint(
            namespace_path=Path("reference_project"),
        )
        cls.steps = tuple(
            ConflictValidationPlanner(
                ConflictValidationConfiguration(),
            ).plan(cls.blueprint, PlanContext())
        )
        bound = {
            binding.component for binding in cls.blueprint.bindings
        }
        cls.components = tuple(
            component
            for component in (
                *cls.blueprint.graph.nodes,
                *cls.blueprint.graph.edges,
            )
            if component.name in bound
        )

    def test_one_findings_step_per_component_property(self) -> None:
        expected = [
            f"{component.name}.{prop.name}"
            for component in self.components
            for prop in component.properties
        ]
        findings = [
            step for step in self.steps if step.name != "report"
        ]
        self.assertEqual([step.name for step in findings], expected)

    def test_findings_steps_declare_their_artifact_type(self) -> None:
        for step in self.steps:
            if step.name == "report":
                continue
            self.assertEqual(
                step.instruction.kind, ("conflict_findings", "duckdb"),
            )
            self.assertEqual(step.inputs[0].input_name, "records")
            self.assertEqual(step.outputs[0].name, "findings")
            self.assertIsInstance(step.outputs[0], Output)
            self.assertNotIsInstance(step.outputs[0], Publication)
            self.assertEqual(
                step.outputs[0].type.namespace, "conflict_validation",
            )
            self.assertEqual(
                step.outputs[0].type.name, f"findings.{step.name}",
            )

    def test_the_report_step_is_deferred_and_publishes_validation(self) -> None:
        report = self.steps[-1]
        self.assertEqual(report.name, "report")
        self.assertEqual(report.instruction.kind, ("conflict_report", "default"))
        self.assertEqual(report.assembly_preference, "deferred")
        self.assertEqual(
            report.instruction.payload, {"fail_on_error": True},
        )
        publication = report.outputs[0]
        self.assertIsInstance(publication, Publication)
        self.assertEqual(publication.name, "report")
        self.assertEqual(publication.type.namespace, "conflict_validation")
        self.assertEqual(
            [output.name for output in report.outputs[1:]],
            [f"{component.name}.validated" for component in self.components],
        )
        for output in report.outputs[1:]:
            self.assertIsInstance(output, Output)
            self.assertNotIsInstance(output, Publication)


if __name__ == "__main__":
    unittest.main()
