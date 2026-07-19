"""Binding declaration for the demonstration graph."""

from kg_build_system.binding import ColumnRef, EdgeBinding, FieldBinding, InputFormat, NodeBinding, Relation, binding_set

from demo.topology import AssociatedWith, Disease, Target


class TargetDiseaseRows(
    Relation,
    location="demo/data/target_disease.csv",
    format=InputFormat.CSV,
):
    target_id: ColumnRef[str] = ColumnRef[str](nullable=False)
    target_symbol: ColumnRef[str] = ColumnRef[str](nullable=False)
    target_name: ColumnRef[str] = ColumnRef[str]()
    disease_id: ColumnRef[str] = ColumnRef[str](nullable=False)
    disease_name: ColumnRef[str] = ColumnRef[str](nullable=False)
    score: ColumnRef[float] = ColumnRef[float](nullable=False)


class TargetRows(NodeBinding[Target], relation=TargetDiseaseRows):
    identifier: FieldBinding[str] = FieldBinding(Target.id, TargetDiseaseRows.target_id)
    symbol: FieldBinding[str] = FieldBinding(Target.symbol, TargetDiseaseRows.target_symbol)
    name: FieldBinding[str] = FieldBinding(Target.name, TargetDiseaseRows.target_name)


class DiseaseRows(NodeBinding[Disease], relation=TargetDiseaseRows):
    identifier: FieldBinding[str] = FieldBinding(Disease.id, TargetDiseaseRows.disease_id)
    name: FieldBinding[str] = FieldBinding(Disease.name, TargetDiseaseRows.disease_name)


class AssociationRows(EdgeBinding[AssociatedWith], relation=TargetDiseaseRows):
    source: ColumnRef[str] = TargetDiseaseRows.target_id
    target: ColumnRef[str] = TargetDiseaseRows.disease_id
    score: FieldBinding[float] = FieldBinding(AssociatedWith.score, TargetDiseaseRows.score)


BINDINGS = binding_set(
    "target_disease_demo",
    node_bindings=(TargetRows, DiseaseRows),
    edge_bindings=(AssociationRows,),
)
