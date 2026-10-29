"""How contributed steps become a wired workflow definition."""
from __future__ import annotations

import unittest

from kg_build_system.workflow.interfaces import AssemblyError, assemble_workflow
from kg_build_system.workflow.interfaces import create_workflow_contract
from kg_build_system.workflow.interfaces import opening_identity, step_identity
from kg_build_system.workflow.interfaces import workflow_from_ir
from kg_build_system.workflow.interfaces import (
    ArtifactType, Input, ModuleDefinition, ModuleReference, Output, Publication,
    WorkflowContribution, WorkflowStep,
)

SITES = ArtifactType("core", "graph.node.site")
SURVEYS = ArtifactType("core", "graph.node.survey")
ANY_GRAPH = ArtifactType("core", "graph.*")
WRITTEN = ArtifactType("file", "write_result")


def module(module_id: str) -> ModuleDefinition:
    return ModuleDefinition(reference=ModuleReference(
        module_id=module_id, import_module="tests.fake", class_qualname="Module",
        implementation_version="1",
    ))


def contribution(module_id: str, *steps: WorkflowStep) -> WorkflowContribution:
    return WorkflowContribution(module(module_id), tuple(steps))


def producer(*types: ArtifactType, name: str = "produce") -> WorkflowStep:
    return WorkflowStep(
        outputs=tuple(Output(item, item.name.rsplit(".", 1)[-1]) for item in types),
        name=name,
    )


def wires(workflow) -> set[tuple[str, str]]:
    return {
        (connection.output_id, connection.input_id)
        for connection in workflow.connections
    }


def opening_id(module_id: str, step: str, opening: str) -> str:
    """The identity of one opening, formed the way the assembler forms it."""
    return opening_identity(step_identity(module_id, step), opening)


input_id = output_id = opening_id


class DeclaringTests(unittest.TestCase):
    def test_one_writer_of_a_type_feeds_the_step_that_asks_for_it(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES)),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
        ))
        self.assertEqual(wires(workflow), {(
            output_id("core", "produce", "site"),
            input_id("file", "write", "records"),
        )})

    def test_an_unnamed_opening_takes_the_word_for_its_kind(self) -> None:
        workflow = assemble_workflow((
            contribution("core", WorkflowStep(outputs=(Output(SITES),))),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES),), outputs=(Publication(WRITTEN),),
            )),
        ))
        self.assertEqual(wires(workflow), {(
            output_id("core", "step1", "output"),
            input_id("file", "step1", "input"),
        )})

    def test_unnamed_steps_are_counted_within_their_module(self) -> None:
        workflow = assemble_workflow((contribution("core",
            WorkflowStep(outputs=(Output(SITES),)),
            WorkflowStep(inputs=(Input(SITES),), outputs=(Output(SURVEYS),)),
            WorkflowStep(inputs=(Input(SURVEYS),), outputs=(Publication(WRITTEN),)),
        ),))
        names = [step.name for step in workflow.contributions[0].steps]
        self.assertEqual(names, ["step1", "step2", "step3"])
        self.assertEqual(len(workflow.connections), 2)

    def test_two_steps_of_one_module_may_not_share_a_name(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "declares step 'produce' twice"):
            assemble_workflow((contribution("core", producer(SITES), producer(SURVEYS)),))

    def test_two_modules_may_name_their_step_alike(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES, name="make")),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES),), outputs=(Publication(WRITTEN),), name="make",
            )),
        ))
        self.assertEqual(wires(workflow), {(
            output_id("core", "make", "site"), input_id("file", "make", "input"),
        )})

    def test_a_step_may_not_take_the_same_opening_name_twice(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "takes 'records' twice"):
            assemble_workflow((
                contribution("core", producer(SITES, SURVEYS)),
                contribution("file", WorkflowStep(
                    inputs=(Input(SITES, "records"), Input(SURVEYS, "records")),
                    outputs=(Publication(WRITTEN),),
                )),
            ))

    def test_an_output_may_not_ask_for_a_family_of_types(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "a value given out is one type"):
            assemble_workflow((contribution("core", WorkflowStep(
                outputs=(Output(ANY_GRAPH, "everything"),),
            )),))


class OpenInputTests(unittest.TestCase):
    def test_an_open_input_grows_one_port_per_type_it_matches(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES, SURVEYS)),
            contribution("file", WorkflowStep(
                inputs=(Input(ANY_GRAPH, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
        ))
        written = workflow.contributions[1].steps[0]
        self.assertEqual(
            [(item.input_name, item.name, item.type) for item in written.inputs],
            [
                ("records", "records:core.graph.node.site", SITES),
                ("records", "records:core.graph.node.survey", SURVEYS),
            ],
        )
        self.assertEqual(wires(workflow), {
            (output_id("core", "produce", "site"), input_id("file", "write", "records:core.graph.node.site")),
            (output_id("core", "produce", "survey"), input_id("file", "write", "records:core.graph.node.survey")),
        })

    def test_a_pattern_in_the_namespace_half_spans_modules(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES)),
            contribution("clean", WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Output(SITES, "cleared"),),
                name="pass",
            )),
            contribution("both", WorkflowStep(
                inputs=(Input(ArtifactType("*", "graph.node.site"), "records"),),
                outputs=(Publication(ArtifactType("both", "counted"), "result"),),
                name="gather",
            )),
        ))
        gathered = next(
            step for module_id, step in workflow.steps_by_module if module_id == "both"
        )
        self.assertEqual([item.name for item in gathered.inputs], ["records:core.graph.node.site"])

    def test_an_open_input_matching_nothing_takes_no_port(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES)),
            contribution("edges", WorkflowStep(
                inputs=(Input(ArtifactType("core", "edge.*"), "edges"),),
                outputs=(Publication(ArtifactType("edges", "counted"), "result"),),
                name="count",
            )),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
        ))
        counter = workflow.contributions[1].steps[0]
        self.assertEqual(counter.inputs, ())
        self.assertEqual(len(workflow.connections), 1)

    def test_a_type_nobody_writes_is_reported_rather_than_dropped(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "which no other step writes"):
            assemble_workflow((contribution("core", WorkflowStep(
                inputs=(Input(SITES, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
            )),))


class ChoiceTests(unittest.TestCase):
    def test_two_writers_of_one_type_that_differ_by_nothing_are_refused(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "differ by nothing the declaration states"):
            assemble_workflow((
                contribution("core", producer(SITES, name="first"), producer(SITES, name="second")),
                contribution("file", WorkflowStep(
                    inputs=(Input(SITES, "records"),), outputs=(Publication(WRITTEN),),
                    name="one",
                ), WorkflowStep(
                    inputs=(Input(SITES, "records"),),
                    outputs=(Publication(ArtifactType("file", "other_result"),),),
                    name="two",
                )),
            ))

    def test_a_step_that_takes_the_type_it_writes_hands_on_the_freshest_result(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES, name="raw")),
            contribution(
                "clean",
                WorkflowStep(
                    inputs=(Input(SITES, "records"),), outputs=(Output(SITES, "cleaned"),),
                    name="tidy",
                ),
            ),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Publication(WRITTEN),), name="write",
            )),
        ))
        self.assertEqual(wires(workflow), {
            (output_id("core", "raw", "site"), input_id("clean", "tidy", "records")),
            (output_id("clean", "tidy", "cleaned"), input_id("file", "write", "records")),
        })

    def test_of_two_endofunctors_the_one_that_ran_last_is_taken(self) -> None:
        """A chain of steps that each take the type they write leaves the freshest on top."""
        def tidy(name: str) -> WorkflowStep:
            return WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Output(SITES, name),), name=name,
            )

        workflow = assemble_workflow((
            contribution("core", producer(SITES, name="raw")),
            contribution("first_pass", tidy("tidy_a")),
            contribution("second_pass", tidy("tidy_b")),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Publication(WRITTEN),), name="write",
            )),
        ))
        self.assertEqual(wires(workflow), {
            (output_id("core", "raw", "site"), input_id("first_pass", "tidy_a", "records")),
            (output_id("first_pass", "tidy_a", "tidy_a"), input_id("second_pass", "tidy_b", "records")),
            (output_id("second_pass", "tidy_b", "tidy_b"), input_id("file", "write", "records")),
        })

    def test_a_step_may_not_read_what_it_writes_itself(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "which no other step writes"):
            assemble_workflow((contribution("core", WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Output(SITES, "site"),),
            )),))

    def test_a_round_trip_is_refused(self) -> None:
        first = ArtifactType("a", "first")
        second = ArtifactType("a", "second")
        with self.assertRaisesRegex(AssemblyError, "loop back to every writer"):
            assemble_workflow((contribution("a",
                WorkflowStep(inputs=(Input(second, "in"),), outputs=(Output(first, "out"),)),
                WorkflowStep(inputs=(Input(first, "in"),), outputs=(Output(second, "out"),)),
            ),))


class ReadingTests(unittest.TestCase):
    def test_an_output_nobody_reads_is_refused(self) -> None:
        with self.assertRaisesRegex(AssemblyError, "nothing reads core::produce.site"):
            assemble_workflow((contribution("core", producer(SITES)),))

    def test_several_readers_may_share_one_output(self) -> None:
        workflow = assemble_workflow((
            contribution("core", producer(SITES)),
            contribution("file", WorkflowStep(
                inputs=(Input(SITES, "records"),), outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
            contribution("graph_doc", WorkflowStep(
                inputs=(Input(SITES, "records"),),
                outputs=(Publication(ArtifactType("graph_doc", "document"), "result"),),
                name="document",
            )),
        ))
        self.assertEqual(len(workflow.connections), 2)

    def test_a_publication_needs_no_reader(self) -> None:
        workflow = assemble_workflow((contribution("file", WorkflowStep(
            outputs=(Publication(WRITTEN, "result"),), name="write",
        )),))
        self.assertEqual(workflow.connections, ())

    def test_an_unfed_input_names_what_it_was_asked_for(self) -> None:
        with self.assertRaises(AssemblyError) as caught:
            assemble_workflow((contribution("file", WorkflowStep(
                inputs=(Input(ArtifactType("core", "graph.node.missing"), "records"),),
                outputs=(Publication(WRITTEN, "result"),),
            )),))
        self.assertIn("core/graph.node.missing", str(caught.exception))


class DefinitionTests(unittest.TestCase):
    def workflow(self):
        return assemble_workflow((
            contribution("core", producer(SITES, SURVEYS, name="produce")),
            contribution("file", WorkflowStep(
                inputs=(Input(ANY_GRAPH, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
        ))

    def test_the_definition_lists_steps_with_their_module(self) -> None:
        workflow = self.workflow()
        self.assertEqual(
            [(module_id, step.name) for module_id, step in workflow.steps_by_module],
            [("core", "produce"), ("file", "write")],
        )

    def test_the_definition_survives_the_contract_round_trip(self) -> None:
        workflow = self.workflow()
        contract = create_workflow_contract(workflow, provenance={"why": "test"})
        self.assertEqual(workflow_from_ir(contract.workflow), workflow)

    def test_the_fingerprint_follows_the_wiring(self) -> None:
        first = create_workflow_contract(self.workflow())
        second = create_workflow_contract(self.workflow())
        self.assertEqual(first.workflow_fingerprint, second.workflow_fingerprint)
        moved = assemble_workflow((
            contribution("file", WorkflowStep(
                inputs=(Input(ANY_GRAPH, "records"),),
                outputs=(Publication(WRITTEN, "result"),),
                name="write",
            )),
            contribution("core", producer(SITES, SURVEYS, name="produce")),
        ))
        self.assertNotEqual(
            first.workflow_fingerprint,
            create_workflow_contract(moved).workflow_fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
