"""Import the complete authoring surface for the demonstration graph.

Blueprint compilation and execution are intentionally paused until the new
authoring model has a canonical blueprint IR.
"""

from demo.bindings.nodes.disease.disease import disease_from_reference
from demo.bindings.nodes.study.study import study_from_contract
from demo.bindings.nodes.target.edges.associated_with_disease import association_to_disease
from demo.bindings.nodes.target.target import target_from_reference
from demo.table.sources import evidence_release_source


authoring_declarations = (
    evidence_release_source,
    target_from_reference,
    disease_from_reference,
    study_from_contract,
    association_to_disease,
)

__all__ = ["authoring_declarations"]
