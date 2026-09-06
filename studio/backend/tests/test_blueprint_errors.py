"""Blueprint-tier mapping of the framework's own error texts.

Every message asserted here is copied from the framework source that raises it, so
the rules cannot drift away from ``kg_build_system`` without a test going red:

* ``kg_build_system/binding/factories.py``
* ``kg_build_system/types/validation.py``
* ``kg_build_system/compile/validation.py``
* ``kg_build_system/compile/compiler.py``
"""

from __future__ import annotations

import pytest

from studio_backend.diagnostics.blueprint_errors import map_blueprint_error
from studio_backend.diagnostics.problem import Problem
from studio_backend.ir.document import (
    Binding,
    Component,
    DataField,
    FieldExpression,
    LiteralExpression,
    ProjectDocument,
    Property,
    PropertyBinding,
    Source,
    Table,
    unit,
)


def hint_of(problem: Problem) -> str:
    """The hint, asserted present: every mapped problem must carry one."""
    assert problem.hint is not None
    return problem.hint


SITE_KEY = FieldExpression(source="sites", path=("site_id",), logical_type=unit("str"))

#: The compiler's own binding symbol id, ``binding:<kind>:<component>:<fingerprint>``.
SITE_SYMBOL = "binding:node:site:4f2c1d9a7b3e8c05a1d6f9b2"
HAS_UNIT_SYMBOL = "binding:edge:has_unit:9b2e7c4a1d05836f2a1c4e77"


@pytest.fixture
def document() -> ProjectDocument:
    documented = Component(
        id="documented",
        kind="node",
        tier="category",
        declaration_name="DocumentedAbstractNode",
        name="documented",
        properties=(Property(name="summary", logical_type=unit("str")),),
    )
    site = documented.updated(
        id="site",
        tier="concrete",
        declaration_name="SiteNode",
        name="site",
        parent="documented",
        properties=(Property(name="name", logical_type=unit("str")), Property(name="city", logical_type=unit("str"))),
    )
    unit_node = site.updated(
        id="unit",
        declaration_name="UnitNode",
        name="unit",
        properties=(Property(name="name", logical_type=unit("str")),),
    )
    monitored = Component(
        id="monitored_relation",
        kind="edge",
        tier="category",
        declaration_name="MonitoredRelationAbstractEdge",
        name="monitored_relation",
        source="documented",
        target="documented",
    )
    has_unit = monitored.updated(
        id="has_unit",
        tier="concrete",
        declaration_name="HasUnitEdge",
        name="has_unit",
        parent="monitored_relation",
        source="site",
        target="unit",
        properties=(),
    )
    sites = Table(
        id="sites",
        declaration_name="SitesTable",
        name="sites",
        fields=(
            DataField(name="site_id", logical_type=unit("str", nullable=True)),
            DataField(name="site_name", logical_type=unit("str", nullable=True)),
        ),
    )
    equipment = sites.updated(
        id="equipment",
        declaration_name="EquipmentTable",
        name="equipment",
        fields=(DataField(name="unit_ref", logical_type=unit("str", nullable=True)),),
    )
    site_binding = Binding(
        id="site_binding",
        kind="node",
        component="site",
        build_key=SITE_KEY,
        properties=(
            PropertyBinding(
                name="name",
                expression=LiteralExpression(value="Unnamed site", logical_type=unit("str")),
            ),
            PropertyBinding(
                name="city",
                expression=FieldExpression(
                    source="sites", path=("site_id",), logical_type=unit("str", nullable=True)
                ),
            ),
        ),
    )
    has_unit_binding = Binding(
        id="has_unit_binding",
        kind="edge",
        component="has_unit",
        build_key=SITE_KEY,
        source_build_key=SITE_KEY,
        target_build_key=SITE_KEY,
    )
    return ProjectDocument(
        tables=(sites, equipment),
        components=(documented, site, unit_node, monitored, has_unit),
        bindings=(site_binding, has_unit_binding),
        sources=(
            Source(id="sites_source", table="sites", location="data/sites.json", format="json"),
            Source(id="equipment_source", table="equipment", location="data/equipment.json", format="json"),
        ),
    )


def test_problem_shape_is_the_contract(document: ProjectDocument) -> None:
    problem = map_blueprint_error("component names must be unique", document)
    payload = problem.as_json()
    assert set(payload) == {
        "id",
        "tier",
        "severity",
        "message",
        "code",
        "file",
        "line",
        "column",
        "end_line",
        "end_column",
        "ref",
        "ref_trusted",
        "hint",
    }
    assert payload["tier"] == "blueprint"
    assert payload["severity"] == "error"
    # A framework validation error has no position, and inventing one would put a
    # squiggle on a line the user did not write.
    assert payload["file"] is None
    assert payload["line"] is None
    assert payload["hint"] not in ("", None)
    assert payload["message"] == "component names must be unique"


# ----------------------------------------------------- binding-level property slots


def test_property_type_mismatch_resolves_to_the_bound_slot(document: ProjectDocument) -> None:
    message = (
        "SiteNode.city expects UnitType(name='str'), "
        "but the expression resolves to UnitType(name='int')"
    )
    problem = map_blueprint_error(message, document)
    assert problem.code == "property_type_mismatch"
    assert problem.ref == "binding:site_binding.property.city"
    assert problem.ref_trusted == "name"
    assert problem.message == message
    assert "SiteNode.city" in hint_of(problem) or "city" in hint_of(problem)


def test_inherited_slot_mismatch_resolves_through_the_category(document: ProjectDocument) -> None:
    message = (
        "SiteNode.summary expects UnitType(name='int'), "
        "but the expression resolves to UnitType(name='str')"
    )
    problem = map_blueprint_error(message, document)
    assert problem.ref == "component:documented.property.summary"


def test_missing_slot_value(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "SiteNode.city must be assigned a value selection or expression", document
    )
    assert problem.code == "property_value_missing"
    assert problem.ref == "binding:site_binding.property.city"
    assert "city" in hint_of(problem)


def test_missing_inherited_slot_value(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "UnitNode.summary must be assigned a value selection or expression", document
    )
    assert problem.code == "property_value_missing"
    assert problem.ref == "component:documented.property.summary"


def test_property_value_must_be_an_expression(document: ProjectDocument) -> None:
    problem = map_blueprint_error("SiteNode.city must be a value expression", document)
    assert problem.code == "property_value_missing"
    assert problem.ref == "binding:site_binding.property.city"


def test_binding_property_logical_type_mismatch(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"binding {SITE_SYMBOL!r} property 'city' has an incompatible logical type", document
    )
    assert problem.code == "property_incompatible_type"
    assert problem.ref == "binding:site_binding.property.city"


def test_binding_must_map_every_property_once(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"binding {SITE_SYMBOL!r} must map every declared component property exactly once", document
    )
    assert problem.code == "property_not_mapped_once"
    assert problem.ref == "binding:site_binding"


def test_properties_must_be_the_target_class(document: ProjectDocument) -> None:
    problem = map_blueprint_error("properties must be an instance of SiteNode", document)
    assert problem.code == "properties_wrong_class"
    assert problem.ref == "component:site"


# ------------------------------------------------------------------ build keys


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("build_key must not be nullable", "build_key_nullable"),
        ("source_build_key must not be nullable", "build_key_nullable"),
        ("target_build_key must not be nullable", "build_key_nullable"),
        ("build_key must be a scalar", "build_key_not_scalar"),
        ("source_build_key must be a scalar", "build_key_not_scalar"),
        ("build_key must be a value selection or expression", "build_key_not_expression"),
        ("target_build_key must be a value selection or expression", "build_key_not_expression"),
    ],
)
def test_build_key_rules(document: ProjectDocument, message: str, code: str) -> None:
    problem = map_blueprint_error(message, document)
    assert problem.code == code
    # The argument name is all the message says, so no ref may be invented for it.
    assert problem.ref is None
    assert problem.ref_trusted is None
    assert "build_key" in hint_of(problem)


def test_binding_keys_non_null_scalar(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"binding {HAS_UNIT_SYMBOL!r} keys must be non-null scalar expressions", document
    )
    assert problem.code == "binding_keys_invalid"
    assert problem.ref == "binding:has_unit_binding"


# ----------------------------------------------------------------- binding target


def test_abstract_binding_target_from_the_factory(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "target must be a concrete node component, not DocumentedAbstractNode", document
    )
    assert problem.code == "target_must_be_concrete"
    assert problem.ref == "component:documented"
    assert "DocumentedAbstractNode" in hint_of(problem)
    assert "node" in hint_of(problem)


def test_abstract_binding_target_from_validation(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"node binding {SITE_SYMBOL!r} may not target abstract component 'documented'", document
    )
    assert problem.code == "target_must_be_concrete"
    assert problem.ref in {"binding:site_binding", "component:documented"}
    assert "documented" in hint_of(problem)


def test_binding_targets_an_incompatible_component(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"edge binding {SITE_SYMBOL!r} targets an incompatible component", document
    )
    assert problem.code == "target_incompatible_component"
    assert problem.ref == "binding:site_binding"


# -------------------------------------------------------------------- endpoints


def test_endpoint_token_must_be_concrete(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "source_node must name a concrete node component, not DocumentedAbstractNode", document
    )
    assert problem.code == "endpoint_not_concrete"
    assert problem.ref == "component:documented"
    assert "source" in hint_of(problem)


def test_endpoint_must_descend_from_the_declared_category(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "target_node UnitNode must equal or descend from the declared endpoint category DocumentedAbstractNode",
        document,
    )
    assert problem.code == "endpoint_not_descended"
    assert problem.ref == "component:unit"
    assert "DocumentedAbstractNode" in hint_of(problem)


def test_endpoint_token_is_required(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "source_node must name the declared endpoint category DocumentedAbstractNode: "
        "pass endpoint(...) for that side",
        document,
    )
    assert problem.code == "endpoint_required"
    assert problem.ref == "component:documented"


def test_endpoint_token_must_be_a_token(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "target_node must be an endpoint(...) token, not the raw value <class 'SiteNode'>", document
    )
    assert problem.code == "endpoint_token_required"
    assert "target" in hint_of(problem)


def test_validation_endpoint_not_concrete(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"edge binding {HAS_UNIT_SYMBOL!r} source endpoint 'documented' "
        "must name a concrete node component",
        document,
    )
    assert problem.code == "endpoint_not_concrete"
    assert problem.ref is not None and problem.ref.startswith("binding:has_unit_binding")


def test_validation_endpoint_not_descended(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"edge binding {HAS_UNIT_SYMBOL!r} target endpoint 'site' "
        "must equal or descend from the declared endpoint 'unit'",
        document,
    )
    assert problem.code == "endpoint_not_descended"
    assert problem.ref is not None and problem.ref.startswith("binding:has_unit_binding")


def test_edge_references_an_unknown_endpoint(document: ProjectDocument) -> None:
    problem = map_blueprint_error("edge 'has_unit' references an unknown endpoint", document)
    assert problem.code == "unknown_endpoint"
    assert problem.ref == "component:has_unit"


# -------------------------------------------------------------- duplicate names


@pytest.mark.parametrize(
    ("message", "expected_ref"),
    [
        ("blueprint symbol IDs must be unique", None),
        ("table names must be unique", None),
        ("component names must be unique", None),
        ("projection names must be unique", None),
        ("logical source names must be unique", None),
        ("module IDs must be unique", None),
        ("sites field names must be unique", "table:sites"),
        ("site property names must be unique", "component:site"),
        ("SiteCityProjection projection field names must be unique", None),
    ],
)
def test_duplicate_name_rules(document: ProjectDocument, message: str, expected_ref: str | None) -> None:
    problem = map_blueprint_error(message, document)
    assert problem.code in {"duplicate_names", "duplicate_symbol_ids", "duplicate_module_ids"}
    assert problem.ref == expected_ref
    assert "unique" not in hint_of(problem) or "rename" in hint_of(problem)


# ---------------------------------------------------------- sources and tables


def test_physical_source_references_an_unknown_table(document: ProjectDocument) -> None:
    problem = map_blueprint_error("a physical source references an unknown table", document)
    assert problem.code == "unknown_source_table"
    assert problem.ref is None
    assert "source" in hint_of(problem).lower()


def test_table_without_a_bound_source(document: ProjectDocument) -> None:
    problem = map_blueprint_error("no source bound for: equipment, sites", document)
    assert problem.code == "table_without_source"
    assert problem.ref in {"table:equipment", "table:sites"}
    assert "equipment" in hint_of(problem)


def test_expression_references_an_unknown_logical_source(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"binding:node:site:4f2c1d9a7b3e8c05a1d6f9b2 references unknown logical source 'readings'",
        document,
    )
    assert problem.code == "unknown_logical_source"
    # ``readings`` is not in the document — that is the point of the message — so the
    # ref lands on the binding whose expression names it.
    assert problem.ref == "binding:site_binding"


def test_expression_references_an_unknown_field(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"{HAS_UNIT_SYMBOL} references unknown field 'unit_code' on logical source 'equipment'",
        document,
    )
    assert problem.code == "unknown_field"
    assert problem.ref is not None
    assert "equipment" in hint_of(problem) or "unit_code" in hint_of(problem)


def test_undiscoverable_logical_sources(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "expressions reference undiscoverable logical sources: readings, surveys", document
    )
    assert problem.code == "undiscoverable_sources"
    assert "readings" in hint_of(problem)


# ------------------------------------------------------------------- hierarchy


def test_unknown_parent(document: ProjectDocument) -> None:
    problem = map_blueprint_error("component 'site' references an unknown parent", document)
    assert problem.code == "unknown_parent"
    assert problem.ref == "component:site"


def test_parent_must_be_abstract_of_the_same_kind(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "component 'site' parent must name an abstract node component", document
    )
    assert problem.code == "parent_wrong_kind"
    assert problem.ref == "component:site"


def test_parent_cycle(document: ProjectDocument) -> None:
    problem = map_blueprint_error("component parent chain cycle includes 'site'", document)
    assert problem.code == "parent_cycle"
    assert problem.ref == "component:site"


def test_projection_cycle(document: ProjectDocument) -> None:
    problem = map_blueprint_error("projection dependency cycle includes 'site_cities'", document)
    assert problem.code == "projection_cycle"
    assert problem.ref is None


def test_node_may_not_declare_endpoints(document: ProjectDocument) -> None:
    problem = map_blueprint_error("node 'site' may not declare endpoints", document)
    assert problem.code == "node_declares_endpoints"
    assert problem.ref == "component:site"


def test_edge_requires_endpoints(document: ProjectDocument) -> None:
    problem = map_blueprint_error("edge 'has_unit' requires source and target components", document)
    assert problem.code == "edge_missing_endpoints"
    assert problem.ref == "component:has_unit"


# ------------------------------------------------------------- expression shape


def test_expand_requires_an_array(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        f"{SITE_SYMBOL} expand operation requires an array argument", document
    )
    assert problem.code == "expand_shape"
    assert problem.ref == "binding:site_binding"


def test_expand_arity(document: ProjectDocument) -> None:
    problem = map_blueprint_error("site_cities expand operation requires one argument", document)
    assert problem.code == "expand_shape"


# ------------------------------------------------------------------- fallbacks


def test_an_unrecognised_message_still_becomes_a_problem(document: ProjectDocument) -> None:
    problem = map_blueprint_error("the plan could not be lowered for reasons", document)
    assert problem.code == "blueprint_validation_error"
    assert problem.ref is None
    assert problem.tier == "blueprint"
    assert problem.hint


def test_the_message_is_stored_verbatim_minus_line_breaks(document: ProjectDocument) -> None:
    problem = map_blueprint_error(
        "SiteNode.city expects UnitType(name='str'), \n  but the expression resolves to UnitType(name='int')",
        document,
    )
    assert problem.message == (
        "SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')"
    )


def test_hint_never_restates_the_raw_message(document: ProjectDocument) -> None:
    messages = [
        "SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')",
        "build_key must be a scalar",
        "component names must be unique",
        "a physical source references an unknown table",
        "target must be a concrete node component, not DocumentedAbstractNode",
    ]
    for message in messages:
        problem = map_blueprint_error(message, document)
        hint = hint_of(problem)
        assert hint.strip() != message.strip()
        assert "expects UnitType" not in hint
        assert "must be unique" not in hint


def test_identical_errors_have_identical_ids(document: ProjectDocument) -> None:
    first = map_blueprint_error("component names must be unique", document)
    second = map_blueprint_error("component names must be unique", document)
    assert first.id == second.id


def test_id_is_the_sha1_of_tier_file_code_message(document: ProjectDocument) -> None:
    from studio_backend.diagnostics.problem import problem_id

    problem = map_blueprint_error("component names must be unique", document)
    assert problem.id == problem_id("blueprint", None, problem.code, problem.message)
