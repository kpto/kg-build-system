"""Binding vocabulary shared across binding packages.

Components that share a template often bind identical values to the
inherited properties. Declaring those stamps once as a ``TypedDict`` keeps
the key set and value types checked at every ``**``-unpacking binding site,
so a missing or mistyped shared stamp is a static error rather than a
binding-time surprise. The bundles pair with the templates and their
``Provenance`` annotations in ``reference_project.topology.common``.
"""

from typing import TypedDict

from kg_build_system import Selection, value_expression


class ProvenanceStamps(TypedDict):
    """The identical parameters every provenanced node binding stamps."""

    source_version: Selection[str]


provenance_stamps: ProvenanceStamps = {
    "source_version": value_expression("survey-2026-08"),
}


class RelationStamps(TypedDict):
    """The identical parameters every recorded relation binding stamps."""

    stage: Selection[str]


relation_stamps: RelationStamps = {"stage": value_expression("derived")}
